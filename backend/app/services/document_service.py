import uuid
from pathlib import Path

from fastapi import HTTPException, UploadFile

from app.services.pdf_service import extract_text_from_pdf
from app.services.chunk_service import chunk_text
from app.services.embedding_service import generate_embeddings
from app.db.vector_store import store_embeddings


UPLOAD_DIR = Path(__file__).resolve().parents[3] / "storage" / "uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


async def save_uploaded_pdf(file: UploadFile) -> dict:
    if file.content_type != "application/pdf":
        raise HTTPException(status_code=400, detail="Only PDF files are allowed.")

    file_path = UPLOAD_DIR / file.filename
    contents = await file.read()

    with open(file_path, "wb") as f:
        f.write(contents)

    extracted_text = extract_text_from_pdf(file_path)
    chunks = chunk_text(extracted_text)
    embeddings = generate_embeddings(chunks)

    doc_id = str(uuid.uuid4())
    store_embeddings(
        collection_name="documents",
        chunks=chunks,
        embeddings=embeddings,
        doc_id=doc_id,
    )

    return {
        "message": "File uploaded successfully.",
        "filename": file.filename,
        "content_type": file.content_type,
        "file_path": str(file_path),
        "extracted_text": extracted_text,
        "chunks": chunks,
        "chunk_count": len(chunks),
    }