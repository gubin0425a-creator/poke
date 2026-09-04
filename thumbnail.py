"""
3단계: 어그로 썸네일 자동 생성 (Pillow)
- 결정타 구간의 프레임 하나를 캡처해 썸네일 배경으로 활용
- Pillow를 사용해 '맑은 고딕 볼드(malgunbd.ttf)' 폰트로 텍스트 합성
- 상단 서브 텍스트: 흰색 글씨 + 두꺼운 검은색 테두리(Stroke)
- 중앙 메인 텍스트: 테디님 시그니처 형광 노란색(#FFE812) 글씨 + 매우 두꺼운 검은색 테두리
- final_thumbnail.jpg로 저장
"""
import os
import cv2
import numpy as np
from pathlib import Path
from typing import Optional, Dict, List
from PIL import Image, ImageDraw, ImageFont, ImageEnhance, ImageFilter

import config


class TeddyThumbnailGenerator:
    def __init__(
        self,
        font_path: str = config.FONT_PATH,
        fallback_font_path: str = config.FALLBACK_FONT_PATH,
        width: int = config.THUMBNAIL_WIDTH,
        height: int = config.THUMBNAIL_HEIGHT,
        output_dir: Optional[Path] = None
    ):
        self.font_path = font_path
        self.fallback_font_path = fallback_font_path
        self.width = width
        self.height = height
        self.output_dir = output_dir or config.OUTPUT_DIR
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.font_file = self._resolve_font()

    def _resolve_font(self) -> str:
        """사용 가능한 볼드 폰트 경로를 찾습니다."""
        candidates = [
            self.font_path,
            self.fallback_font_path,
            "C:/Windows/Fonts/malgunbd.ttf",
            "C:/Windows/Fonts/malgun.ttf",
            "C:/Windows/Fonts/arialbd.ttf"
        ]
        for c in candidates:
            if os.path.exists(c):
                return c
        return "arial.ttf"

    def extract_finishing_frame(self, video_path: str, matches: List[Dict]) -> Image.Image:
        """
        결정타 구간(승리 직전 2.5초)의 프레임 한 장을 캡처하여 PIL Image로 반환합니다.
        """
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            raise RuntimeError(f"영상을 열 수 없습니다: {video_path}")

        # 가장 극적인 경기(첫 번째 경기 또는 마지막 경기)의 결정타 순간 프레임 추출
        target_time = 5.0
        if matches:
            chosen_match = matches[0]
            # 승리 감지 시점 기준 2.5초 전 (결정타의 정점)
            target_time = max(0.0, chosen_match.get("win_time", 10.0) - 2.5)

        cap.set(cv2.CAP_PROP_POS_MSEC, target_time * 1000.0)
        ret, frame = cap.read()
        cap.release()

        if not ret or frame is None:
            # 프레임 캡처 실패 시 기본 그라디언트 배경 생성
            print("   ⚠️ 결정타 프레임 캡처 실패, 기본 배틀 배경 생성")
            img = Image.new("RGB", (self.width, self.height), color=(25, 30, 60))
        else:
            # BGR -> RGB
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            img = Image.fromarray(frame_rgb)

        return img.resize((self.width, self.height), Image.Resampling.LANCZOS)

    def enhance_image(self, img: Image.Image) -> Image.Image:
        """
        유튜브 썸네일 특유의 쨍하고 강렬한 색감(채도 1.25x, 대비 1.15x)으로 보정합니다.
        """
        enhancer = ImageEnhance.Color(img)
        img = enhancer.enhance(1.25)

        enhancer = ImageEnhance.Contrast(img)
        img = enhancer.enhance(1.15)
        return img

    def add_vignette_and_overlays(self, img: Image.Image) -> Image.Image:
        """
        텍스트 가독성을 극대화하기 위해 상단과 하단에 부드러운 다크 그라데이션 및 비네팅을 추가합니다.
        """
        overlay = Image.new("RGBA", (self.width, self.height), (0, 0, 0, 0))
        draw = ImageDraw.Draw(overlay)

        # 상단 텍스트 배경을 위한 은은한 다크 그라데이션
        for y in range(200):
            alpha = int(140 * (1.0 - y / 200.0))
            draw.line([(0, y), (self.width, y)], fill=(0, 0, 0, alpha))

        # 하단 텍스트 배경을 위한 은은한 다크 그라데이션
        for y in range(self.height - 240, self.height):
            progress = (y - (self.height - 240)) / 240.0
            alpha = int(170 * progress)
            draw.line([(0, y), (self.width, y)], fill=(0, 0, 0, alpha))

        img = img.convert("RGBA")
        img = Image.alpha_composite(img, overlay)
        return img.convert("RGB")

    def create_thumbnail(
        self,
        video_path: str,
        matches: List[Dict],
        sub_text: str = "상대 멘탈 터진 역대급 레전드 경기 ㄷㄷ",
        main_text: str = "이 포켓몬 하나로 올킬?!",
        output_filename: str = config.FINAL_THUMBNAIL_FILENAME
    ) -> str:
        """
        어그로 썸네일을 생성하여 final_thumbnail.jpg로 저장합니다.
        """
        print(f"\n[3단계: 어그로 썸네일 생성 시작]")
        print(f" - 상단 서브 텍스트: {sub_text}")
        print(f" - 중앙 메인 텍스트: {main_text}")
        print(f" - 폰트: {self.font_file}")

        # 1) 프레임 캡처
        raw_bg = self.extract_finishing_frame(video_path, matches)

        # 2) 화질 및 색감 보정 + 비네팅
        enhanced_bg = self.enhance_image(raw_bg)
        final_bg = self.add_vignette_and_overlays(enhanced_bg)

        draw = ImageDraw.Draw(final_bg)

        # 3) 폰트 로드
        try:
            sub_font = ImageFont.truetype(self.font_file, 52)
            main_font = ImageFont.truetype(self.font_file, 92)
            badge_font = ImageFont.truetype(self.font_file, 34)
        except Exception:
            sub_font = ImageFont.load_default()
            main_font = ImageFont.load_default()
            badge_font = ImageFont.load_default()

        # 4) 상단 중앙 테디 시그니처 뱃지 ([포챔스] / 레드 배너)
        badge_text = " 포챔스 "
        bbox = draw.textbbox((0, 0), badge_text, font=badge_font)
        bw, bh = bbox[2] - bbox[0], bbox[3] - bbox[1]
        badge_x = (self.width - bw - 24) // 2
        badge_y = 25
        draw.rounded_rectangle(
            [badge_x, badge_y, badge_x + bw + 24, badge_y + bh + 12],
            radius=8,
            fill=(230, 30, 30),
            outline=(255, 255, 255),
            width=3
        )
        draw.text((badge_x + 12, badge_y + 3), badge_text, font=badge_font, fill=(255, 255, 255))

        # 5) 상단 서브 텍스트 렌더링 (흰색 + 두꺼운 검은 테두리)
        sub_bbox = draw.textbbox((0, 0), sub_text, font=sub_font)
        sub_w = sub_bbox[2] - sub_bbox[0]
        sub_x = (self.width - sub_w) // 2
        sub_y = 85

        draw.text(
            (sub_x, sub_y),
            sub_text,
            font=sub_font,
            fill=config.COLOR_SUB_TEXT,
            stroke_width=config.STROKE_WIDTH_SUB,
            stroke_fill=config.COLOR_STROKE
        )

        # 6) 중앙 메인 텍스트 렌더링 (노란색 #FFE812 + 매우 두꺼운 검은 테두리)
        main_bbox = draw.textbbox((0, 0), main_text, font=main_font)
        main_w = main_bbox[2] - main_bbox[0]
        main_h = main_bbox[3] - main_bbox[1]
        main_x = (self.width - main_w) // 2
        main_y = (self.height - main_h) // 2 + 50

        draw.text(
            (main_x, main_y),
            main_text,
            font=main_font,
            fill=config.COLOR_MAIN_TEXT,
            stroke_width=config.STROKE_WIDTH_MAIN,
            stroke_fill=config.COLOR_STROKE
        )

        # 7) 이미지 저장
        output_path = str((self.output_dir / output_filename).resolve())
        final_bg.save(output_path, format="JPEG", quality=95)

        print(f"✨ [3단계 완료] 썸네일 생성 성공!")
        print(f" - 저장 위치: {output_path} (1280x720)")
        return output_path


if __name__ == "__main__":
    import sys
    gen = TeddyThumbnailGenerator()
    out = gen.create_thumbnail("test_video.mp4", [])
    print("썸네일 생성 완료:", out)
