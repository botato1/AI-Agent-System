import json
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]
KNOWLEDGE_DIR = BASE_DIR / "data" / "knowledge"

print(f"[data/knowledge 폴더 JSON 수량]\n")

total = 0
for f in sorted(KNOWLEDGE_DIR.glob("*.json")):
    try:
        with open(f, "r", encoding="utf-8") as fp:
            data = json.load(fp)
        count = len(data) if isinstance(data, list) else 0
        print(f"  {f.name:<40} {count}개")
        total += count
    except Exception as e:
        print(f"  {f.name:<40} [오류: {e}]")

print(f"\n  {'합계':<40} {total}개")