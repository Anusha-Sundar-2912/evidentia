from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class DocumentUploadResponse(BaseModel):
    id: UUID
    filename: str
    source_type: str
    status: str
    chunk_count: int
    created_at: datetime

    model_config = {
        "from_attributes": True
    }