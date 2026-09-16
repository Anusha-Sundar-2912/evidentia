import os
import shutil
import uuid
from pathlib import Path

from fastapi import (
    APIRouter,
    Depends,
    File,
    HTTPException,
    UploadFile,
)
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.chunk import Chunk
from app.models.document import Document
from app.schemas.document import DocumentUploadResponse
from app.services.chunker import chunk_pages
from app.services.embeddings import generate_embeddings
from app.services.parser import parse_document


router = APIRouter()


UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(
    parents=True,
    exist_ok=True,
)


ALLOWED_EXTENSIONS = {
    ".pdf",
    ".docx",
}


@router.post(
    "/upload",
    response_model=DocumentUploadResponse,
)
async def upload_document(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    if not file.filename:
        raise HTTPException(
            status_code=400,
            detail="File name is missing.",
        )

    extension = Path(file.filename).suffix.lower()

    if extension not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=(
                "Unsupported file type. "
                "Only PDF and DOCX are currently supported."
            ),
        )

    unique_name = (
        f"{uuid.uuid4()}{extension}"
    )

    file_path = UPLOAD_DIR / unique_name

    try:
        with file_path.open("wb") as buffer:
            shutil.copyfileobj(
                file.file,
                buffer,
            )

        file_size = os.path.getsize(file_path)

        document = Document(
            filename=file.filename,
            source_type=extension.replace(".", ""),
            content_type=file.content_type,
            file_size=file_size,
            status="processing",
        )

        db.add(document)
        db.commit()
        db.refresh(document)

        pages = parse_document(
            str(file_path)
        )

        chunks = chunk_pages(pages)

        if not chunks:
            document.status = "failed"
            db.commit()

            raise HTTPException(
                status_code=400,
                detail=(
                    "No readable text could be "
                    "extracted from the document."
                ),
            )

        texts = [
            chunk["content"]
            for chunk in chunks
        ]

        embeddings = generate_embeddings(
            texts
        )

        for chunk_data, embedding in zip(
            chunks,
            embeddings,
        ):
            chunk = Chunk(
                document_id=document.id,
                chunk_index=chunk_data[
                    "chunk_index"
                ],
                content=chunk_data[
                    "content"
                ],
                page_number=chunk_data[
                    "page_number"
                ],
                chunk_metadata={
                    "filename": file.filename,
                    "source_type": extension.replace(
                        ".",
                        "",
                    ),
                },
                embedding=embedding,
            )

            db.add(chunk)

        document.chunk_count = len(chunks)
        document.status = "ready"

        db.commit()
        db.refresh(document)

        return document

    except HTTPException:
        raise

    except Exception as exc:
        db.rollback()

        raise HTTPException(
            status_code=500,
            detail=f"Document ingestion failed: {str(exc)}",
        ) from exc

    finally:
        try:
            if file_path.exists():
                file_path.unlink()
        except OSError:
            pass