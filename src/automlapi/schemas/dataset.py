from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, Field


class Dataset(BaseModel):
    id: UUID
    tenant_id: str
    asset_id: Optional[str] = None
    name: Optional[str] = None
    version: Optional[str] = None
    storage_uri: Optional[str] = None
    columns: Optional[List[str]] = Field(
        default=None, description="List of column names in the dataset"
    )
    row_count: Optional[int] = None
    byte_size: Optional[int] = None
    profile_path: Optional[str] = None
