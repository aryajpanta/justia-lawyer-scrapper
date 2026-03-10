from pydantic import BaseModel, Field
from typing import Optional


class Lawyer(BaseModel):
    """Schema for lawyer listing data extracted from Justia."""
    Name: str = Field(..., description="The lawyer's full name")
    Phone: Optional[str] = Field(None, description="Their contact phone number")
    Address: Optional[str] = Field(None, description="Their physical office address")
    Profile_URL: str = Field(..., description="The link to their Justia profile")
    Bio_Experience: Optional[str] = Field(
        None, description="Any brief text about their law school or experience"
    )

    class Config:
        extra = 'ignore'  # Ignore extra fields from extraction
