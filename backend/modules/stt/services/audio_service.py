# services/audio_service.py
from pydub import AudioSegment

def convert_to_wav(input_path: str) -> str:
    """
    오디오 파일을 읽어 16kHz, Mono 채널의 .wav 파일로 강제 변환합니다.
    변환된 임시 파일의 경로를 반환합니다.
    """
    print("🛠️ [진행 중] 오디오 전처리 및 자동 변환 (.wav, 16kHz, Mono)")
    
    # pydub으로 오디오 불러오기 및 스펙 변경
    audio = AudioSegment.from_file(input_path)
    audio = audio.set_frame_rate(16000).set_channels(1)
    
    # 변환된 결과 저장
    wav_path = input_path + "_converted.wav"
    audio.export(wav_path, format="wav")
    
    return wav_path