from typing import Any

from pydantic import BaseModel, Field


class ExtractionRequest(BaseModel):
    field_type: str = Field(alias="fieldType")
    answer: str
    user_language: str = Field(alias="userLanguage")
    source_language: str = Field(alias="sourceLanguage")
    output_language: str = Field(alias="outputLanguage")

    model_config = {
        "populate_by_name": True,
    }


class ExtractionResult(BaseModel):
    normalized_value: Any = Field(alias="normalizedValue")
    output_value: str | None = Field(alias="outputValue")
    requires_clarification: bool = Field(alias="requiresClarification")
    uncertainties: list[str] = Field(default_factory=list)

    model_config = {
        "populate_by_name": True,
    }
