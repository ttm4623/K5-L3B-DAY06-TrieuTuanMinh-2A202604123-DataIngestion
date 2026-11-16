import json
import os
from pathlib import Path
import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv

# Cố định hoàn toàn thông số kết nối, không phụ thuộc vào .env
DB_HOST = "127.0.0.1"
DB_PORT = 55433
DB_NAME = "day6_lab"     
DB_USER = "day6"          
DB_PASS = "day6_local_only"

TABLE_NAME = "chunks"
print(f"DEBUGGING -> Connecting to Host: {DB_HOST}, Port: {DB_PORT}")
def export_chunks():
    conn = psycopg2.connect(
        host=DB_HOST,
        port=DB_PORT,
        dbname=DB_NAME,
        user=DB_USER,
        password=DB_PASS
    )
    
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            # Kiểm tra tên các cột hiện có trong bảng
            cur.execute(f"SELECT * FROM {TABLE_NAME} LIMIT 1;")
            sample = cur.fetchone()
            if not sample:
                print(f"Bảng '{TABLE_NAME}' đang trống!")
                return
            
            print("Các cột tìm thấy trong DB:", list(sample.keys()))
            
            # Lấy toàn bộ dữ liệu (bỏ qua cột embedding để file JSON nhẹ và dễ đọc)
            # Nếu bảng Day 6 lưu cả 3 strategy (fixed, paragraph...), bạn có thể thêm WHERE id LIKE '%_fixed_%'
            cur.execute(f"SELECT * FROM {TABLE_NAME};")
            rows = cur.fetchall()

        exported = []
        for r in rows:
            meta = r.get("metadata") or {}
            if isinstance(meta, str):
                meta = json.loads(meta)
                
            chunk_id = str(r.get("id") or r.get("chunk_id"))
            source_id = str(r.get("source_id") or r.get("document_id") or meta.get("source_id") or "gutenberg_tesla_inventions_39272")
            source = str(r.get("source") or meta.get("source") or "pg39272-images.html")
            page = r.get("page") if r.get("page") is not None else (meta.get("page") or meta.get("unit_id") or 1)
            text = str(r.get("text") or r.get("content") or "")

            exported.append({
                "id": chunk_id,
                "source_id": source_id,
                "source": source,
                "page": page,
                "text": text,
                "metadata": meta
            })

        out_path = Path("day6_chunks_raw.json")
        out_path.write_text(json.dumps(exported, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"Đã xuất thành công {len(exported)} chunks ra file: {out_path.resolve()}")

    finally:
        conn.close()

if __name__ == "__main__":
    export_chunks()