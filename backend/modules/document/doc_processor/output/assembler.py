from __future__ import annotations

import hashlib
from pathlib import Path

from doc_processor.core.models import DocumentResult, PageResult
from doc_processor.schemas.chunk import ChunkSchema
from doc_processor.schemas.document import DocumentSchema
from doc_processor.schemas.metadata import (
    ChunkMetadata,
    DocumentMetadata,
    PageResultSchema,
)


# ── ID 생성 ──────────────────────────────────────────────────────────────────

def _doc_id(source: str) -> str:
    return "doc_" + hashlib.md5(source.encode()).hexdigest()[:12]


def _chunk_id(doc_id: str, page: int, chunk_type: str, index: int) -> str:
    raw = f"{doc_id}::p{page}::{chunk_type}::{index}"
    return hashlib.md5(raw.encode()).hexdigest()[:12]


# ── content 조립 (plain text) ────────────────────────────────────────────────

def _build_plain_text(doc: DocumentResult) -> str:
    """PyMuPDF 텍스트 + OCR 텍스트 + 표 텍스트를 모두 합쳐 반환합니다."""
    parts: list[str] = []
    for page in doc.pages:
        # 텍스트 블록
        for block in page.content.text:
            if block.text.strip():
                parts.append(block.text.strip())
        # 표 — 셀을 공백으로 이어 붙임
        for table in page.content.tables:
            for row in table.data:
                row_text = " ".join(str(c) for c in row if c is not None)
                if row_text.strip():
                    parts.append(row_text.strip())
        # 이미지 OCR
        for img in page.content.images:
            if img.ocr_text.strip():
                parts.append(img.ocr_text.strip())
        # 차트
        for chart in page.content.charts:
            if chart.description.strip():
                parts.append(chart.description.strip())
    return "\n".join(parts)


# ── content_markdown 조립 ────────────────────────────────────────────────────

def _build_markdown(doc: DocumentResult) -> str:
    parts: list[str] = []
    for page in doc.pages:
        parts.append(f"<!-- page {page.page} -->")
        for block in page.content.text:
            prefix = {"title": "# ", "heading": "## ", "caption": "_"}.get(block.style, "")
            suffix = "_" if block.style == "caption" else ""
            parts.append(f"{prefix}{block.text}{suffix}")
        for table in page.content.tables:
            parts.append(table.markdown)
        for img in page.content.images:
            if img.ocr_text.strip():
                parts.append(f"> {img.ocr_text.strip()}")
        for chart in page.content.charts:
            if chart.description.strip():
                parts.append(f"**[Chart]** {chart.description.strip()}")
    return "\n\n".join(parts)


# ── 태그 자동 생성 ────────────────────────────────────────────────────────────

def _auto_tags(doc: DocumentResult) -> list[str]:
    tags = ["pdf", doc.pdf_type]
    if any(page.content.tables for page in doc.pages):
        tags.append("table")
    if any(page.content.images for page in doc.pages):
        tags.append("image")
    if any(page.fallback_used for page in doc.pages):
        tags.append("gemini-fallback")
    return tags


# ── 엔진 목록 수집 ────────────────────────────────────────────────────────────

def _collect_engines(doc: DocumentResult) -> list[str]:
    engines = ["pymupdf", "pdfplumber"]
    has_ocr = any(page.content.images for page in doc.pages)
    if has_ocr:
        engines += ["paddle", "surya"]
    if any(page.fallback_used for page in doc.pages):
        engines.append("gemini")
    return engines


# ── 문서 평균 confidence ─────────────────────────────────────────────────────

def _avg_confidence(doc: DocumentResult) -> float:
    scores: list[float] = []
    for page in doc.pages:
        d = page.confidence.to_dict()
        # overall·chart는 제외하고 실제 추출 항목만 평균
        scores.extend(v for k, v in d.items() if k not in ("overall", "chart"))
    if not scores:
        return 1.0
    return round(sum(scores) / len(scores), 3)


# ── status 결정 ───────────────────────────────────────────────────────────────

def _status(doc: DocumentResult, avg_conf: float) -> str:
    if not doc.pages:
        return "error"
    if avg_conf < 0.7:
        return "uploaded"   # 신뢰도 낮음 — 사람 검토 필요
    return "processed"


# ── text 블록 청크 병합 ───────────────────────────────────────────────────────

# 같은 스타일 + 같은 폰트 + 세로 간격이 이 값 이하면 하나의 청크로 병합
_CHUNK_MERGE_GAP = 8.0


def _should_merge(a: "TextBlock", b: "TextBlock") -> bool:  # type: ignore[name-defined]
    """두 블록을 하나의 청크로 병합해야 하는지 판단.

    Stage 5 완화: 폰트가 달라도 스타일·사이즈가 같고 간격이 좁으면 병합.
    이는 같은 문단 안에서 bold/italic 전환이 있는 경우를 포함하기 위함.
    """
    if a.style != b.style:
        return False
    # 폰트 조건 완화: body 스타일은 폰트가 달라도 병합 허용
    if a.style not in ("body", "caption") and a.font != b.font:
        return False
    if abs(a.size - b.size) > 2.0:  # 허용 오차 1.0pt → 2.0pt로 완화
        return False
    # a의 bbox 하단과 b의 bbox 상단 간격
    gap = b.bbox[1] - a.bbox[3] if len(a.bbox) >= 4 and len(b.bbox) >= 4 else 0.0
    return gap <= _CHUNK_MERGE_GAP


def _merge_text_blocks(blocks: "list[TextBlock]") -> "list[tuple[str, TextBlock]]":  # type: ignore[name-defined]
    """연속된 텍스트 블록을 병합하고 (병합 텍스트, 대표 블록) 리스트를 반환."""
    if not blocks:
        return []

    groups: list[list] = [[blocks[0]]]
    for block in blocks[1:]:
        if _should_merge(groups[-1][-1], block):
            groups[-1].append(block)
        else:
            groups.append([block])

    result = []
    for group in groups:
        sep = " " if group[0].style in ("title", "heading") else "\n"
        merged_text = sep.join(b.text for b in group).strip()
        if merged_text:
            result.append((merged_text, group[0]))
    return result


# ── chunks 조립 ───────────────────────────────────────────────────────────────

def _build_chunks(doc: DocumentResult, doc_id: str) -> list[ChunkSchema]:
    chunks: list[ChunkSchema] = []

    for page in doc.pages:
        pg = page.page_number if hasattr(page, "page_number") else page.page

        # text — 블록 병합 후 청크 생성
        merged_text_blocks = _merge_text_blocks(page.content.text)
        for i, (merged_text, rep_block) in enumerate(merged_text_blocks):
            chunks.append(ChunkSchema(
                id=_chunk_id(doc_id, pg, "text", i),
                content_type="text",
                page_number=pg,
                content=merged_text,
                metadata=ChunkMetadata(
                    confidence_score=page.confidence.text,
                    engines=["pymupdf"],
                    fallback_used=page.fallback_used,
                    style=rep_block.style,
                    font=rep_block.font,
                    size=round(rep_block.size, 2),
                ),
            ))

        # table
        for i, table in enumerate(page.content.tables):
            if not table.markdown.strip():
                continue
            chunks.append(ChunkSchema(
                id=_chunk_id(doc_id, pg, "table", i),
                content_type="table",
                page_number=pg,
                content=table.markdown,
                metadata=ChunkMetadata(
                    confidence_score=page.confidence.table,
                    engines=["pdfplumber"],
                    fallback_used=page.fallback_used,
                    rows=len(table.data),
                    cols=len(table.data[0]) if table.data else 0,
                ),
            ))

        # image
        for i, img in enumerate(page.content.images):
            if not img.ocr_text.strip():
                continue
            chunks.append(ChunkSchema(
                id=_chunk_id(doc_id, pg, "image", i),
                content_type="image",
                page_number=pg,
                content=img.ocr_text,
                metadata=ChunkMetadata(
                    confidence_score=page.confidence.image,
                    engines=["paddle", "surya"],
                    fallback_used=page.fallback_used,
                    voting_confidence=img.voting_confidence,
                    source_engines=img.source_engines,
                    ocr_quality_score=img.quality_score if img.quality_score >= 0 else None,
                ),
            ))

        # chart
        for i, chart in enumerate(page.content.charts):
            if not chart.description.strip():
                continue
            chunks.append(ChunkSchema(
                id=_chunk_id(doc_id, pg, "chart", i),
                content_type="chart",
                page_number=pg,
                content=chart.description,
                metadata=ChunkMetadata(
                    confidence_score=page.confidence.chart,
                    engines=["gemini"],
                    fallback_used=page.fallback_used,
                ),
            ))

    return chunks


# ── page_results 조립 (디버깅용) ─────────────────────────────────────────────

def _build_page_results(doc: DocumentResult) -> list[PageResultSchema]:
    results: list[PageResultSchema] = []
    for page in doc.pages:
        pg = page.page_number if hasattr(page, "page_number") else page.page
        results.append(PageResultSchema(
            page_number=pg,
            text_blocks=[
                {"text": b.text, "style": b.style, "font": b.font, "size": round(b.size, 2)}
                for b in page.content.text
            ],
            tables=[
                {"markdown": t.markdown, "rows": len(t.data)}
                for t in page.content.tables
            ],
            images=[
                {
                    "bbox": img.bbox,
                    "ocr_text": img.ocr_text,
                    "voting_confidence": img.voting_confidence,
                    "quality_score": img.quality_score if img.quality_score >= 0 else None,
                    **({"debug": img.debug} if img.debug is not None else {}),
                }
                for img in page.content.images
            ],
            charts=[
                {"description": c.description[:100]}
                for c in page.content.charts
            ],
            confidence=page.confidence.to_dict(),
            fallback_used=page.fallback_used,
        ))
    return results


# ── 최종 조립 ─────────────────────────────────────────────────────────────────

def _is_fallback_candidate(doc: DocumentResult, avg_conf: float) -> bool:
    """Gemini 보정이 권장되는 문서인지 판단.

    조건:
    - 문서 평균 confidence < 0.70
    - 또는 이미지 confidence 평균 < 0.50 (OCR 품질이 낮은 이미지 포함)
    """
    if avg_conf < 0.70:
        return True
    image_scores = [p.confidence.image for p in doc.pages if p.content.images]
    if image_scores and (sum(image_scores) / len(image_scores)) < 0.50:
        return True
    return False


def assemble(doc: DocumentResult) -> DocumentSchema:
    """DocumentResult → DocumentSchema 변환의 단일 진입점."""
    doc_id = _doc_id(doc.source)
    avg_conf = _avg_confidence(doc)
    fallback_candidate = _is_fallback_candidate(doc, avg_conf)

    if fallback_candidate:
        print(f"[Assembler] fallback_candidate=True (avg_conf={avg_conf:.3f})")

    return DocumentSchema(
        id=doc_id,
        title=Path(doc.source).stem,
        source="pdf",
        content=_build_plain_text(doc),
        content_markdown=_build_markdown(doc),
        tags=_auto_tags(doc),
        status=_status(doc, avg_conf),
        chunks=_build_chunks(doc, doc_id),
        page_results=_build_page_results(doc),
        metadata=DocumentMetadata(
            confidence_score=avg_conf,
            engines=_collect_engines(doc),
            fallback_used=any(p.fallback_used for p in doc.pages),
            page_count=max(len(doc.pages), 1),
            file_path=doc.source,
            pdf_type=doc.pdf_type,
            fallback_candidate=fallback_candidate,
            ocr_attempt_count=doc.ocr_stats.attempt_count,
            ocr_skip_count=doc.ocr_stats.skip_count,
            ocr_success_count=doc.ocr_stats.success_count,
            ocr_empty_count=doc.ocr_stats.empty_count,
            ocr_filtered_count=doc.ocr_stats.filtered_count,
            ocr_useful_count=doc.ocr_stats.useful_count,
            ocr_garbage_count=doc.ocr_stats.garbage_count,
            ocr_avg_quality_score=doc.ocr_stats.avg_quality_score,
            ocr_skip_ratio=doc.ocr_stats.skip_ratio,
            ocr_success_ratio=doc.ocr_stats.success_ratio,
            ocr_useful_ratio=doc.ocr_stats.useful_ratio,
            ocr_surya_ratio=doc.ocr_stats.surya_ratio,
            ocr_paddle_only_count=doc.ocr_stats.paddle_only_count,
            ocr_paddle_surya_count=doc.ocr_stats.paddle_surya_count,
            ocr_chart_paddle_only_count=doc.ocr_stats.chart_paddle_only_count,
            ocr_table_tsr_count=doc.ocr_stats.table_tsr_count,
            processing_time_sec=doc.ocr_stats.processing_time_sec,
            pages_per_second=round(
                len(doc.pages) / doc.ocr_stats.processing_time_sec, 3
            ) if doc.ocr_stats.processing_time_sec > 0 else 0.0,
        ),
    )
