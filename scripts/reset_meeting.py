import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]
if str(BASE_DIR) not in sys.path:
    sys.path.append(str(BASE_DIR))

import chromadb

CHROMA_DIR = str(BASE_DIR / "storage" / "chroma")
client = chromadb.PersistentClient(path=CHROMA_DIR)

try:
    client.delete_collection("meeting_collection")
    print("meeting_collection 삭제 완료")
except Exception as e:
    print(f"삭제 실패: {e}")

# 확인
collections = client.list_collections()
print(f"남은 컬렉션: {[c.name for c in collections]}")