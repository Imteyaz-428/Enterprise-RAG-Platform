from pydantic import BaseModel, Field
from typing import Optional

class OrganizationCreate(BaseModel):
    name: str = Field( min_length=2,  max_length=100)

    slug: str = Field( min_length=2,max_length=100, pattern=r"^[a-z0-9-]+$")


class OrganizationResponse(BaseModel):
    id: int
    name: str
    slug: str

    class Config:
        from_attributes = True
        

class OrganizationUpdate(BaseModel):

    name: Optional[str] = Field(
        default=None,
        min_length=2,
        max_length=100
    )

    slug: Optional[str] = Field(
        default=None,
        min_length=2,
        max_length=100,
        pattern=r"^[a-z0-9-]+$"
    )
    
    
class OrganizationInfo(BaseModel):
    id: int
    name: str
    slug: str

    class Config:
        from_attributes = True