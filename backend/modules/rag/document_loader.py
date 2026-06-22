# backend/services/document_loader.py
#
# 사용자 업로드 문서(document/meeting)와 음성(voice)을
# 청킹해서 ChromaDB에 적재하는 모듈.
#
# [청킹 전략]
# document/meeting:
#   - chunks[]에서 style=="caption" 제거 (팀원이 미리 제거해서 넘겨줄 예정)
#   - style=="title"  → 새 청크 경계 + content 맨 앞에 포함
#   - style=="body"   → 500~1700자 기준으로 묶기
#   - 청크 content = "[섹션 title]\n[body 내용들]"
#
# voice:
#   - transcription[] 발화를 300~800자 기준으로 묶기
#   - 화자 바뀌는 지점 우선 경계로
#   - 청크 content = "[SPEAKER_00]: 발화\n[SPEAKER_01]: 발화\n..."
#
# [컬렉션 매핑]
#   type == "document" → document_collection
#   type == "meeting"  → meeting_collection
#   type == "voice"    → meeting_collection

import sys
import json
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[2]
if str(BASE_DIR) not in sys.path:
    sys.path.append(str(BASE_DIR))

from backend.modules.rag.chroma_client import insert_document
from backend.db.crud import get_document_by_id

# ── 청킹 파라미터 ──────────────────────────────────────────────
DOC_CHUNK_MIN  = 500    # 문서 청크 최소 글자 수
DOC_CHUNK_MAX  = 1700   # 문서 청크 최대 글자 수
STT_CHUNK_MIN  = 300    # 음성 청크 최소 글자 수
STT_CHUNK_MAX  = 800    # 음성 청크 최대 글자 수


# ── 문서/회의록 청킹 ──────────────────────────────────────────

def _chunk_document(chunks: list) -> list[dict]:
    """
    document/meeting 타입의 chunks[]를 받아서
    검색에 적합한 크기(500~1700자)의 청크 리스트로 반환한다.

    규칙:
    - style == "caption" → 제외 (팀원이 미리 제거 예정이지만 방어 코드로 유지)
    - style == "title"   → 새 청크 경계. 현재 모인 body가 있으면 먼저 확정.
                           다음 청크의 맨 앞에 이 title을 포함시킴.
    - style == "body"    → 현재 청크에 계속 추가.
                           DOC_CHUNK_MAX를 넘으면 현재 청크 확정 후 새로 시작.

    반환: [{"content": str, "page_number": int}, ...]
    """
    result = []
    current_lines = []       # 현재 청크에 모인 텍스트 라인들
    current_title = ""       # 현재 섹션 title
    current_page = 1         # 현재 페이지 번호
    current_chars = 0        # 현재 청크의 글자 수

    def flush(lines, title, page):
        """현재 모인 lines를 하나의 청크로 확정."""
        if not lines:
            return
        content = "\n".join(lines).strip()
        if not content:
            return
        # title이 있으면 content 맨 앞에 포함
        if title:
            content = f"{title}\n{content}"
        result.append({"content": content, "page_number": page})

    for chunk in chunks:
        style = chunk.get("metadata", {}).get("style", "body")
        content = chunk.get("content", "").strip()
        page = chunk.get("page_number", 1)

        if not content:
            continue

        # caption 제외 (방어 코드)
        if style == "caption":
            continue

        if style == "title":
            # 현재 모인 body가 있으면 먼저 확정
            if current_lines:
                flush(current_lines, current_title, current_page)
                current_lines = []
                current_chars = 0
            # 새 섹션 시작
            current_title = content
            current_page = page

        elif style == "body":
            content_len = len(content)

            # 이미 MAX를 넘는 경우: 현재 청크 확정 후 새로 시작
            if current_chars + content_len > DOC_CHUNK_MAX and current_chars >= DOC_CHUNK_MIN:
                flush(current_lines, current_title, current_page)
                current_lines = []
                current_chars = 0
                # title은 다음 청크에도 이어서 사용 (같은 섹션 내 분할이므로)

            current_lines.append(content)
            current_chars += content_len
            current_page = page

    # 마지막 청크 처리
    flush(current_lines, current_title, current_page)

    return result


# ── 음성(STT) 청킹 ────────────────────────────────────────────

def _chunk_transcription(transcription: list) -> list[dict]:
    """
    voice 타입의 transcription[]을 받아서
    검색에 적합한 크기(300~800자)의 청크 리스트로 반환한다.

    규칙:
    - 화자(speaker)가 바뀌는 지점을 우선 청크 경계로 사용
    - 같은 화자가 이어지더라도 STT_CHUNK_MAX를 넘으면 청크 확정

    반환: [{"content": str, "start": float, "end": float}, ...]
    """
    result = []
    current_lines = []    # "[SPEAKER_00]: 발화내용" 형식의 라인들
    current_chars = 0
    current_start = 0.0
    current_end = 0.0
    prev_speaker = None

    def flush(lines, start, end):
        if not lines:
            return
        content = "\n".join(lines).strip()
        if content:
            result.append({"content": content, "start": start, "end": end})

    for seg in transcription:
        speaker = seg.get("speaker", "SPEAKER_00")
        text = seg.get("text", "").strip()
        start = seg.get("start", 0.0)
        end = seg.get("end", 0.0)

        if not text:
            continue

        line = f"[{speaker}]: {text}"
        line_len = len(line)

        speaker_changed = (prev_speaker is not None and speaker != prev_speaker)
        over_max = (current_chars + line_len > STT_CHUNK_MAX and current_chars >= STT_CHUNK_MIN)

        # 화자가 바뀌거나 MAX를 넘으면 현재 청크 확정
        if (speaker_changed or over_max) and current_lines:
            flush(current_lines, current_start, current_end)
            current_lines = []
            current_chars = 0
            current_start = start

        if not current_lines:
            current_start = start

        current_lines.append(line)
        current_chars += line_len
        current_end = end
        prev_speaker = speaker

    # 마지막 청크 처리
    flush(current_lines, current_start, current_end)

    return result


# ── 컬렉션 결정 ───────────────────────────────────────────────

def _get_upload_context(doc_type: str) -> str:
    """
    type → upload_context 매핑.
    chroma_client.CONTEXT_TO_COLLECTION이 이 값을 기준으로
    컬렉션을 결정한다.

    document → document_collection
    meeting  → meeting_collection
    voice    → meeting_collection
    """
    mapping = {
        "document": "document",
        "meeting":  "meeting",
        "voice":    "voice",
    }
    return mapping.get(doc_type, "document")


# ── 공통 메타데이터 빌더 ──────────────────────────────────────

def _build_base_meta(doc: dict, room_id: str = "") -> dict:
    """문서/음성 공통 메타데이터."""
    return {
        "title":          doc.get("title", ""),
        "document_id":    doc.get("id") or doc.get("document_id", ""),
        "filename":       doc.get("filename", ""),
        "type":           doc.get("type", "document"),
        "source":         doc.get("source", ""),
        "language":       doc.get("language", "ko"),
        "created_at":     doc.get("created_at", ""),
        "status":         doc.get("status", "processed"),
        "notion_url":     doc.get("notion_url") or "",
        "error":          doc.get("error") or "",
        "user_edited":    False,
        "tags":           ",".join(doc.get("tags", [])),
        "importance_score": doc.get("importance_score", 0),
        "room_id":        room_id,
        "tech_score":     0,  # 사용자 업로드 문서는 tech_score 없음
    }


# ── 메인 적재 함수 ────────────────────────────────────────────

def load_document(document_id: str, room_id: str = "") -> dict:
    """
    document_id를 받아서 SQLite documents 테이블에서 json_path를 조회하고,
    해당 JSON 파일을 읽어서 청킹 후 ChromaDB에 적재한다.

    흐름:
    문서 업로드
    → 8000에서 8003 호출
    → 8000 SQLite documents 저장 (json_path 포함)
    → load_document(document_id) 호출
    → json_path에서 chunks[]/transcription[] 읽기
    → 청킹 후 ChromaDB 저장

    Args:
        document_id: SQLite documents 테이블의 id
        room_id: 채팅방 ID (검색 필터용)

    Returns:
        {"status": "success"/"error", "chunk_count": int, "document_id": str, "error": str}
    """
    print(f"[document_loader] 적재 시작 → document_id={document_id}")

    # 1. SQLite에서 문서 정보 조회
    try:
        db_record = get_document_by_id(document_id)
    except Exception as e:
        print(f"[document_loader] DB 조회 실패: {e}")
        return {"status": "error", "chunk_count": 0, "document_id": document_id, "error": f"db_lookup_failed: {e}"}

    if not db_record:
        print(f"[document_loader] document_id를 찾을 수 없음: {document_id}")
        return {"status": "error", "chunk_count": 0, "document_id": document_id, "error": "document_not_found"}

    json_path = db_record.get("json_path")
    if not json_path:
        print(f"[document_loader] json_path가 없음: {document_id}")
        return {"status": "error", "chunk_count": 0, "document_id": document_id, "error": "json_path_missing"}

    # 2. json_path에서 전체 JSON 읽기
    try:
        with open(json_path, "r", encoding="utf-8") as f:
            doc = json.load(f)
    except Exception as e:
        print(f"[document_loader] JSON 파일 읽기 실패 ({json_path}): {e}")
        return {"status": "error", "chunk_count": 0, "document_id": document_id, "error": f"json_read_failed: {e}"}

    # 3. room_id가 없으면 db_record에서 보완
    # SQLite documents 테이블의 컬럼명은 conversation_id
    if not room_id:
        room_id = db_record.get("conversation_id", "")

    # 4. 타입 판단 후 적재
    doc_type = doc.get("type", "document")
    upload_context = _get_upload_context(doc_type)
    base_meta = _build_base_meta(doc, room_id)

    try:
        if doc_type == "voice":
            return _load_voice(doc, base_meta, upload_context)
        else:
            return _load_text_document(doc, base_meta, upload_context)

    except Exception as e:
        print(f"[document_loader 에러] {document_id}: {e}")
        return {"status": "error", "chunk_count": 0, "document_id": document_id, "error": str(e)}


def _load_text_document(doc: dict, base_meta: dict, upload_context: str) -> dict:
    """document/meeting 타입 적재."""
    chunks = doc.get("chunks", [])
    doc_id = base_meta["document_id"]

    if not chunks:
        print(f"[document_loader] chunks가 비어있음 → document_id: {doc_id}")
        return {
            "status": "error",
            "chunk_count": 0,
            "document_id": doc_id,
            "error": "chunks_empty",
        }

    chunked = _chunk_document(chunks)

    if not chunked:
        print(f"[document_loader] 청킹 결과 없음 → document_id: {doc_id}")
        return {
            "status": "error",
            "chunk_count": 0,
            "document_id": doc_id,
            "error": "chunk_result_empty",
        }

    for idx, chunk in enumerate(chunked):
        chunk_id = f"{doc_id}_chunk_{idx:04d}"
        metadata = {
            **base_meta,
            "chunk_index": idx,
            "page_number": chunk.get("page_number", 1),
            "upload_context": upload_context,
            "chroma_id": chunk_id,
        }
        insert_document({
            "id":      chunk_id,
            "content": chunk["content"],
            **metadata,
        })

    print(f"[document_loader] 완료 → {len(chunked)}개 청크 적재 (document_id: {doc_id})")
    return {
        "status": "success",
        "chunk_count": len(chunked),
        "document_id": doc_id,
        "error": None,
    }


def _load_voice(doc: dict, base_meta: dict, upload_context: str) -> dict:
    """voice 타입 적재."""
    transcription = doc.get("transcription", [])
    doc_id = base_meta["document_id"]

    if not transcription:
        print(f"[document_loader] transcription이 비어있음 → document_id: {doc_id}")
        return {
            "status": "error",
            "chunk_count": 0,
            "document_id": doc_id,
            "error": "transcription_empty",
        }

    chunked = _chunk_transcription(transcription)

    if not chunked:
        print(f"[document_loader] STT 청킹 결과 없음 → document_id: {doc_id}")
        return {
            "status": "error",
            "chunk_count": 0,
            "document_id": doc_id,
            "error": "stt_chunk_result_empty",
        }

    for idx, chunk in enumerate(chunked):
        chunk_id = f"{doc_id}_chunk_{idx:04d}"
        metadata = {
            **base_meta,
            "chunk_index": idx,
            "page_number": 0,          # 음성은 페이지 개념 없음
            "upload_context": upload_context,
            "chroma_id": chunk_id,
            # 음성 전용 메타데이터
            "stt_start": chunk.get("start", 0.0),
            "stt_end":   chunk.get("end", 0.0),
        }
        insert_document({
            "id":      chunk_id,
            "content": chunk["content"],
            **metadata,
        })

    print(f"[document_loader] 완료 → {len(chunked)}개 청크 적재 (document_id: {doc_id})")
    return {
        "status": "success",
        "chunk_count": len(chunked),
        "document_id": doc_id,
        "error": None,
    }