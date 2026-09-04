"""
Configuration settings for Pokémon Champions Video Automation Pipeline.
"""
import os
import sys
from pathlib import Path

# Windows 콘솔 출력(CP949) 이모지 인코딩 오류 방지
if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

# Base directories
BASE_DIR = Path(__file__).resolve().parent
ASSETS_DIR = BASE_DIR / "assets"
OUTPUT_DIR = BASE_DIR / "output"
TEMP_DIR = BASE_DIR / "temp"

# Ensure runtime directories exist
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
TEMP_DIR.mkdir(parents=True, exist_ok=True)
ASSETS_DIR.mkdir(parents=True, exist_ok=True)

# 1단계: 승리 경기 감지 (OpenCV)
WIN_TEMPLATE_PATH = ASSETS_DIR / "win_template.png"
TEMPLATE_MATCH_THRESHOLD = 0.70    # 템플릿 매칭 유사도 임계값 (0.0 ~ 1.0)
FRAME_SAMPLE_INTERVAL = 0.5        # 비디오 스캔 간격 (초 단위, 빠르고 정확한 스캔)
MIN_MATCH_SEPARATION = 10.0        # 같은 승리 화면 중복 감지 방지 간격 (초)
DEFAULT_MATCH_MAX_DURATION = 300.0 # 경기 최대 길이 추정치 (5분)
WIN_AFTER_MARGIN = 2.0             # 승리 화면 이후 포함할 여유 시간 (초)

# 2단계: 테디님 템포 자동 편집 (auto-editor + MoviePy)
AUDIO_THRESHOLD = "4%"             # auto-editor 무음 기준 볼륨
SILENT_SPEED = 4                   # 무음 구간 배속 (4배속)
SOUNDED_SPEED = 1                  # 소리 구간 배속 (1배속)
FINISHING_BLOW_DURATION = 5.0      # 결정타 구간 길이 (승리 직전 5초)
ZOOM_FACTOR = 1.2                  # 결정타 화면 중앙 줌인 배율 (1.2배)
TARGET_FPS = 30                    # 출력 영상 프레임레이트

# 3단계: 어그로 썸네일 생성 (Pillow)
THUMBNAIL_WIDTH = 1280
THUMBNAIL_HEIGHT = 720
FONT_PATH = "C:/Windows/Fonts/malgunbd.ttf"  # 맑은 고딕 볼드
FALLBACK_FONT_PATH = "C:/Windows/Fonts/malgun.ttf"
COLOR_SUB_TEXT = "#FFFFFF"         # 상단 서브 텍스트: 흰색
COLOR_MAIN_TEXT = "#FFE812"        # 중앙 메인 텍스트: 테디님 시그니처 형광 노란색
COLOR_STROKE = "#000000"           # 테두리 스트로크: 검은색
STROKE_WIDTH_SUB = 8               # 서브 텍스트 테두리 두께
STROKE_WIDTH_MAIN = 18             # 메인 텍스트 매우 두꺼운 테두리 두께

# 4단계: SEO 메타데이터 생성 (Gemini API)
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
GEMINI_MODEL_NAME = "gemini-1.5-flash"  # 빠르고 안정적인 모델

# 5단계: 유튜브 업로드 (YouTube Data API v3)
CLIENT_SECRETS_FILE = BASE_DIR / "client_secrets.json"
TOKEN_PICKLE_FILE = BASE_DIR / "token.pickle"
YOUTUBE_UPLOAD_SCOPE = ["https://www.googleapis.com/auth/youtube.upload"]
YOUTUBE_API_SERVICE_NAME = "youtube"
YOUTUBE_API_VERSION = "v3"
DEFAULT_PRIVACY_STATUS = "unlisted"  # 일부공개
YOUTUBE_CATEGORY_ID = "20"           # 20 = Gaming (게임)

# Output File Names
FINAL_VIDEO_FILENAME = "final_video.mp4"
FINAL_THUMBNAIL_FILENAME = "final_thumbnail.jpg"
METADATA_FILENAME = "metadata.json"
