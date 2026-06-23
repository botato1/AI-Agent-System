import os
import sys
import json
from pathlib import Path
from langdetect import detect, LangDetectException

BASE_DIR = Path(__file__).resolve().parents[2]
if str(BASE_DIR) not in sys.path:
    sys.path.append(str(BASE_DIR))

from scripts.crawlers.score_utils import detect_language

DATA_DIR = os.path.join(BASE_DIR, "data", "knowledge")

# language 필드를 재검사할 파일들
TARGET_FILES = ["toss_blog.json", "k8s_docs.json", "docker_docs.json"]


def fix_file(filename):
    path = os.path.join(DATA_DIR, filename)
    if not os.path.exists(path):
        print(f"[스킵] 파일 없음: {filename}")
        return

    with open(path, "r", encoding="utf-8") as f:
        docs = json.load(f)

    changed = 0
    lang_count = {}

    for doc in docs:
        old_lang = doc.get("language")
        new_lang = detect_language(doc.get("content", ""))
        lang_count[new_lang] = lang_count.get(new_lang, 0) + 1

        if old_lang != new_lang:
            doc["language"] = new_lang
            changed += 1

    tmp_path = path + ".tmp"
    with open(tmp_path, "w", encoding="utf-8") as f:
        json.dump(docs, f, ensure_ascii=False, indent=2)
    os.replace(tmp_path, path)

    print(f"{filename}: 총 {len(docs)}개 | 변경 {changed}개 | 분포 {lang_count}")

if __name__ == "__main__":
    for fname in TARGET_FILES:
        fix_file(fname)