from pydantic import BaseModel
from uuid import UUID
from typing import List

class Dataset(BaseModel):
    id: UUID
    tenant_id: str
    asset_id: str | None = None
    name: str | None = None
    version: str | None = None
    storage_uri: str | None = None
    columns: List[str] | None = None
    row_count: int | None = None
    byte_size: int | None = None
    profile_path: str | None = None
