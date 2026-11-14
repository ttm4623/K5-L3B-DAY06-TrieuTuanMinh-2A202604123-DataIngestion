"""Choose a real embedding provider (API or local) and implement this contract."""
from typing import Protocol
from sentence_transformers import SentenceTransformer


class Embedder(Protocol):
    model_name: str
    dimensions: int

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        """Return one vector per input text, in the same order."""
        ...

    def embed_query(self, question: str) -> list[float]:
        """Return a query vector compatible with the stored document vectors."""
        ...


class MyEmbedder:
    """Real embedder adapter using SentenceTransformers."""

    def __init__(self, model_name: str = "all-MiniLM-L6-v2") -> None:
        self.model_name = model_name
        print(f"Đang khởi tạo embedding model: {self.model_name}...")
        self._model = SentenceTransformer(self.model_name)
        self.dimensions = self._model.get_sentence_embedding_dimension()
        print(f"Model đã sẵn sàng. Số chiều vector (dimensions): {self.dimensions}")

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        """Return one vector per input text, in the same order."""
        if not texts:
            return []
        embeddings = self._model.encode(texts, show_progress_bar=False, convert_to_tensor=False)
        return embeddings.tolist()

    def embed_query(self, question: str) -> list[float]:
        """Return a query vector compatible with the stored document vectors."""
        if not question:
            return []
        embedding = self._model.encode(question, convert_to_tensor=False)
        return embedding.tolist()