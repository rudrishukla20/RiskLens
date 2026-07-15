import json
import logging
import uuid
from typing import Any, Dict, Optional

import httpx
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.analytics.borrower_analytics_engine import BorrowerAnalyticsEngine
from app.analytics.concentration_engine import ConcentrationEngine

# Analytics Engine imports for metric retrieval grounding
from app.analytics.data_quality_engine import DataQualityEngine
from app.analytics.diagnostic_engine import DiagnosticEngine
from app.analytics.loan_analytics_engine import LoanAnalyticsEngine
from app.analytics.migration_engine import MigrationEngine
from app.analytics.portfolio_analytics_engine import PortfolioAnalyticsEngine
from app.analytics.profiling_engine import ProfilingEngine
from app.analytics.trend_engine import TrendEngine
from app.analytics.vintage_engine import VintageEngine
from app.core.config import settings
from app.enums.analysis_type import AnalysisTypeEnum
from app.models.ai_insight import AIInsight
from app.models.document_analysis_result import DocumentAnalysisResult as DocumentAnalysisResultModel
from app.models.document_extraction import DocumentExtraction
from app.models.risk_assessment import RiskAssessment
from app.models.user import User
from app.repositories.ai_insight_repository import AIInsightRepository

logger = logging.getLogger(__name__)

SYSTEM_INSTRUCTIONS = """You are a highly precise credit risk analysis assistant at RiskLens.
Your goal is to summarize financial and analytical data into clean, structured insights.

Strict constraints:
1. Do NOT act as a chatbot or engage in conversational banter.
2. Do NOT provide financial or investment advice.
3. Do NOT make automated loan decisions or approve/reject loans.
4. Do NOT modify risk scores or database values.
5. Do NOT fabricate or hallucinate any numbers, ratios, or metrics. All statements must be grounded strictly in the provided data.
6. Do NOT hide or omit missing fields.
7. Do NOT call external resources or search the internet.

Your response MUST be a clean, valid JSON object matching exactly this schema:
{
  "executive_summary": "Overall summary of the metrics and observations.",
  "key_findings": ["Finding 1", "Finding 2", ...],
  "risk_observations": ["Observation 1", "Observation 2", ...],
  "recommendations": ["Recommendation 1", "Recommendation 2", ...],
  "missing_data_caveats": ["Caveat 1", "Caveat 2", ...]
}
"""


class AIInsightService:
    """Service handling AI-powered commentaries and audit review summaries."""

    def __init__(self, db: AsyncSession, user: User) -> None:
        self.db = db
        self.user = user
        self.repo = AIInsightRepository(db)

    async def generate_insight(
        self,
        *,
        dataset_id: Optional[uuid.UUID] = None,
        version_id: Optional[uuid.UUID] = None,
        document_id: Optional[uuid.UUID] = None,
        analysis_type: AnalysisTypeEnum,
    ) -> AIInsight:
        """
        Coordinates generating and saving structured AI insights based on grounding metrics.
        """
        # 1. Clear previous insights of same type/dataset/document for idempotency
        del_stmt = delete(AIInsight).where(AIInsight.analysis_type == analysis_type)
        if dataset_id:
            del_stmt = del_stmt.where(AIInsight.dataset_id == dataset_id)
        if document_id:
            del_stmt = del_stmt.where(AIInsight.document_id == document_id)
        await self.db.execute(del_stmt)
        await self.db.flush()

        # 2. Gather source metrics
        source_metrics = await self._gather_grounding_metrics(
            dataset_id=dataset_id, version_id=version_id, document_id=document_id, analysis_type=analysis_type
        )

        # 3. Handle Disabled / Missing Config Mode
        provider = (settings.AI_PROVIDER or "disabled").strip().lower()
        if provider == "disabled":
            return await self._save_disabled_insight(
                dataset_id=dataset_id,
                document_id=document_id,
                analysis_type=analysis_type,
                source_metrics=source_metrics,
            )

        # 4. Construct Prompt
        prompt = self._build_prompt(analysis_type, source_metrics)

        # 5. Call Provider REST API via httpx
        executive_summary = ""
        key_findings = []
        risk_observations = []
        recommendations = []

        try:
            timeout = httpx.Timeout(float(settings.AI_REQUEST_TIMEOUT_SECONDS or 60.0))
            async with httpx.AsyncClient(timeout=timeout) as client:
                if provider == "openai":
                    if not settings.OPENAI_API_KEY:
                        raise ValueError("OPENAI_API_KEY is not configured in settings.")

                    url = "https://api.openai.com/v1/chat/completions"
                    headers = {"Authorization": f"Bearer {settings.OPENAI_API_KEY}", "Content-Type": "application/json"}
                    payload = {
                        "model": settings.AI_MODEL_NAME or "gpt-4o-mini",
                        "messages": [
                            {"role": "system", "content": SYSTEM_INSTRUCTIONS},
                            {"role": "user", "content": prompt},
                        ],
                        "temperature": 0.0,
                        "response_format": {"type": "json_object"},
                    }
                    response = await client.post(url, json=payload, headers=headers)
                    response.raise_for_status()
                    res_data = response.json()
                    content = res_data["choices"][0]["message"]["content"]

                elif provider == "anthropic":
                    if not settings.ANTHROPIC_API_KEY:
                        raise ValueError("ANTHROPIC_API_KEY is not configured in settings.")

                    url = "https://api.anthropic.com/v1/messages"
                    headers = {
                        "x-api-key": settings.ANTHROPIC_API_KEY,
                        "anthropic-version": "2023-06-01",
                        "Content-Type": "application/json",
                    }
                    payload = {
                        "model": settings.AI_MODEL_NAME or "claude-3-5-sonnet-20240620",
                        "max_tokens": 4000,
                        "system": SYSTEM_INSTRUCTIONS,
                        "messages": [{"role": "user", "content": prompt}],
                        "temperature": 0.0,
                    }
                    response = await client.post(url, json=payload, headers=headers)
                    response.raise_for_status()
                    res_data = response.json()
                    content = res_data["content"][0]["text"]
                else:
                    raise ValueError(f"Unsupported AI_PROVIDER: {provider}")

            # Parse structured JSON payload
            data = json.loads(content)
            executive_summary = data.get("executive_summary", "")
            key_findings = data.get("key_findings", [])
            risk_observations = data.get("risk_observations", [])
            recommendations = data.get("recommendations", [])

        except Exception as e:
            logger.exception("AI Insight request failed. Saving failure fallback details.")
            executive_summary = f"AI Insight generation encountered an error: {str(e)}"

        # 6. Save Insight record to database
        insight = AIInsight(
            id=uuid.uuid4(),
            dataset_id=dataset_id,
            document_id=document_id,
            analysis_type=analysis_type,
            executive_summary=executive_summary,
            key_findings_json=key_findings,
            risk_observations_json=risk_observations,
            recommendations_json=recommendations,
            source_metrics_json=source_metrics,
            provider=provider,
            model_name=settings.AI_MODEL_NAME or "default",
            generated_by=self.user.id,
        )
        self.db.add(insight)
        await self.db.flush()
        return insight

    async def _gather_grounding_metrics(
        self,
        dataset_id: Optional[uuid.UUID],
        version_id: Optional[uuid.UUID],
        document_id: Optional[uuid.UUID],
        analysis_type: AnalysisTypeEnum,
    ) -> Dict[str, Any]:
        """
        Dynamically executes the appropriate analytics engine to assemble strict grounding context.
        """
        if analysis_type == AnalysisTypeEnum.DOCUMENT:
            if not document_id:
                return {}
            # Query DocumentExtraction and DocumentAnalysisResultModel
            ext_stmt = select(DocumentExtraction).where(DocumentExtraction.document_id == document_id)
            ext_res = await self.db.execute(ext_stmt)
            ext = ext_res.scalar_one_or_none()

            analysis_stmt = select(DocumentAnalysisResultModel).where(
                DocumentAnalysisResultModel.document_id == document_id
            )
            analysis_res = await self.db.execute(analysis_stmt)
            analysis = analysis_res.scalar_one_or_none()

            return {
                "document_id": str(document_id),
                "ratios": analysis.extracted_financial_ratios_json if analysis else {},
                "text_length": len(ext.extracted_text) if ext and ext.extracted_text else 0,
                "text_excerpt": ext.extracted_text[:2500] if ext and ext.extracted_text else "",
            }

        # Handle structured data analytics engines
        if not dataset_id or not version_id:
            return {}

        if analysis_type == AnalysisTypeEnum.RISK:
            stmt = select(RiskAssessment).where(
                RiskAssessment.dataset_id == dataset_id, RiskAssessment.version_id == version_id
            )
            res = await self.db.execute(stmt)
            assessments = list(res.scalars().all())

            cats = {"LOW": 0, "MEDIUM": 0, "HIGH": 0}
            scores = []
            for a in assessments:
                cat_str = a.risk_category.value if hasattr(a.risk_category, "value") else str(a.risk_category)
                if cat_str in cats:
                    cats[cat_str] += 1
                scores.append(a.risk_score)

            return {
                "total_assessments": len(assessments),
                "risk_categories": cats,
                "average_risk_score": round(sum(scores) / len(scores), 2) if scores else 0.0,
            }

        engine_map = {
            AnalysisTypeEnum.DATA_QUALITY: DataQualityEngine,
            AnalysisTypeEnum.PROFILING: ProfilingEngine,
            AnalysisTypeEnum.BORROWER: BorrowerAnalyticsEngine,
            AnalysisTypeEnum.LOAN: LoanAnalyticsEngine,
            AnalysisTypeEnum.PORTFOLIO: PortfolioAnalyticsEngine,
            AnalysisTypeEnum.CONCENTRATION: ConcentrationEngine,
            AnalysisTypeEnum.TREND: TrendEngine,
            AnalysisTypeEnum.VINTAGE: VintageEngine,
            AnalysisTypeEnum.MIGRATION: MigrationEngine,
            AnalysisTypeEnum.DIAGNOSTIC: DiagnosticEngine,
        }

        if analysis_type not in engine_map:
            return {}

        engine_class = engine_map[analysis_type]
        engine = engine_class(self.db)
        return await engine.get_metrics(dataset_id, version_id)

    def _build_prompt(self, analysis_type: AnalysisTypeEnum, source_metrics: Dict[str, Any]) -> str:
        if analysis_type == AnalysisTypeEnum.DOCUMENT:
            return f"""Please analyze this extracted compliance document.
Extracted Ratios:
{json.dumps(source_metrics.get("ratios", {}), indent=2)}

Extracted Text Excerpt:
{source_metrics.get("text_excerpt", "")}
"""
        return f"""Please analyze these computed credit risk metrics for analysis lens: {analysis_type.value}.
Source Metrics:
{json.dumps(source_metrics, indent=2)}
"""

    async def _save_disabled_insight(
        self,
        dataset_id: Optional[uuid.UUID],
        document_id: Optional[uuid.UUID],
        analysis_type: AnalysisTypeEnum,
        source_metrics: Dict[str, Any],
    ) -> AIInsight:
        """
        Saves a clean mock insight stating that AI provider is disabled.
        """
        executive_summary = (
            "AI insight generation is disabled. Please verify your environment configurations (.env) "
            "and set AI_PROVIDER to 'openai' or 'anthropic' to enable automated LLM commentaries."
        )
        insight = AIInsight(
            id=uuid.uuid4(),
            dataset_id=dataset_id,
            document_id=document_id,
            analysis_type=analysis_type,
            executive_summary=executive_summary,
            key_findings_json=[],
            risk_observations_json=[],
            recommendations_json=[],
            source_metrics_json=source_metrics,
            provider="disabled",
            model_name="disabled",
            generated_by=self.user.id,
        )
        self.db.add(insight)
        await self.db.flush()
        return insight
