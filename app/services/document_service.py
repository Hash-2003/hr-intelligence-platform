import hashlib
from pathlib import Path

from sqlalchemy import desc
from sqlalchemy.orm import Session

from app.database import Document, DocumentChunk


class DocumentService:
    """Service layer for controlled HR document ingestion and retrieval."""

    def __init__(self, db: Session):
        self.db = db

    def ingest_local_document(
        self,
        file_path: Path,
        document_type: str = "policy",
    ) -> tuple[Document, int, bool]:
        """Ingest or refresh one local HR document."""
        self.validate_supported_file(file_path)

        text = self.read_text_file(file_path)
        content_hash = self.hash_text(text)

        existing = (
            self.db.query(Document)
            .filter(Document.filename == file_path.name)
            .first()
        )

        if existing and existing.content_hash == content_hash:
            return existing, 0, False

        if existing:
            self._delete_document_chunks(existing.id)
            existing.title = self.title_from_filename(file_path.name)
            existing.document_type = document_type
            existing.source_path = str(file_path)
            existing.content_hash = content_hash
            document = existing
        else:
            document = Document(
                title=self.title_from_filename(file_path.name),
                document_type=document_type,
                filename=file_path.name,
                source_path=str(file_path),
                source="local_seed",
                content_hash=content_hash,
            )
            self.db.add(document)

        self.db.commit()
        self.db.refresh(document)

        chunks = self.chunk_text(text)

        for index, chunk_text in enumerate(chunks):
            chunk = DocumentChunk(
                document_id=document.id,
                chunk_index=index,
                content=chunk_text,
                token_estimate=self.estimate_tokens(chunk_text),
            )
            self.db.add(chunk)

        self.db.commit()

        return document, len(chunks), True

    def ingest_directory(
        self,
        directory_path: Path,
        document_type: str = "policy",
    ) -> list[tuple[Document, int, bool]]:
        """Ingest all supported documents from a local directory."""
        if not directory_path.exists():
            raise ValueError(f"Directory does not exist: {directory_path}")

        results: list[tuple[Document, int, bool]] = []

        for file_path in sorted(directory_path.iterdir()):
            if file_path.is_file() and file_path.suffix.lower() in {".txt", ".md"}:
                results.append(
                    self.ingest_local_document(
                        file_path=file_path,
                        document_type=document_type,
                    )
                )

        return results

    def get_documents(self, limit: int = 50) -> list[Document]:
        """Retrieve ingested HR documents."""
        return (
            self.db.query(Document)
            .order_by(desc(Document.created_at))
            .limit(limit)
            .all()
        )

    def get_document_by_id(self, document_id: int) -> Document | None:
        """Retrieve one document by ID."""
        return (
            self.db.query(Document)
            .filter(Document.id == document_id)
            .first()
        )

    def get_document_chunks(self, document_id: int) -> list[DocumentChunk]:
        """Retrieve chunks for one document."""
        return (
            self.db.query(DocumentChunk)
            .filter(DocumentChunk.document_id == document_id)
            .order_by(DocumentChunk.chunk_index)
            .all()
        )

    def _delete_document_chunks(self, document_id: int) -> None:
        """Delete existing chunks before refreshing a changed document."""
        chunks = (
            self.db.query(DocumentChunk)
            .filter(DocumentChunk.document_id == document_id)
            .all()
        )

        for chunk in chunks:
            self.db.delete(chunk)

        self.db.commit()

    @staticmethod
    def validate_supported_file(file_path: Path) -> None:
        """Validate supported local document extensions."""
        if file_path.suffix.lower() not in {".txt", ".md"}:
            raise ValueError("Only .txt and .md files are supported.")

    @staticmethod
    def read_text_file(file_path: Path) -> str:
        """Read a UTF-8 local document."""
        try:
            text = file_path.read_text(encoding="utf-8")
        except UnicodeDecodeError as exc:
            raise ValueError(f"File must be valid UTF-8 text: {file_path}") from exc

        cleaned = text.strip()

        if not cleaned:
            raise ValueError(f"Document is empty: {file_path}")

        return cleaned

    @staticmethod
    def chunk_text(text: str, max_chars: int = 1200, overlap: int = 150) -> list[str]:
        """Split text into overlapping character-based chunks."""
        if max_chars <= overlap:
            raise ValueError("max_chars must be greater than overlap.")

        chunks: list[str] = []
        start = 0
        text_length = len(text)

        while start < text_length:
            end = min(start + max_chars, text_length)
            chunk = text[start:end].strip()

            if chunk:
                chunks.append(chunk)

            if end == text_length:
                break

            start = end - overlap

        return chunks

    @staticmethod
    def estimate_tokens(text: str) -> int:
        """Estimate token count using a simple character heuristic."""
        return max(1, len(text) // 4)

    @staticmethod
    def hash_text(text: str) -> str:
        """Create a stable SHA-256 hash for document change detection."""
        return hashlib.sha256(text.encode("utf-8")).hexdigest()

    @staticmethod
    def title_from_filename(filename: str) -> str:
        """Create a readable title from a file name."""
        stem = Path(filename).stem
        return stem.replace("_", " ").replace("-", " ").title()