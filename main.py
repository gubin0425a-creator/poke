"""
포켓몬 챔피언스 자동 편집 및 유튜브 업로드 파이프라인 - 통합 메인 오케스트레이터
OpenCV 승리 감지 -> auto-editor + MoviePy 테디님 템포 편집 -> Pillow 썸네일 -> Gemini SEO 메타데이터 -> YouTube 업로드
"""
import os
import sys
import argparse
from pathlib import Path

import config
from detector import WinDetector
from editor import TeddyVideoEditor
from thumbnail import TeddyThumbnailGenerator
from metadata_generator import TeddyMetadataGenerator
from uploader import YouTubeUploader


def print_banner():
    banner = """
======================================================================
  ⚡ 포켓몬 챔피언스(포챔스) AI 자동 편집 & 유튜브 업로드 파이프라인 ⚡
                 [테디님 스타일 100% 전자동 시스템]
======================================================================
 [1단계] OpenCV 템플릿 매칭 승리 경기 감지 & 컷 분할
 [2단계] auto-editor 4배속 압축 + 결정타 1.2배 줌인 편집 (MoviePy)
 [3단계] Pillow 맑은 고딕 볼드 폰트 어그로 썸네일 생성
 [4단계] Gemini API 기반 SEO 최적화 제목/설명/15개 태그 생성
 [5단계] YouTube Data API v3 일부공개(unlisted) 자동 업로드
======================================================================
"""
    print(banner)


def run_pipeline(
    video_path: str,
    skip_upload: bool = False,
    dry_run: bool = False,
    threshold: float = config.TEMPLATE_MATCH_THRESHOLD,
    template_path: str = None
):
    print_banner()

    video_file = Path(video_path).resolve()
    if not video_file.exists():
        print(f"❌ 오류: 입력 영상 파일을 찾을 수 없습니다 -> {video_path}")
        sys.exit(1)

    print(f"🎬 작업 대상 파일: {video_file.name}")
    print(f"📂 파일 전체 경로: {video_file}")

    # -------------------------------------------------------------
    # 1단계: 승리 경기 감지 및 컷 분할 (OpenCV)
    # -------------------------------------------------------------
    detector = WinDetector(
        template_path=template_path,
        threshold=threshold
    )
    matches = detector.detect_winning_matches(str(video_file))

    if not matches:
        print("\n⚠️ 알림: 영상에서 '승리(WIN)' 화면을 감지하지 못했습니다.")
        print(" - 원인 1: 템플릿 매칭 임계값(현재: {:.2f})이 너무 높을 수 있습니다. (--threshold 0.50 시도)".format(threshold))
        print(" - 원인 2: 녹화본의 승리 화면 그래픽이 assets/win_template.png와 다를 수 있습니다.")
        print(" - 안내: 사용자의 실제 승리 화면 스크린샷을 assets/win_template.png 로 교체하면 100% 인식됩니다.")
        sys.exit(1)

    print(f"\n✅ [1단계 성공] 총 {len(matches)}개의 승리 경기 클립 정보 추출 완료!")

    # -------------------------------------------------------------
    # 2단계: 테디님 템포 자동 편집 (auto-editor + MoviePy)
    # -------------------------------------------------------------
    editor = TeddyVideoEditor()
    final_video_path = editor.edit_matches(str(video_file), matches)
    print(f"\n✅ [2단계 성공] 최종 영상 생성 완료 -> {final_video_path}")

    # -------------------------------------------------------------
    # 3단계 & 4단계: Gemini 메타데이터 생성 후 썸네일 합성
    # -------------------------------------------------------------
    metadata_gen = TeddyMetadataGenerator()
    metadata = metadata_gen.generate_metadata(matches)
    print(f"\n✅ [4단계 성공] SEO 메타데이터 생성 완료")

    sub_text = metadata.get("sub_text", "상대 멘탈 터진 역대급 레전드 경기 ㄷㄷ")
    main_text = metadata.get("main_text", "이 포켓몬 하나로 올킬?!")

    thumb_gen = TeddyThumbnailGenerator()
    final_thumbnail_path = thumb_gen.create_thumbnail(
        str(video_file),
        matches,
        sub_text=sub_text,
        main_text=main_text
    )
    print(f"\n✅ [3단계 성공] 어그로 썸네일 생성 완료 -> {final_thumbnail_path}")

    # -------------------------------------------------------------
    # 5단계: 유튜브 자동 업로드 (YouTube Data API v3)
    # -------------------------------------------------------------
    if skip_upload:
        print("\n⏩ [--skip-upload] 유튜브 업로드 단계를 건너뜁니다.")
        upload_result = {"status": "skipped", "reason": "user_flag"}
    else:
        uploader = YouTubeUploader()
        upload_result = uploader.upload_video(
            video_path=final_video_path,
            thumbnail_path=final_thumbnail_path,
            metadata=metadata,
            dry_run=dry_run
        )

    # -------------------------------------------------------------
    # 최종 결과 요약 리포트
    # -------------------------------------------------------------
    print("\n" + "=" * 70)
    print(" 🎉 모든 파이프라인 작업이 성공적으로 완료되었습니다! 🎉")
    print("=" * 70)
    print(f" 📹 최종 영상 : {final_video_path}")
    print(f" 🖼️ 썸네일   : {final_thumbnail_path}")
    print(f" 📝 메타데이터 : {config.OUTPUT_DIR / config.METADATA_FILENAME}")
    print(f" 🏷️ 영상 제목 : {metadata.get('title')}")
    if upload_result.get("status") == "success":
        print(f" 🚀 유튜브 링크: {upload_result.get('watch_url')} (일부공개)")
    elif upload_result.get("status") == "dry_run_success":
        print(f" 🚀 [DRY RUN] 유튜브 업로드 파라미터 검증 완료")
    else:
        print(f" 💡 유튜브 업로드: 로컬 파일 보관 (사유: {upload_result.get('reason')})")
    print("=" * 70 + "\n")


def main():
    parser = argparse.ArgumentParser(
        description="포켓몬 챔피언스 테디님 스타일 자동 편집 및 유튜브 업로드 파이프라인"
    )
    parser.add_argument(
        "video_path",
        nargs="?",
        help="입력 녹화본 비디오 파일 (.mp4)"
    )
    parser.add_argument(
        "--skip-upload",
        action="store_true",
        help="유튜브 업로드를 건너뛰고 로컬 파일(영상/썸네일/메타데이터)만 생성합니다."
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="실제 유튜브 채널에 업로드하지 않고 업로드 요청 정보만 시뮬레이션합니다."
    )
    parser.add_argument(
        "--threshold",
        type=float,
        default=config.TEMPLATE_MATCH_THRESHOLD,
        help=f"승리 화면 템플릿 매칭 임계값 (기본값: {config.TEMPLATE_MATCH_THRESHOLD})"
    )
    parser.add_argument(
        "--template",
        type=str,
        default=None,
        help="커스텀 win_template.png 이미지 경로"
    )

    args = parser.parse_args()

    # 인자가 없을 경우 input 폴더나 드래그 앤 드롭 안내
    if not args.video_path:
        input_dir = config.BASE_DIR / "input"
        input_dir.mkdir(exist_ok=True)
        mp4_files = list(input_dir.glob("*.mp4"))
        if mp4_files:
            args.video_path = str(mp4_files[0])
            print(f"ℹ️ input 폴더에서 영상을 감지했습니다: {args.video_path}")
        else:
            print_banner()
            print("❌ 입력 영상 파일이 지정되지 않았습니다.")
            print("사용법:")
            print("  1) 영상을 run.bat 위로 드래그 앤 드롭")
            print("  2) CLI 실행: python main.py <영상경로.mp4>")
            print("  3) input/ 폴더에 .mp4 영상을 넣고 python main.py 실행\n")
            sys.exit(1)

    run_pipeline(
        video_path=args.video_path,
        skip_upload=args.skip_upload,
        dry_run=args.dry_run,
        threshold=args.threshold,
        template_path=args.template
    )


if __name__ == "__main__":
    main()
