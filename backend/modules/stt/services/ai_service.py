# services/ai_service.py
from pyannote.audio import Pipeline
from faster_whisper import WhisperModel
from config import HF_AUTH_TOKEN
import torch  # 💡 [추가] GPU 제어를 위해 PyTorch를 불러옵니다.

print("🚀 [System] AI 모델 2개를 메모리에 로드 중입니다. (시간이 조금 걸립니다)...")

# 1. STT 엔진 로드 
# (faster-whisper는 CTranslate2 기반으로 이미 Mac CPU에 최적화되어 있어 CPU로 유지합니다)
print("-> 1/2: faster-whisper 로드 중...")
whisper_model = WhisperModel("large-v3-turbo", device="cpu", compute_type="int8")

# 2. 화자 분리 엔진 로드
print("-> 2/2: pyannote 화자 분리 모델 로드 중...")
try:
    diarization_pipeline = Pipeline.from_pretrained(
        "pyannote/speaker-diarization-3.1",
        token=HF_AUTH_TOKEN
    )
    if diarization_pipeline is None:
        print("❌ [Fatal Error] 모델이 껍데기(None) 상태입니다. 허깅페이스 약관 동의 및 토큰을 확인하세요!")
    else:
        # ==============================================================
        # 🚀 [핵심] 맥북 M칩 GPU(MPS) 가속 활성화 로직
        # ==============================================================
        if torch.backends.mps.is_available():
            print("⚡ [System] 애플 실리콘 GPU(MPS) 가속 엔진을 장착합니다! (속도 대폭 향상) ⚡")
            diarization_pipeline.to(torch.device("mps"))
        else:
            print("⚠️ [System] MPS를 사용할 수 없어 기본 CPU로 구동합니다.")
            
        print("✅ [System] 모든 모델 로드 완료! 서버 준비 완료.")
        
except Exception as e:
    print(f"❌ [Error] 화자 분리 모델 로드 실패: {e}")
    diarization_pipeline = None


def process_audio_with_ai(wav_path: str, topic: str) -> list:
    """
    화자 분리(pyannote)와 STT(Whisper)를 동시에 수행하고 결과를 병합합니다.
    """
    if not diarization_pipeline:
        raise RuntimeError("Pyannote 모델이 로드되지 않아 분석을 실행할 수 없습니다.")
        
    # ----------------------------------------------------
    # 공정 1: 화자 분리 (MPS 가속 적용됨!)
    # ----------------------------------------------------
    print("🔍 [1단계] 화자 분리 분석 중 (GPU 가속 작동 중)...")
    diarization = diarization_pipeline(wav_path)
    
    # ----------------------------------------------------
    # 공정 2: STT 추출 (주제 반영)
    # ----------------------------------------------------
    print("📝 [2단계] 음성 텍스트 변환 중...")
    dynamic_prompt = f"비고 프로젝트, 제미나이, 문지수, 김나연, 이승주, 정승현, 가동현. 대화 주제: {topic}"
    
    segments, info = whisper_model.transcribe(
        wav_path, 
        vad_filter=True, 
        initial_prompt=dynamic_prompt
    )

    # ----------------------------------------------------
    # 공정 3: 데이터 결합
    # ----------------------------------------------------
    print("🔗 [3단계] 화자와 텍스트 매칭 중...")
    transcription_result = []
    
    if hasattr(diarization, "itertracks"):
        annotation = diarization
    elif hasattr(diarization, "speaker_diarization"):
        annotation = diarization.speaker_diarization
    else:
        raise RuntimeError("화자 분리 결과에서 시간표를 찾을 수 없습니다.")
    
    for segment in segments:
        max_overlap = 0
        speaker_label = "Speaker_???"
        
        for turn, _, speaker in annotation.itertracks(yield_label=True):
            overlap_start = max(segment.start, turn.start)
            overlap_end = min(segment.end, turn.end)
            overlap = max(0, overlap_end - overlap_start)
            
            if overlap > max_overlap:
                max_overlap = overlap
                speaker_label = speaker
                
        transcription_result.append({
            "start": f"{segment.start:.2f}",
            "end": f"{segment.end:.2f}",
            "speaker": speaker_label,
            "text": segment.text.strip(),
            "user_edited": False
        })
        
    return transcription_result