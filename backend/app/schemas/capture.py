from pydantic import BaseModel

from app.schemas.resource import ResourceCreate, ResourceOut


class BatchImportRequest(ResourceCreate):
    """Same shape as ResourceCreate — the batch endpoint takes a list of these."""


class BatchImportResult(BaseModel):
    created: list[ResourceOut]
    updated: list[ResourceOut]
