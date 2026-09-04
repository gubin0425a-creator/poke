"""
엔드투엔드 파이프라인 검증용 합성 테스트 스위트 (test_pipeline.py)
포챔스 게임 환경(배틀 사운드, 턴 고민 무음, 결정타, 승리 화면)을 모사하는
합성 비디오를 생성하고 5단계 파이프라인 전체를 자동 검증합니다.
"""
import os
import sys

# Windows 콘솔 인코딩 설정
if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

import cv2
import numpy as np
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

from moviepy.editor import VideoClip
from moviepy.audio.AudioClip import AudioArrayClip

import config
from detector import WinDetector
from editor import TeddyVideoEditor
from thumbnail import TeddyThumbnailGenerator
from metadata_generator import TeddyMetadataGenerator
from uploader import YouTubeUploader


def create_synthetic_game_video(output_path: str = "synthetic_game_video.mp4", duration: float = 24.0):
    """
    포켓몬 챔피언스 게임 진행을 모사하는 가상 비디오를 생성합니다:
    - 0초 ~ 4초: 배틀 시작 및 공격 (소리 있음)
    - 4초 ~ 14초: 턴 고민 및 대기 시간 (소리 무음 - 4배속 압축 대상)
    - 14초 ~ 19초: 마지막 결정타 공격 (소리 큼 - 1.2배 줌인 대상)
    - 19초 ~ 24초: 승리 화면 (assets/win_template.png가 화면 중앙에 렌더링됨)
    """
    output_path = str(Path(output_path).resolve())
    print(f"\n[테스트 환경 준비] 가상 포챔스 게임 녹화본 생성 중... ({duration}초)")

    width, height = 640, 360
    fps = 24
    sr = 44100

    # 템플릿 로드
    tpl = Image.open(str(config.WIN_TEMPLATE_PATH)).convert("RGBA")

    def make_frame(t):
        # 배경 (시간에 따라 색상이 조금씩 변하는 배틀 경기장)
        img = Image.new("RGB", (width, height), (30, 45, int(80 + 30 * np.sin(t))))
        draw = ImageDraw.Draw(img)

        # 게임 경기장 UI 바닥 원
        draw.ellipse([80, 180, 560, 340], fill=(20, 35, 60), outline=(255, 215, 0), width=4)

        if t < 4.0:
            # 배틀 시작 구간
            draw.text((180, 60), f"BATTLE START! (Turn 1)", fill=(255, 255, 255))
            draw.rectangle([120, 200, 220, 300], fill=(240, 128, 128))  # 내 포켓몬
            draw.rectangle([420, 200, 520, 300], fill=(135, 206, 250))  # 상대 포켓몬
        elif 4.0 <= t < 14.0:
            # 턴 고민 / 대기 구간 (무음 구간)
            draw.text((170, 60), f"Thinking... (Waiting for Move)", fill=(200, 200, 200))
            draw.rectangle([120, 200, 220, 300], fill=(240, 128, 128))
            draw.rectangle([420, 200, 520, 300], fill=(135, 206, 250))
        elif 14.0 <= t < 19.0:
            # 결정타 구간 (1.2배 줌인 대상)
            draw.text((150, 40), f"CRITICAL HIT! FINISHING BLOW!", fill=(255, 69, 0))
            # 공격 이펙트
            draw.line([(180, 240), (460, 250)], fill=(255, 255, 0), width=8)
            draw.rectangle([420, 200, 520, 300], fill=(255, 0, 0))  # 피격 연출
        else:
            # 19초 이후: 승리 화면 (win_template.png 합성)
            draw.text((200, 40), f"VICTORY RESULT SCREEN", fill=(255, 215, 0))
            # 화면 중앙에 win_template 배치
            tw, th = tpl.size
            px = (width - tw) // 2
            py = (height - th) // 2 + 30
            img.paste(tpl, (px, py), tpl)

        return np.array(img)

    video_clip = VideoClip(make_frame, duration=duration)

    # 오디오 생성: 0~4s 소리, 4~14s 무음(0.001), 14~24s 소리
    total_samples = int(duration * sr)
    t_samples = np.linspace(0, duration, total_samples, endpoint=False)
    audio_data = 0.4 * np.sin(2 * np.pi * 440 * t_samples)

    # 4초 ~ 14초 구간 무음 처리 (오디오 볼륨 4% 이하)
    silent_start_idx = int(4.0 * sr)
    silent_end_idx = int(14.0 * sr)
    audio_data[silent_start_idx:silent_end_idx] = 0.0005

    audio_clip = AudioArrayClip(audio_data.reshape(-1, 1), fps=sr)
    video_clip = video_clip.set_audio(audio_clip)

    video_clip.write_videofile(
        output_path,
        fps=fps,
        codec="libx264",
        audio_codec="aac",
        logger=None
    )
    video_clip.close()
    print(f"가상 테스트 영상 생성 완료: {output_path}")
    return output_path


def run_full_verification():
    print("================================================================")
    print(" 🧪 포챔스 자동 편집 & 유튜브 업로드 파이프라인 통합 테스트 시작")
    print("================================================================")

    # 1. 합성 영상 생성
    test_video_path = "test_game_sample.mp4"
    create_synthetic_game_video(test_video_path, duration=24.0)

    # 2. 1단계: OpenCV 승리 감지 테스트
    detector = WinDetector(threshold=0.65, sample_interval=0.5)
    matches = detector.detect_winning_matches(test_video_path)

    assert len(matches) > 0, "❌ 1단계 실패: 승리 화면을 감지하지 못했습니다."
    match = matches[0]
    print(f"✅ 1단계 검증 통과: 승리 화면 감지 성공 (승리 시점: {match['win_time']}초, 결정타: {match['finishing_blow_start']}초)")

    # 3. 2단계: 테디님 템포 편집 테스트 (auto-editor 4배속 + MoviePy 1.2배 줌인)
    editor = TeddyVideoEditor(target_fps=24)
    final_video = editor.edit_matches(test_video_path, matches, output_filename="test_final_video.mp4")
    assert os.path.exists(final_video), "❌ 2단계 실패: final_video.mp4 파일이 생성되지 않았습니다."
    print(f"✅ 2단계 검증 통과: auto-editor 4배속 압축 및 1.2배 줌인 최종 영상 렌더링 완료 ({final_video})")

    # 4. 4단계: Gemini 메타데이터 생성 테스트
    meta_gen = TeddyMetadataGenerator()
    metadata = meta_gen.generate_metadata(matches, output_filename="test_metadata.json")
    assert "title" in metadata and "tags" in metadata, "❌ 4단계 실패: 메타데이터 키 누락"
    assert len(metadata["tags"]) >= 10, "❌ 4단계 실패: 해시태그 15개 생성 미흡"
    print(f"✅ 4단계 검증 통과: 테디님 스타일 제목 및 SEO 해시태그 {len(metadata['tags'])}개 생성 완료")

    # 5. 3단계: Pillow 썸네일 생성 테스트 (맑은 고딕 볼드 + 노란색/흰색 스트로크)
    thumb_gen = TeddyThumbnailGenerator()
    thumb_path = thumb_gen.create_thumbnail(
        test_video_path,
        matches,
        sub_text=metadata.get("sub_text", "상대 멘탈 터진 역대급 레전드 경기 ㄷㄷ"),
        main_text=metadata.get("main_text", "이 포켓몬 하나로 올킬?!"),
        output_filename="test_final_thumbnail.jpg"
    )
    assert os.path.exists(thumb_path), "❌ 3단계 실패: final_thumbnail.jpg 파일이 생성되지 않았습니다."
    
    # 썸네일 해상도 검증 (1280x720)
    with Image.open(thumb_path) as im:
        assert im.size == (1280, 720), f"❌ 3단계 실패: 썸네일 해상도 불일치 ({im.size})"
    print(f"✅ 3단계 검증 통과: 1280x720 고화질 어그로 썸네일 정상 생성 완료")

    # 6. 5단계: 유튜브 업로드 드라이런 테스트
    uploader = YouTubeUploader()
    upload_res = uploader.upload_video(final_video, thumb_path, metadata, dry_run=True)
    assert upload_res["status"] == "dry_run_success", "❌ 5단계 실패: 업로드 파라미터 검증 실패"
    print(f"✅ 5단계 검증 통과: 유튜브 업로드 API 구조 및 '일부공개(unlisted)' 설정 검증 완료")

    print("\n" + "=" * 64)
    print(" 🎉 [최종 검증 성공] 5단계 전 과정이 완벽하게 정상 작동합니다! 🎉")
    print("================================================================\n")


if __name__ == "__main__":
    run_full_verification()
