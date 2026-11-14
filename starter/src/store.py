"""Store and search vectors using PostgreSQL + pgvector."""
from typing import Any
import json
import psycopg2
from pgvector.psycopg2 import register_vector
from models import Chunk


class PgVectorStore:
    def __init__(self, database_url: str, dimensions: int) -> None:
        """Retain connection settings; validate model dimensions."""
        self.database_url = database_url
        self.dimensions = dimensions
        self._conn = psycopg2.connect(database_url)
        register_vector(self._conn)

    def create_schema(self) -> None:
        """Create table with vector column and source/page/filter metadata."""
        with self._conn.cursor() as cur:
            cur.execute("CREATE EXTENSION IF NOT EXISTS vector;")
            cur.execute(f"""
                CREATE TABLE IF NOT EXISTS chunks (
                    strategy VARCHAR(50),
                    chunk_id VARCHAR(255),
                    document_id VARCHAR(255),
                    source TEXT,
                    page INT,
                    text TEXT,
                    metadata JSONB,
                    embedding vector({self.dimensions}),
                    PRIMARY KEY (strategy, chunk_id)
                );
            """)
            self._conn.commit()

    def upsert(self, strategy: str, chunks: list[Chunk], vectors: list[list[float]]) -> None:
        """Validate lengths/dimensions and write stable IDs without duplicates.

        When re-ingesting changed source documents, remove obsolete chunks too.
        """
        if len(chunks) != len(vectors):
            raise ValueError("Số lượng chunks và vectors không khớp nhau.")
        
        if not chunks:
            return

        doc_ids = set(c.document_id for c in chunks)

        with self._conn.cursor() as cur:
            # Xóa các chunk cũ thuộc document và strategy này để loại bỏ obsolete chunks
            for doc_id in doc_ids:
                cur.execute(
                    "DELETE FROM chunks WHERE strategy = %s AND document_id = %s;",
                    (strategy, doc_id)
                )

            insert_query = """
                INSERT INTO chunks (strategy, chunk_id, document_id, source, page, text, metadata, embedding)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (strategy, chunk_id) DO UPDATE 
                SET text = EXCLUDED.text, 
                    source = EXCLUDED.source,
                    page = EXCLUDED.page,
                    metadata = EXCLUDED.metadata,
                    embedding = EXCLUDED.embedding;
            """

            data = []
            for chunk, vec in zip(chunks, vectors):
                if len(vec) != self.dimensions:
                    raise ValueError(f"Số chiều vector {len(vec)} không khớp với dimensions của store ({self.dimensions}).")
                data.append((
                    strategy,
                    chunk.chunk_id,
                    chunk.document_id,
                    chunk.source,
                    chunk.page,
                    chunk.text,
                    json.dumps(chunk.metadata),
                    vec
                ))

            cur.executemany(insert_query, data)
            self._conn.commit()

    def search(self, strategy: str, query_vector: list[float], top_k: int = 3,
               filters: dict[str, Any] | None = None) -> list[dict[str, Any]]:
        """Filter permitted metadata in SQL, rank by cosine distance, return top-k.

        Return chunk ID, text, score and metadata. Parameterize user-supplied values.
        """
        with self._conn.cursor() as cur:
            sql = """
                SELECT chunk_id, text, 1 - (embedding <=> %s::vector) AS score, metadata, source, page
                FROM chunks
                WHERE strategy = %s
            """
            params = [query_vector, strategy]

            if filters:
                for key, val in filters.items():
                    sql += " AND metadata->>%s = %s"
                    params.extend([key, str(val)])

            sql += " ORDER BY embedding <=> %s::vector LIMIT %s;"
            params.extend([query_vector, top_k])

            cur.execute(sql, params)
            rows = cur.fetchall()

            results = []
            for row in rows:
                results.append({
                    "chunk_id": row[0],
                    "text": row[1],
                    "score": float(row[2]),
                    "metadata": row[3],
                    "source": row[4],
                    "page": row[5]
                })
            return results