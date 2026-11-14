"""Pipeline entry point; orchestration for ingestion, embedding, storage and evaluation."""
import json
from pathlib import Path

from ingestion import load_html_corpus
from chunking import fixed_size, by_paragraph
from embeddings import MyEmbedder
from store import PgVectorStore
from evaluation import evaluate_query, summarize


def main() -> None:
    """Orchestrate Day 06 pipeline:

    1. Load the corpus and benchmark; validate at least 30 content pages.
    2. Build strategies A (fixed), B (paragraph) and C (B + metadata filter).
    3. Embed with the same model and store vectors/metadata per strategy.
    4. Run the same dev/test questions and save full top-3 traces.
    5. Report retrieval metrics and prepare samples for manual assessment.
    """
    print("=== BẮT ĐẦU PIPELINE NGÀY 06 ===")

    # Cấu hình kết nối DB PostgreSQL (cổng 55433)
    db_url = "postgresql://day6:day6_local_only@localhost:55433/day6_lab"
    
    # 1. Load Corpus & Benchmark
    root_dir = Path(__file__).resolve().parent.parent.parent
    corpus_path = Path("data/pg39272-images.html")
    benchmark_path = Path("data/tesla_benchmark.json")

    document_id = "gutenberg_tesla_inventions_39272"
    source_name = "Project Gutenberg eBook #39272"

    print("Đang đọc corpus HTML...")
    pages = load_html_corpus(corpus_path, document_id=document_id, source=source_name)
    print(f"-> Đã tải thành công {len(pages)} trang/đơn vị nội dung.")
    
    # Validate ít nhất 30 trang nội dung
    if len(pages) < 30:
        print(f"[Cảnh báo] Số lượng trang ({len(pages)}) nhỏ hơn 30.")

    with open(benchmark_path, "r", encoding="utf-8") as f:
        benchmark_data = json.load(f)

    # 2. Khởi tạo Embedder
    embedder = MyEmbedder(model_name="all-MiniLM-L6-v2")
    store = PgVectorStore(database_url=db_url, dimensions=embedder.dimensions)
    store.create_schema()

    # Định nghĩa 3 chiến lược (Strategies)
    strategies = ["strategy_a_fixed", "strategy_b_paragraph", "strategy_c_filtered"]

    # Xây dựng và nạp dữ liệu cho từng chiến lược
    for strategy_name in strategies:
        print(f"\n--- Đang xử lý chiến lược: {strategy_name} ---")
        all_chunks = []
        
        for page in pages:
            # Gán metadata mẫu cho từng trang (phục vụ bộ lọc metadata ở chiến lược C)
            page.metadata = {"section": "chapters", "document_type": "book"}
            
            if strategy_name == "strategy_a_fixed":
                chunks = fixed_size(page, size=500, overlap=50)
            else:
                # Strategy B và C dùng paragraph chunking
                chunks = by_paragraph(page, max_size=800)
            
            # Cập nhật metadata cho từng chunk từ page
            for c in chunks:
                c.metadata = page.metadata
            all_chunks.extend(chunks)

        print(f"-> Tạo được {len(all_chunks)} chunks. Đang tính toán embeddings...")
        texts = [c.text for c in all_chunks]
        vectors = embedder.embed_documents(texts)

        print(f"-> Đang upsert vào PgVectorStore...")
        store.upsert(strategy=strategy_name, chunks=all_chunks, vectors=vectors)

    # 4 & 5. Chạy đánh giá trên tập Dev & Test cho từng chiến lược
    print("\n=== KẾT QUẢ ĐÁNH GIÁ RETRIEVAL ===")
    
    for strategy_name in strategies:
        print(f"\n================ [{strategy_name.upper()}] ================")
        traces = []
        
        for item in benchmark_data:
            q_text = item["question"]
            q_vec = embedder.embed_query(q_text)
            
            # Nếu là chiến lược C, áp dụng metadata filter giả lập từ câu hỏi (hoặc cấu hình sẵn)
            filters = {"section": "chapters"} if strategy_name == "strategy_c_filtered" else None
            
            hits = store.search(strategy=strategy_name, query_vector=q_vec, top_k=3, filters=filters)
            
            # Đánh giá qua hàm trong evaluation.py
            trace = evaluate_query(item, hits)
            trace["split"] = item["split"]
            traces.append(trace)

        summary = summarize(traces)
        for split_name, metrics in summary.items():
            print(f"  • Tập {split_name.upper()} (Tổng: {metrics['total']} câu):")
            print(f"    - Hit Rate @ 1 : {metrics['hit_rate_at_1']:.2f}%")
            print(f"    - Hit Rate @ 3 : {metrics['hit_rate_at_3']:.2f}%")

    print("\n=== HOÀN TẤT PIPELINE THÀNH CÔNG ===")


if __name__ == "__main__":
    main()