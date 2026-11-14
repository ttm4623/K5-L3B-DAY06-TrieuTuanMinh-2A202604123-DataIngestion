"""Read and normalize source data. Implemented for HTML/Text Gutenberg corpus."""
from pathlib import Path
import re
import unicodedata
from bs4 import BeautifulSoup
from .models import DocumentPage


def load_html_corpus(path: Path, document_id: str, source: str) -> list[DocumentPage]:
    """Extract logical units/chapters from Project Gutenberg HTML file.
    
    Keeps section titles, source info, and character counts.
    """
    if not path.exists():
        raise FileNotFoundError(f"Corpus file not found at {path}")

    with open(path, 'r', encoding='utf-8') as f:
        html_content = f.read()

    soup = BeautifulSoup(html_content, 'html.parser')
    
    document_pages = []
    current_text_buffer = []
    unit_counter = 1

    # Duyệt qua các thẻ tiêu đề và đoạn văn bản trong file HTML
    for element in soup.find_all(['h2', 'h3', 'p']):
        tag_name = element.name
        text = element.get_text(strip=True)
        
        if tag_name in ['h2', 'h3'] and ('Chapter' in text or 'PART' in text):
            if current_text_buffer:
                combined_text = " ".join(current_text_buffer)
                normalized = normalize_text(combined_text)
                if len(normalized) > 100:
                    document_pages.append(
                        DocumentPage(
                            page_id=f"{document_id}_unit_{unit_counter:03d}",
                            document_id=document_id,
                            page_number=unit_counter,
                            source=source,
                            text=normalized,
                            char_count=len(normalized)
                        )
                    )
                    unit_counter += 1
                current_text_buffer = []
        else:
            if text:
                current_text_buffer.append(text)

    if current_text_buffer:
        combined_text = " ".join(current_text_buffer)
        normalized = normalize_text(combined_text)
        if len(normalized) > 100:
            document_pages.append(
                DocumentPage(
                    page_id=f"{document_id}_unit_{unit_counter:03d}",
                    document_id=document_id,
                    page_number=unit_counter,
                    source=source,
                    text=normalized,
                    char_count=len(normalized)
                )
            )

    return document_pages


def load_pdf(path: Path, document_id: str, source: str) -> list[DocumentPage]:
    """Fallback function giữ lại theo khung starter nếu sau này dùng PDF."""
    raise NotImplementedError("Currently using HTML corpus. Use load_html_corpus instead.")


def normalize_text(text: str) -> str:
    """Normalize Unicode and whitespace without discarding useful structure."""
    if not text:
        return ""
    
    # Chuẩn hóa Unicode sang dạng NFC chuẩn
    normalized = unicodedata.normalize('NFC', text)
    
    # Loại bỏ khoảng trắng thừa nhưng giữ nguyên ranh giới dòng/đoạn
    normalized = re.sub(r'[ \t]+', ' ', normalized)
    normalized = re.sub(r'\n\s*\n', '\n\n', normalized)
    
    return normalized.strip()