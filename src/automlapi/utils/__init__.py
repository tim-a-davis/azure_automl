"""Utility helpers for working with SQLAlchemy models and Pydantic schemas."""

from typing import Iterable, Type, TypeVar

from pydantic import BaseModel

ModelT = TypeVar("ModelT")
SchemaT = TypeVar("SchemaT", bound=BaseModel)


def model_to_schema(model: ModelT, schema_cls: Type[SchemaT]) -> SchemaT:
    """Convert a SQLAlchemy model instance to a Pydantic schema."""
    return schema_cls.model_validate(model, from_attributes=True)


def models_to_schema(models: Iterable[ModelT], schema_cls: Type[SchemaT]) -> list[SchemaT]:
    """Convert an iterable of SQLAlchemy models to a list of Pydantic schemas."""
    return [model_to_schema(m, schema_cls) for m in models]
