"""
5단계: 유튜브 자동 업로드 (YouTube Data API v3)
- 생성된 최종 영상(final_video.mp4), 썸네일(final_thumbnail.jpg), 메타데이터(metadata.json)를
  사용자의 유튜브 채널에 '일부공개(unlisted)' 상태로 자동 업로드합니다.
- OAuth 2.0 인증 정보를 token.pickle에 캐싱하여 최초 1회 브라우저 로그인 후 자동화됩니다.
"""
import os
import pickle
import time
from pathlib import Path
from typing import Dict, Optional

import config

try:
    from googleapiclient.discovery import build
    from googleapiclient.http import MediaFileUpload
    from googleapiclient.errors import HttpError
    from google_auth_oauthlib.flow import InstalledAppFlow
    from google.auth.transport.requests import Request
    HAS_YOUTUBE_LIBS = True
except ImportError:
    HAS_YOUTUBE_LIBS = False


class YouTubeUploader:
    def __init__(
        self,
        client_secrets_file: Optional[Path] = None,
        token_pickle_file: Optional[Path] = None,
        privacy_status: str = config.DEFAULT_PRIVACY_STATUS
    ):
        self.client_secrets_file = Path(client_secrets_file or config.CLIENT_SECRETS_FILE)
        self.token_pickle_file = Path(token_pickle_file or config.TOKEN_PICKLE_FILE)
        self.privacy_status = privacy_status

    def get_authenticated_service(self):
        """
        YouTube Data API v3 클라이언트를 생성하고 인증합니다.
        기존 token.pickle이 있으면 재사용하고, 만료되었으면 갱신합니다.
        """
        if not HAS_YOUTUBE_LIBS:
            raise ImportError(
                "google-api-python-client 또는 google-auth-oauthlib 라이브러리가 필요합니다."
            )

        credentials = None

        # 1) 캐시된 토큰 로드
        if self.token_pickle_file.exists():
            with open(self.token_pickle_file, "rb") as token:
                credentials = pickle.load(token)

        # 2) 토큰이 없거나 유효하지 않은 경우 갱신/신규 인증
        if not credentials or not credentials.valid:
            if credentials and credentials.expired and credentials.refresh_token:
                print("   * 저장된 인증 토큰 갱신 중...")
                credentials.refresh(Request())
            else:
                if not self.client_secrets_file.exists():
                    raise FileNotFoundError(
                        f"유튜브 인증 파일 '{self.client_secrets_file}'을 찾을 수 없습니다.\n"
                        f"Google Cloud Console에서 데스크톱 OAuth 클라이언트 ID를 생성한 뒤\n"
                        f"프로젝트 폴더에 'client_secrets.json'으로 저장해 주세요. (README.md 참조)"
                    )

                print("   * 최초 1회 유튜브 로그인 브라우저 인증을 시작합니다...")
                flow = InstalledAppFlow.from_client_secrets_file(
                    str(self.client_secrets_file),
                    config.YOUTUBE_UPLOAD_SCOPE
                )
                credentials = flow.run_local_server(port=0)

            # 새 토큰 저장
            with open(self.token_pickle_file, "wb") as token:
                pickle.dump(credentials, token)
                print(f"   * 인증 토큰 캐싱 완료: {self.token_pickle_file}")

        return build(
            config.YOUTUBE_API_SERVICE_NAME,
            config.YOUTUBE_API_VERSION,
            credentials=credentials
        )

    def upload_video(
        self,
        video_path: str,
        thumbnail_path: Optional[str],
        metadata: Dict,
        dry_run: bool = False
    ) -> Dict:
        """
        비디오를 업로드하고 썸네일을 등록합니다.
        
        Args:
            video_path: 최종 영상 파일 경로
            thumbnail_path: 썸네일 이미지 파일 경로
            metadata: title, description, tags를 포함한 딕셔너리
            dry_run: 실제 업로드 대신 요청 정보만 검증하는 모드
            
        Returns:
            Dict: 업로드 결과 정보 (video_id, watch_url, status)
        """
        print(f"\n[5단계: 유튜브 자동 업로드 시작]")
        video_path = str(Path(video_path).resolve())
        if not os.path.exists(video_path):
            raise FileNotFoundError(f"업로드할 영상을 찾을 수 없습니다: {video_path}")

        title = metadata.get("title", "포켓몬 챔피언스 하이라이트")
        description = metadata.get("description", "")
        tags = metadata.get("tags", [])

        print(f" - 영상 파일: {video_path}")
        print(f" - 공개 상태: {self.privacy_status} (일부공개)")
        print(f" - 영상 제목: {title}")

        if dry_run:
            print("   ℹ️ [DRY RUN] 실제 업로드는 수행하지 않습니다.")
            return {
                "status": "dry_run_success",
                "video_id": "MOCK_VIDEO_ID_12345",
                "watch_url": "https://youtu.be/MOCK_VIDEO_ID_12345",
                "privacy": self.privacy_status
            }

        # client_secrets.json 확인
        if not self.client_secrets_file.exists() and not self.token_pickle_file.exists():
            print("   ⚠️ client_secrets.json 파일이 설정되지 않았습니다.")
            print("   -> 로컬 렌더링(영상/썸네일/메타데이터)은 완료되었으며 유튜브 업로드만 건너뜁니다.")
            print("   -> README.md의 '유튜브 API 연동 가이드'를 확인하여 파일을 배치해 주세요.")
            return {
                "status": "skipped",
                "reason": "client_secrets.json missing",
                "local_video": video_path,
                "local_thumbnail": thumbnail_path
            }

        youtube = self.get_authenticated_service()

        body = {
            "snippet": {
                "title": title[:100],
                "description": description,
                "tags": tags,
                "categoryId": config.YOUTUBE_CATEGORY_ID
            },
            "status": {
                "privacyStatus": self.privacy_status,
                "selfDeclaredMadeForKids": False
            }
        }

        # 대용량 분할 업로드 지원
        media_body = MediaFileUpload(
            video_path,
            chunksize=-1,
            resumable=True
        )

        insert_request = youtube.videos().insert(
            part=",".join(body.keys()),
            body=body,
            media_body=media_body
        )

        print("   * 영상 파일 업로드 진행 중 (Resumable Upload)...")
        response = None
        while response is None:
            status, response = insert_request.next_chunk()
            if status:
                print(f"     진행률: {int(status.progress() * 100)}%")

        video_id = response.get("id")
        watch_url = f"https://youtu.be/{video_id}"
        print(f"   * 영상 업로드 완료! Video ID: {video_id}")
        print(f"   * 영상 링크: {watch_url}")

        # 썸네일 업로드
        if thumbnail_path and os.path.exists(thumbnail_path):
            print(f"   * 썸네일 이미지 등록 중: {thumbnail_path}")
            try:
                youtube.thumbnails().set(
                    videoId=video_id,
                    media_body=MediaFileUpload(thumbnail_path, mimetype="image/jpeg")
                ).execute()
                print("   * 썸네일 등록 성공!")
            except Exception as e:
                print(f"   ⚠️ 썸네일 등록 중 오류 발생: {e}")

        print(f"✨ [5단계 완료] 유튜브 업로드 파이프라인 성공!")
        return {
            "status": "success",
            "video_id": video_id,
            "watch_url": watch_url,
            "privacy": self.privacy_status
        }


if __name__ == "__main__":
    uploader = YouTubeUploader()
    res = uploader.upload_video("test.mp4", None, {"title": "테스트"}, dry_run=True)
    print("결과:", res)
