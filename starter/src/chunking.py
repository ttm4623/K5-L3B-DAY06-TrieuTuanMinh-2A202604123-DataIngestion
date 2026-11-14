"""Implement fixed-size and structure-aware chunking."""
from .models import Chunk, DocumentPage


def fixed_size(page: DocumentPage, size: int, overlap: int) -> list[Chunk]:
    """Split text into overlapping windows and retain page metadata."""
    text = page.text
    if not text:
        return []

    chunks = []
    start = 0
    idx = 0
    step = size - overlap
    if step <= 0:
        step = size

    while start < len(text):
        end = start + size
        chunk_text = text[start:end]
        
        chunk = Chunk(
            chunk_id=f"{page.page_id}_fixed_{idx:03d}",
            document_id=page.document_id,
            page_id=page.page_id,
            text=chunk_text,
            index=idx
        )
        chunks.append(chunk)
        
        start += step
        idx += 1

    return chunks


def by_paragraph(page: DocumentPage, max_size: int) -> list[Chunk]:
    """Group paragraphs, split oversized paragraphs and retain metadata."""
    text = page.text
    if not text:
        return []

    paragraphs = text.split("\n\n")
    chunks = []
    current_chunk_text = ""
    idx = 0

    for para in paragraphs:
        para = para.strip()
        if not para:
            continue

        if len(para) > max_size:
            if current_chunk_text:
                chunks.append(Chunk(
                    chunk_id=f"{page.page_id}_para_{idx:03d}",
                    document_id=page.document_id,
                    page_id=page.page_id,
                    text=current_chunk_text.strip(),
                    index=idx
                ))
                idx += 1
                current_chunk_text = ""

            for i in range(0, len(para), max_size):
                sub_text = para[i:i + max_size]
                chunks.append(Chunk(
                    chunk_id=f"{page.page_id}_para_{idx:03d}",
                    document_id=page.document_id,
                    page_id=page.page_id,
                    text=sub_text,
                    index=idx
                ))
                idx += 1
        else:
            if len(current_chunk_text) + len(para) + 2 <= max_size:
                current_chunk_text += ("\n\n" + para if current_chunk_text else para)
            else:
                if current_chunk_text:
                    chunks.append(Chunk(
                        chunk_id=f"{page.page_id}_para_{idx:03d}",
                        document_id=page.document_id,
                        page_id=page.page_id,
                        text=current_chunk_text.strip(),
                        index=idx
                    ))
                    idx += 1
                current_chunk_text = para

    if current_chunk_text:
        chunks.append(Chunk(
            chunk_id=f"{page.page_id}_para_{idx:03d}",
            document_id=page.document_id,
            page_id=page.page_id,
            text=current_chunk_text.strip(),
            index=idx
        ))

    return chunks