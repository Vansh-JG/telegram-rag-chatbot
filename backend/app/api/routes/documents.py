from fastapi import APIRouter, File, UploadFile

from app.schemas.document import DocumentUploadResponse
from app.services.document_service import save_uploaded_pdf

router = APIRouter()


@router.post("/documents/upload", response_model=DocumentUploadResponse)
async def upload_document(file: UploadFile = File(...)) -> DocumentUploadResponse:
    result = await save_uploaded_pdf(file)
    return DocumentUploadResponse(**result)