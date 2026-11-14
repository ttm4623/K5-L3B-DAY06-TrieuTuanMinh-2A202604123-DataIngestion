"""Evaluate retrieved evidence and preserve per-query traces."""
from typing import Any


def normalize_for_match(text: str) -> str:
    """Chuẩn hóa khoảng trắng và chữ thường để đối chiếu evidence chính xác."""
    if not text:
        return ""
    return " ".join(text.lower().split())


def check_evidence_match(retrieved_text: str, evidence_quote: str) -> bool:
    """Kiểm tra xem bằng chứng gốc có nằm trong nội dung chunk retrieved không."""
    clean_retrieved = normalize_for_match(retrieved_text)
    clean_evidence = normalize_for_match(evidence_quote.replace("...", "").strip())
    
    if not clean_evidence:
        return True
        
    if clean_evidence in clean_retrieved:
        return True
        
    words = clean_evidence.split()
    if len(words) >= 6:
        mid = len(words) // 2
        first_half = " ".join(words[:mid])
        second_half = " ".join(words[mid:])
        if first_half in clean_retrieved or second_half in clean_retrieved:
            return True
            
    return False


def evaluate_query(question: dict[str, Any], hits: list[dict[str, Any]]) -> dict[str, Any]:
    """Check source/page and enough gold evidence; keep hit@1 and hit@3 trace.

    Accept any documented alternative gold evidence. Do not infer human grounding
    or chunk coherence labels from exact string match.
    """
    evidence_quote = question.get("evidence_quote", "")
    
    hit_at_1 = False
    hit_at_3 = False
    found_rank = None

    for idx, hit in enumerate(hits, start=1):
        chunk_text = hit.get("text", "")
        if check_evidence_match(chunk_text, evidence_quote):
            found_rank = idx
            if idx == 1:
                hit_at_1 = True
            if idx <= 3:
                hit_at_3 = True
            break

    return {
        "question_id": question.get("question_id"),
        "split": question.get("split"),
        "hit_at_1": hit_at_1,
        "hit_at_3": hit_at_3,
        "found_rank": found_rank,
        "question": question.get("question")
    }


def summarize(traces: list[dict[str, Any]]) -> dict[str, Any]:
    """Aggregate Hit@1 and Evidence Hit@3 by strategy and dev/test split."""
    summary = {
        "dev": {"total": 0, "hit_at_1_count": 0, "hit_at_3_count": 0},
        "test": {"total": 0, "hit_at_1_count": 0, "hit_at_3_count": 0}
    }

    for trace in traces:
        split = trace.get("split", "dev")
        if split not in summary:
            summary[split] = {"total": 0, "hit_at_1_count": 0, "hit_at_3_count": 0}
            
        summary[split]["total"] += 1
        if trace.get("hit_at_1"):
            summary[split]["hit_at_1_count"] += 1
        if trace.get("hit_at_3"):
            summary[split]["hit_at_3_count"] += 1

    result_metrics = {}
    for split, data in summary.items():
        total = data["total"]
        if total > 0:
            result_metrics[split] = {
                "total": total,
                "hit_rate_at_1": (data["hit_at_1_count"] / total) * 100,
                "hit_rate_at_3": (data["hit_at_3_count"] / total) * 100
            }
        else:
            result_metrics[split] = {
                "total": 0,
                "hit_rate_at_1": 0.0,
                "hit_rate_at_3": 0.0
            }

    return result_metrics