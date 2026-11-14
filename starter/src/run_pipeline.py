"""Pipeline script to ingest Nikola Tesla corpus, chunk it, embed it, and store into pgvector."""
from pathlib import Path
import psycopg2
from pgvector.psycopg2 import register_vector

from ingestion import load_html_corpus
from chunking import fixed_size
from embeddings import MyEmbedder

DB_CONFIG = {
    "dbname": "day6_lab",
    "user": "day6",
    "password": "day6_local_only",
    "host": "localhost",
    "port": 55433
}

def main():
    print("=== BẮT ĐẦU PIPELINE INGESTION & PGVECTOR STORAGE ===")

    corpus_path = Path("data/pg39272-images.html")
    document_id = "gutenberg_tesla_inventions_39272"
    source_name = "Project Gutenberg eBook #39272"
    
    print(f"Đang đọc file corpus từ {corpus_path}...")
    pages = load_html_corpus(corpus_path, document_id=document_id, source=source_name)
    print(f"-> Đã trích xuất thành công {len(pages)} đơn vị/chương.")

    print("Đang thực hiện chia chunk văn bản...")
    all_chunks = []
    for page in pages:
        chunks = fixed_size(page, size=500, overlap=50)
        all_chunks.extend(chunks)
    print(f"-> Tổng số lượng chunks được tạo: {len(all_chunks)}")

    embedder = MyEmbedder(model_name="all-MiniLM-L6-v2")
    texts_to_embed = [chunk.text for chunk in all_chunks]
    
    print("Đang tạo vector embeddings cho các chunks...")
    vectors = embedder.embed_documents(texts_to_embed)
    print(f"-> Đã mã hóa xong {len(vectors)} vectors.")

    print("Đang kết nối tới PostgreSQL tại cổng 55433...")
    conn = psycopg2.connect(**DB_CONFIG)
    register_vector(conn)
    cur = conn.cursor()

    try:
        cur.execute("CREATE EXTENSION IF NOT EXISTS vector;")
        cur.execute(f"""
            CREATE TABLE IF NOT EXISTS tesla_chunks (
                chunk_id VARCHAR(255) PRIMARY KEY,
                document_id VARCHAR(255),
                page_id VARCHAR(255),
                chunk_index INT,
                text TEXT,
                embedding vector({embedder.dimensions})
            );
        """)
        conn.commit()

        cur.execute("DELETE FROM tesla_chunks;")
        
        print("Đang lưu các chunks và vectors vào database...")
        insert_query = """
            INSERT INTO tesla_chunks (chunk_id, document_id, page_id, chunk_index, text, embedding)
            VALUES (%s, %s, %s, %s, %s, %s)
            ON CONFLICT (chunk_id) DO UPDATE 
            SET text = EXCLUDED.text, embedding = EXCLUDED.embedding;
        """
        
        data_to_insert = [
            (c.chunk_id, c.document_id, c.page_id, c.index, c.text, v)
            for c, v in zip(all_chunks, vectors)
        ]
            
        cur.executemany(insert_query, data_to_insert)
        conn.commit()
        print(f"-> Nạp thành công {len(data_to_insert)} bản ghi vào pgvector!")

        # Kiểm thử truy vấn
        print("\n=== KIỂM THỬ TRUY VẤN SIMILARITY SEARCH ===")
        test_query = "What did Tesla invent regarding alternating current motors?"
        query_vector = embedder.embed_query(test_query)
        
        cur.execute("""
            SELECT chunk_id, text, 1 - (embedding <=> %s::vector) AS similarity
            FROM tesla_chunks
            ORDER BY embedding <=> %s::vector
            LIMIT 3;
        """, (query_vector, query_vector))
        
        for idx, row in enumerate(cur.fetchall(), 1):
            print(f"\n[Top {idx}] Chunk ID: {row[0]} | Độ tương đồng: {row[2]:.4f}")
            print(f"Nội dung: {row[1][:200]}...")

    except Exception as e:
        conn.rollback()
        print(f"Lỗi cơ sở dữ liệu: {e}")
    finally:
        cur.close()
        conn.close()
        print("\n=== HOÀN TẤT PIPELINE ===")

if __name__ == "__main__":
    main()