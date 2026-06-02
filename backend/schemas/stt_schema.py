# 음성 STT 결과 구조
from typing import List
from pydantic import BaseModel

from schemas.common_schema import CommonDocumentSchema


# transcription 배열 안에 들어가는 대사 하나의 구조
class TranscriptionItem(BaseModel):
    start: str       # 대사 시작 시간
    end: str         # 대사 종료 시간
    speaker: str     # 화자 구분, 현재는 UNKNOWN
    text: str        # STT가 추출한 실제 텍스트


# STT 처리 관련 메타데이터
class STTMetadata(BaseModel):
    duration_sec: float              # 실제 원본 오디오 길이, 초 단위
    original_format: str             # 원본 파일 확장자
    model_used: str                  # 사용한 STT 모델명
    vad_applied: bool                # VAD 적용 여부
    initial_prompt_applied: bool     # initial prompt 적용 여부
    total_time_sec: float            # STT 처리에 걸린 시간
    compute_type: str                # 연산 타입, 예: int8


# 최종 STT 결과 구조
class STTResultSchema(CommonDocumentSchema):
    transcription: List[TranscriptionItem]
    metadata: STTMetadata