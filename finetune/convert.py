import os
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]
if str(BASE_DIR) not in sys.path:
    sys.path.append(str(BASE_DIR))

MODEL_DIR = str(BASE_DIR / "models" / "qwen2.5-7b-finetuned")
GGUF_DIR = str(BASE_DIR / "models" / "gguf")
MODEL_NAME = "dev-assistant"

def convert():
    from unsloth import FastLanguageModel

    print("파인튜닝된 모델 로딩 중...")
    model, tokenizer = FastLanguageModel.from_pretrained(
        model_name=MODEL_DIR,
        max_seq_length=2048,
        load_in_4bit=True,
    )

    os.makedirs(GGUF_DIR, exist_ok=True)

    print("GGUF 변환 중...")
    model.save_pretrained_gguf(
        GGUF_DIR,
        tokenizer,
        quantization_method="q4_k_m"
    )
    print(f"GGUF 저장 완료: {GGUF_DIR}")

    # Modelfile 생성
    modelfile_path = BASE_DIR / "models" / "Modelfile