from pydantic import BaseModel


class DocumentUploadResponse(BaseModel):
    message: str
    filename: str
    content_type: str
    file_path: str
    extracted_text: str
    chunks: list[str]
    chunk_count: int