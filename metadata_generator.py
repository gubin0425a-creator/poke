"""
4단계: SEO 메타데이터 생성 (Gemini API)
- google-generativeai를 사용해 Gemini 모델 호출
- 프롬프트: '입력된 영상 정보를 바탕으로 테디님 스타일의 자극적인 영상 제목,
  호기심을 유발하는 설명(3경기 타임라인 포함), 검색 최적화(SEO) 해시태그 15개를 JSON 포맷으로 작성해 줘.'
- metadata.json으로 저장
"""
import os
import json
import re
from pathlib import Path
from typing import Dict, List, Optional

import config

try:
    import google.generativeai as genai
    HAS_GENAI = True
except ImportError:
    HAS_GENAI = False


class TeddyMetadataGenerator:
    def __init__(
        self,
        api_key: Optional[str] = None,
        model_name: str = config.GEMINI_MODEL_NAME,
        output_dir: Optional[Path] = None
    ):
        self.api_key = api_key or os.environ.get("GEMINI_API_KEY") or config.GEMINI_API_KEY
        self.model_name = model_name
        self.output_dir = output_dir or config.OUTPUT_DIR
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def _generate_fallback_metadata(self, matches: List[Dict]) -> Dict:
        """
        API 키가 없거나 호출 실패 시 테디님 스타일의 기본 고품질 메타데이터를 자동 생성합니다.
        """
        match_count = len(matches) if matches else 3
        timeline_lines = []
        accumulated_time = 0.0

        for i, m in enumerate(matches, start=1):
            m_min = int(accumulated_time // 60)
            m_sec = int(accumulated_time % 60)
            timeline_lines.append(f"{m_min:02d}:{m_sec:02d} 경기 {i}: 상대 멘탈 터뜨린 기적의 결정타")
            # 추정 시간 누적
            accumulated_time += m.get("duration", 60.0) / 2.0

        if not timeline_lines:
            timeline_lines = [
                "00:00 경기 1: 턴 대기 없이 몰아치는 폭풍 공격!",
                "01:30 경기 2: 방심한 상대를 완전히 무너뜨린 한 방",
                "03:15 경기 3: 기적의 1HP 대역전승"
            ]

        timeline_text = "\n".join(timeline_lines)

        return {
            "title": f"[포챔스] 상대 멘탈 완전히 박살낸 레전드 {match_count}경기 모음 ㅋㅋㅋ (역대급 올킬)",
            "description": (
                f"포켓몬 챔피언스 역대급 사이다 경기 모음집!\n"
                f"상대의 완벽한 설계를 무너뜨리고 멘탈을 털어버린 명경기들만 압축했습니다.\n\n"
                f"📌 [경기 타임라인]\n{timeline_text}\n\n"
                f"구독과 좋아요, 알림 설정은 다음 영상을 만드는 큰 힘이 됩니다! ⚡🔥\n"
                f"#포챔스 #포켓몬스터 #실전배틀 #테디"
            ),
            "tags": [
                "포챔스", "포켓몬 챔피언스", "포켓몬", "포켓몬스터", "테디",
                "실전배틀", "포켓몬배틀", "닌텐도스위치", "포켓몬게임",
                "사이다", "대역전승", "올킬", "포챔스하이라이트", "포켓몬하이라이트", "게임"
            ],
            "sub_text": "상대 멘탈 터진 역대급 레전드 경기 ㄷㄷ",
            "main_text": "이 포켓몬 하나로 올킬?!"
        }

    def generate_metadata(
        self,
        matches: List[Dict],
        video_duration: float = 300.0,
        output_filename: str = config.METADATA_FILENAME
    ) -> Dict:
        """
        Gemini API를 호출하여 테디님 스타일의 제목, 설명문(타임라인 포함), SEO 태그 15개를 생성합니다.
        """
        print(f"\n[4단계: SEO 메타데이터 생성 (Gemini API)]")

        if not self.api_key:
            print("   ⚠️ GEMINI_API_KEY 환경변수가 설정되지 않았습니다.")
            print("   -> 테디님 스타일 프리셋 메타데이터로 안전하게 생성합니다.")
            metadata = self._generate_fallback_metadata(matches)
        elif not HAS_GENAI:
            print("   ⚠️ google.generativeai 라이브러리가 설치되지 않았습니다. 기본 메타데이터 생성.")
            metadata = self._generate_fallback_metadata(matches)
        else:
            try:
                genai.configure(api_key=self.api_key)
                model = genai.GenerativeModel(self.model_name)

                # 경기 정보 요약
                match_summary = []
                for i, m in enumerate(matches, start=1):
                    match_summary.append(
                        f"- 경기 {i}: 시작 {m['start_time']}초, 결정타 {m['finishing_blow_start']}초, 승리감지 {m['win_time']}초"
                    )
                matches_str = "\n".join(match_summary) if match_summary else "총 3경기 승리 경기 포함"

                prompt = f"""
당신은 대한민국 최고 인기 게임 유튜버 '테디님' 전담 유튜브 알고리즘/SEO 전문가입니다.
입력된 영상 정보를 바탕으로 테디님 스타일의 자극적이고 클릭을 부르는 영상 제목, 호기심을 유발하는 설명(3경기 타임라인 포함), 검색 최적화(SEO) 해시태그 15개를 JSON 포맷으로 작성해 줘.

[영상 정보]
- 게임: 포켓몬 챔피언스 (포챔스)
- 총 경기 수: {len(matches)}경기
- 영상 특징: 지루한 턴 대기 구간은 4배속 압축, 마지막 승리 결정타 순간은 1.2배 화면 줌인과 함께 클라이맥스 연출
- 승리 경기 정보:
{matches_str}

[작성 지침]
1. title: 테디님 특유의 텐션 높고 호기심을 자극하는 제목 (대괄호 태그 포함, 100자 이내)
   예: [포챔스] 상대 멘탈 완전히 박살낸 역대급 레전드 경기 ㅋㅋㅋ
2. description: 흥미진진한 인트로, 3경기(또는 승리 경기들)의 타임라인(00:00 형식), 구독 유도 문구 포함
3. tags: 유튜브 검색 노출을 극대화할 수 있는 관련성 높은 한국어 해시태그 정확히 15개 배열
4. sub_text: 썸네일 상단에 들어갈 짧고 강렬한 서브 카피 (예: "상대 멘탈 터진 역대급 경기 ㄷㄷ")
5. main_text: 썸네일 중앙에 크게 박힐 핵심 어그로 카피 (예: "이 포켓몬 하나로 올킬?!")

[출력 형식]
반드시 다음 키를 가진 순수 JSON 형태로만 응답하세요:
{{
  "title": "...",
  "description": "...",
  "tags": ["태그1", "태그2", ..., "태그15"],
  "sub_text": "...",
  "main_text": "..."
}}
"""
                print("   * Gemini API에 프롬프트 전송 중...")
                response = model.generate_content(prompt)
                raw_text = response.text.strip()

                # JSON 블록 파싱 (```json ... ``` 대응)
                clean_json = re.sub(r"^```json\s*", "", raw_text, flags=re.MULTILINE)
                clean_json = re.sub(r"```$", "", clean_json, flags=re.MULTILINE).strip()

                metadata = json.loads(clean_json)

                # 필수 키 누락 방지 보정
                if "tags" not in metadata or len(metadata["tags"]) < 5:
                    metadata["tags"] = self._generate_fallback_metadata(matches)["tags"]
                if "sub_text" not in metadata:
                    metadata["sub_text"] = "상대 멘탈 터진 역대급 레전드 경기 ㄷㄷ"
                if "main_text" not in metadata:
                    metadata["main_text"] = "이 포켓몬 하나로 올킬?!"

                print("   * Gemini API 메타데이터 생성 성공!")

            except Exception as e:
                print(f"   ⚠️ Gemini API 호출 중 오류 발생: {e}")
                print("   -> 테디님 스타일 기본 메타데이터로 대체합니다.")
                metadata = self._generate_fallback_metadata(matches)

        # JSON 파일로 저장
        output_path = str((self.output_dir / output_filename).resolve())
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(metadata, f, ensure_ascii=False, indent=2)

        print(f"✨ [4단계 완료] 메타데이터 생성 성공!")
        print(f" - 제목: {metadata.get('title')}")
        print(f" - 해시태그 수: {len(metadata.get('tags', []))}개")
        print(f" - 저장 위치: {output_path}")

        return metadata


if __name__ == "__main__":
    gen = TeddyMetadataGenerator()
    data = gen.generate_metadata([])
    print("생성된 메타데이터:\n", json.dumps(data, ensure_ascii=False, indent=2))
