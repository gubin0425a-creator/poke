"""
2단계: 테디님 템포 자동 편집 (auto-editor + MoviePy)
- auto-editor 서브프로세스를 호출하여 오디오 볼륨 4% 이하 구간(턴 대기/고민 시간)을 4배속으로 압축
- 각 경기의 마지막 결정타 순간(승리 직전 5초)은 1배속 복귀 + 화면 중앙 1.2배 줌인(Zoom-in)
- 승리 경기들을 모두 결합하여 약 5분 길이의 final_video.mp4로 렌더링
"""
import os
import shutil
import subprocess
from pathlib import Path
from typing import List, Dict, Optional

from moviepy.editor import VideoFileClip, concatenate_videoclips, vfx
import config


class TeddyVideoEditor:
    def __init__(
        self,
        audio_threshold: str = config.AUDIO_THRESHOLD,
        silent_speed: int = config.SILENT_SPEED,
        zoom_factor: float = config.ZOOM_FACTOR,
        target_fps: int = config.TARGET_FPS,
        temp_dir: Optional[Path] = None,
        output_dir: Optional[Path] = None
    ):
        self.audio_threshold = audio_threshold
        self.silent_speed = silent_speed
        self.zoom_factor = zoom_factor
        self.target_fps = target_fps
        self.temp_dir = temp_dir or config.TEMP_DIR
        self.output_dir = output_dir or config.OUTPUT_DIR
        self.temp_dir.mkdir(parents=True, exist_ok=True)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def _apply_zoom(self, clip: VideoFileClip, zoom: float) -> VideoFileClip:
        """
        화면 중앙을 기준으로 지정한 배율(1.2배 등)로 줌인(Zoom-in) 효과를 적용합니다.
        """
        w, h = clip.size
        w_crop = int(w / zoom)
        h_crop = int(h / zoom)
        x1 = int((w - w_crop) / 2)
        y1 = int((h - h_crop) / 2)
        x2 = x1 + w_crop
        y2 = y1 + h_crop

        # 중앙 크롭 후 원래 해상도로 리사이즈
        return clip.fx(vfx.crop, x1=x1, y1=y1, x2=x2, y2=y2).fx(vfx.resize, (w, h))

    def _run_auto_editor(self, input_path: str, output_path: str) -> bool:
        """
        auto-editor CLI를 서브프로세스로 실행하여 무음/저볼륨 구간을 4배속으로 압축합니다.
        """
        cmd = [
            "auto-editor",
            str(input_path),
            "--edit", f"audio:threshold={self.audio_threshold}",
            "--silent-speed", str(self.silent_speed),
            "--no-open",
            "-o", str(output_path)
        ]

        print(f"   [auto-editor 실행] {' '.join(cmd)}")
        try:
            result = subprocess.run(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                check=True
            )
            return True
        except subprocess.CalledProcessError as e:
            print(f"   ⚠️ auto-editor 실행 중 오류 발생: {e.stderr}")
            return False
        except FileNotFoundError:
            print("   ⚠️ auto-editor 실행 파일이 PATH에 없습니다. 원본 속도로 대체합니다.")
            return False

    def edit_matches(self, video_path: str, matches: List[Dict], output_filename: str = config.FINAL_VIDEO_FILENAME) -> str:
        """
        감지된 승리 경기들을 2단계 규칙(auto-editor 4배속 + 결정타 1.2배 줌인)에 맞춰 편집 후 합칩니다.
        
        Args:
            video_path: 원본 녹화본 파일 경로
            matches: 1단계에서 추출된 승리 경기 목록
            output_filename: 출력될 최종 영상 파일명
            
        Returns:
            str: 렌더링 완료된 최종 영상의 절대 경로
        """
        if not matches:
            raise ValueError("편집할 승리 경기 정보가 없습니다. (1단계 검출 결과 0건)")

        video_path = str(Path(video_path).resolve())
        final_output_path = str((self.output_dir / output_filename).resolve())
        print(f"\n[2단계: 테디님 템포 편집 시작]")
        print(f" - 대상 승리 경기: 총 {len(matches)}경기")
        print(f" - 무음 구간 압축 배율: {self.silent_speed}배속 (임계값 {self.audio_threshold})")
        print(f" - 결정타 구간: 1.0배속 복귀 + {self.zoom_factor}배 화면 중앙 줌인")

        # 클립 리스트 및 임시 파일 추적
        processed_match_clips = []
        temp_files_to_clean = []
        opened_clips_to_close = []

        try:
            for idx, m in enumerate(matches, start=1):
                print(f"\n --- [경기 {idx}/{len(matches)}] 편집 처리 중 ---")
                b_start = m["battle_start"]
                b_end = m["battle_end"]
                f_start = m["finishing_blow_start"]
                m_end = m["end_time"]

                # 1) 배틀 구간 추출 및 auto-editor 4배속 압축
                battle_duration = b_end - b_start
                battle_clip = None

                if battle_duration > 0.5:
                    temp_raw_path = str(self.temp_dir / f"temp_m{idx}_raw_battle.mp4")
                    temp_sped_path = str(self.temp_dir / f"temp_m{idx}_sped_battle.mp4")
                    temp_files_to_clean.extend([temp_raw_path, temp_sped_path])

                    print(f"   * 배틀 구간 클립 추출: {b_start:.1f}초 ~ {b_end:.1f}초 (길이 {battle_duration:.1f}초)")
                    with VideoFileClip(video_path) as raw_video:
                        raw_battle = raw_video.subclip(b_start, b_end)
                        raw_battle.write_videofile(
                            temp_raw_path,
                            fps=self.target_fps,
                            codec="libx264",
                            audio_codec="aac",
                            logger=None
                        )

                    # auto-editor 무음 4배속 압축
                    success = self._run_auto_editor(temp_raw_path, temp_sped_path)
                    if success and os.path.exists(temp_sped_path):
                        battle_clip = VideoFileClip(temp_sped_path)
                        opened_clips_to_close.append(battle_clip)
                        print(f"   * auto-editor 4배속 압축 성공! (새 길이: {battle_clip.duration:.1f}초)")
                    else:
                        print("   * auto-editor fallback: 원본 배틀 클립 사용")
                        battle_clip = VideoFileClip(temp_raw_path)
                        opened_clips_to_close.append(battle_clip)

                # 2) 결정타 순간 1배속 유지 + 1.2배 화면 중앙 줌인
                print(f"   * 결정타 구간 줌인 처리: {f_start:.1f}초 ~ {m_end:.1f}초 (길이 {m_end - f_start:.1f}초)")
                raw_finishing_clip = VideoFileClip(video_path).subclip(f_start, m_end)
                opened_clips_to_close.append(raw_finishing_clip)
                zoomed_finishing_clip = self._apply_zoom(raw_finishing_clip, self.zoom_factor)

                # 3) 한 경기 결합 (배틀 구간 + 결정타 줌인)
                match_parts = []
                if battle_clip is not None:
                    match_parts.append(battle_clip)
                match_parts.append(zoomed_finishing_clip)

                match_combined = concatenate_videoclips(match_parts, method="compose")
                processed_match_clips.append(match_combined)
                print(f"   -> [경기 {idx} 편집 완료] 총 길이: {match_combined.duration:.1f}초")

            # 4) 모든 승리 경기들을 하나의 최종 영상으로 결합
            print(f"\n[최종 렌더링] 모든 경기 결합 및 {output_filename} 렌더링 중...")
            final_video = concatenate_videoclips(processed_match_clips, method="compose")
            
            temp_audio = str(self.temp_dir / "temp-audio.m4a")
            final_video.write_videofile(
                final_output_path,
                fps=self.target_fps,
                codec="libx264",
                audio_codec="aac",
                temp_audiofile=temp_audio,
                remove_temp=True,
                threads=4,
                logger="bar"
            )

            print(f"✨ [2단계 완료] 최종 영상 렌더링 성공!")
            print(f" - 저장 위치: {final_output_path}")
            print(f" - 최종 영상 길이: {final_video.duration/60:.2f}분 ({final_video.duration:.1f}초)")

            # 자원 해제
            final_video.close()
            for c in processed_match_clips:
                try:
                    c.close()
                except Exception:
                    pass

        finally:
            for c in opened_clips_to_close:
                try:
                    c.close()
                except Exception:
                    pass
            # 임시 파일 정리
            for f in temp_files_to_clean:
                try:
                    if os.path.exists(f):
                        os.remove(f)
                except Exception:
                    pass

        return final_output_path


if __name__ == "__main__":
    import sys
    print("editor.py는 main.py 또는 모듈로 호출됩니다.")
