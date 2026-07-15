import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from app.enums.analysis_type import AnalysisTypeEnum
from app.schemas.common import BaseSchema, UUIDModel


class AIInsightGenerateRequest(BaseModel):
    """Configuration parameters to execute an AI LLM insight generation run."""

    dataset_id: Optional[uuid.UUID] = Field(default=None, description="Scope to a structured dataset")
    document_id: Optional[uuid.UUID] = Field(default=None, description="Scope to an unstructured compliance doc")
    analysis_type: AnalysisTypeEnum = Field(description="Target analytics lens model to request")
    force_regenerate: bool = Field(default=False, description="Bypass cache and generate fresh insights")


class AIInsightResponse(UUIDModel):
    """Analytical summary context extracted by the LLM helper."""

    dataset_id: Optional[uuid.UUID] = None
    document_id: Optional[uuid.UUID] = None
    analysis_type: AnalysisTypeEnum
    executive_summary: Optional[str] = None
    key_findings_json: Optional[List[Any]] = Field(default=None, alias="key_findings")
    risk_observations_json: Optional[List[Any]] = Field(default=None, alias="risk_observations")
    recommendations_json: Optional[List[Any]] = Field(default=None, alias="recommendations")
    source_metrics_json: Optional[Dict[str, Any]] = Field(default=None, alias="source_metrics")
    provider: Optional[str] = None
    model_name: Optional[str] = None
    generated_by: Optional[uuid.UUID] = None
    created_at: datetime


class AIInsightListResponse(BaseSchema):
    """Wrapper response for insights list."""

    items: List[AIInsightResponse]
    total: int
