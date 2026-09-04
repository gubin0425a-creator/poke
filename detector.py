"""
1단계: 승리 경기 감지 및 컷 분할 (OpenCV)
OpenCV 템플릿 매칭을 사용하여 포챔스 녹화본에서 승리(WIN) 결과창을 감지하고,
승리한 경기들의 시작~종료 및 결정타 타임스탬프를 추출합니다.
"""
import os
import cv2
import numpy as np
from pathlib import Path
from typing import List, Dict, Optional, Tuple

import config


class WinDetector:
    def __init__(
        self,
        template_path: Optional[str] = None,
        threshold: float = config.TEMPLATE_MATCH_THRESHOLD,
        sample_interval: float = config.FRAME_SAMPLE_INTERVAL,
        min_separation: float = config.MIN_MATCH_SEPARATION,
        finishing_blow_duration: float = config.FINISHING_BLOW_DURATION,
        win_after_margin: float = config.WIN_AFTER_MARGIN
    ):
        self.template_path = Path(template_path) if template_path else config.WIN_TEMPLATE_PATH
        self.threshold = threshold
        self.sample_interval = sample_interval
        self.min_separation = min_separation
        self.finishing_blow_duration = finishing_blow_duration
        self.win_after_margin = win_after_margin
        self.template_img = None
        self._load_template()

    def _load_template(self):
        """템플릿 이미지를 읽어 그레이스케일로 변환합니다."""
        if not self.template_path.exists():
            raise FileNotFoundError(
                f"승리 템플릿 이미지를 찾을 수 없습니다: {self.template_path}\n"
                f"assets/ 폴더에 'win_template.png'를 준비해 주세요."
            )
        template = cv2.imread(str(self.template_path), cv2.IMREAD_COLOR)
        if template is None:
            raise ValueError(f"템플릿 이미지를 읽을 수 없습니다: {self.template_path}")
        self.template_img = cv2.cvtColor(template, cv2.COLOR_BGR2GRAY)

    def _match_multiscale(self, frame_gray: np.ndarray) -> Tuple[float, Optional[Tuple[int, int]]]:
        """
        다양한 화면 해상도 및 배율 변화를 고려하여 다중 스케일 템플릿 매칭을 수행합니다.
        가장 높은 매칭 신뢰도와 위치를 반환합니다.
        """
        best_val = -1.0
        best_loc = None
        h_f, w_f = frame_gray.shape[:2]
        h_t, w_t = self.template_img.shape[:2]

        # 영상 해상도에 맞춰 템플릿 비율 조정 (0.5x, 0.75x, 1.0x, 1.25x, 1.5x)
        scales = [0.5, 0.75, 1.0, 1.25, 1.5]
        for scale in scales:
            new_w = int(w_t * scale)
            new_h = int(h_t * scale)
            if new_w >= w_f or new_h >= h_f or new_w < 10 or new_h < 10:
                continue

            resized_tpl = cv2.resize(self.template_img, (new_w, new_h), interpolation=cv2.INTER_AREA)
            res = cv2.matchTemplate(frame_gray, resized_tpl, cv2.TM_CCOEFF_NORMED)
            _, max_val, _, max_loc = cv2.minMaxLoc(res)

            if max_val > best_val:
                best_val = max_val
                best_loc = max_loc

        return best_val, best_loc

    def detect_winning_matches(self, video_path: str) -> List[Dict]:
        """
        영상 전체를 스캔하여 승리 경기들의 타임스탬프 구간을 추출합니다.
        
        Returns:
            List[Dict]: 승리 경기 목록. 각 항목은 다음 필드를 포함:
                - match_index: 1부터 시작하는 경기 인덱스
                - start_time: 경기 시작 타임스탬프 (초)
                - battle_start: 배틀/고민 구간 시작 (초)
                - battle_end: 배틀/고민 구간 종료 (초)
                - finishing_blow_start: 결정타 순간 시작 (초)
                - win_time: 승리 화면 최초 감지 시점 (초)
                - end_time: 경기 종료 시점 (초)
                - confidence: 매칭 신뢰도 (0.0 ~ 1.0)
        """
        video_path = str(Path(video_path).resolve())
        if not os.path.exists(video_path):
            raise FileNotFoundError(f"입력 비디오 파일을 찾을 수 없습니다: {video_path}")

        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            raise RuntimeError(f"비디오 파일을 열 수 없습니다: {video_path}")

        fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        duration = total_frames / fps
        frame_step = max(1, int(fps * self.sample_interval))

        print(f"\n[1단계: 승리 감지] 영상 분석 시작")
        print(f" - 파일: {os.path.basename(video_path)}")
        print(f" - 총 길이: {duration/60:.1f}분 ({duration:.1f}초), FPS: {fps:.1f}, 프레임수: {total_frames}")
        print(f" - 스캔 간격: {self.sample_interval}초마다 ({frame_step}프레임 단위)")
        print(f" - 매칭 임계값: {self.threshold:.2f}")

        detected_hits = []  # (timestamp, confidence)

        current_frame = 0
        while current_frame < total_frames:
            cap.set(cv2.CAP_PROP_POS_FRAMES, current_frame)
            ret, frame = cap.read()
            if not ret:
                break

            current_time = current_frame / fps
            frame_gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            conf, _ = self._match_multiscale(frame_gray)

            if conf >= self.threshold:
                detected_hits.append((current_time, conf))

            current_frame += frame_step

        cap.release()

        # 연속 감지된 승리 프레임들을 하나의 승리 이벤트로 클러스터링
        win_events = []
        for t, conf in detected_hits:
            if not win_events:
                win_events.append({"start_t": t, "end_t": t, "conf": conf})
            else:
                last_event = win_events[-1]
                if t - last_event["end_t"] <= self.min_separation:
                    # 같은 승리 화면이 지속되는 중
                    last_event["end_t"] = t
                    last_event["conf"] = max(last_event["conf"], conf)
                else:
                    win_events.append({"start_t": t, "end_t": t, "conf": conf})

        print(f" - 감지된 승리 화면 이벤트 수: {len(win_events)}개")

        # 각 승리 이벤트로부터 [시작 ~ 결정타 ~ 종료] 구간 계산
        matches = []
        prev_end_time = 0.0

        for idx, event in enumerate(win_events, start=1):
            win_time = event["start_t"]
            conf = event["conf"]

            # 경기 종료: 승리 화면 후 마진 포함
            match_end = min(duration, win_time + self.win_after_margin)

            # 경기 시작: 직전 경기 종료 시점 혹은 기본 경기 길이 제한
            match_start = max(prev_end_time, win_time - config.DEFAULT_MATCH_MAX_DURATION)
            # 최소 10초 이상의 유효 구간 보장
            if win_time - match_start < 10.0 and prev_end_time > 0:
                match_start = max(0.0, win_time - 30.0)

            # 결정타 순간: 승리 직전 5초 (또는 경기 시작 후)
            finishing_start = max(match_start, win_time - self.finishing_blow_duration)

            match_info = {
                "match_index": idx,
                "start_time": round(match_start, 2),
                "battle_start": round(match_start, 2),
                "battle_end": round(finishing_start, 2),
                "finishing_blow_start": round(finishing_start, 2),
                "win_time": round(win_time, 2),
                "end_time": round(match_end, 2),
                "duration": round(match_end - match_start, 2),
                "confidence": round(float(conf), 3)
            }
            matches.append(match_info)
            prev_end_time = match_end

            print(f"   [승리 경기 #{idx}] {match_start/60:.1f}분 ~ {match_end/60:.1f}분 "
                  f"(승리감지: {win_time:.1f}초, 결정타: {finishing_start:.1f}초~{match_end:.1f}초, 신뢰도: {conf:.2f})")

        return matches


if __name__ == "__main__":
    import sys
    test_video = sys.argv[1] if len(sys.argv) > 1 else "test_video.mp4"
    if os.path.exists(test_video):
        detector = WinDetector()
        results = detector.detect_winning_matches(test_video)
        print("검출 결과:", results)
    else:
        print("사용법: python detector.py <비디오_경로>")
