from pathlib import Path

from app.database import SessionLocal, create_db_tables
from app.services.document_service import DocumentService


DOCUMENT_DIR = Path("data/hr_documents")


def main() -> None:
    """Ingest controlled HR documents from the local data directory."""
    create_db_tables()

    db = SessionLocal()

    try:
        service = DocumentService(db)
        results = service.ingest_directory(DOCUMENT_DIR)

        if not results:
            print("No supported documents found.")

        for document, chunks_created, changed in results:
            status = "ingested" if changed else "unchanged"
            print(
                f"{status}: {document.filename} "
                f"(document_id={document.id}, chunks={chunks_created})"
            )

    finally:
        db.close()


if __name__ == "__main__":
    main()