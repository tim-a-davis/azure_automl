from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, Field


class Dataset(BaseModel):
    id: UUID
    uploaded_by: UUID = Field(description="User ID who uploaded the dataset")
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
    tags: Optional[Dict[str, Any]] = Field(
        default=None, description="Tags for categorization and metadata"
    )
    private: bool = Field(
        default=False, description="Whether the dataset is private to the uploader"
    )
