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
        Generates and saves deterministic rule-based insights when AI provider is disabled.
        """
        def format_inr(val: float) -> str:
            if val is None:
                return "₹0"
            is_neg = val < 0
            val = abs(val)
            s = f"{val:.2f}"
            parts = s.split('.')
            int_part = parts[0]
            dec_part = parts[1]
            if len(int_part) <= 3:
                formatted_int = int_part
            else:
                last_three = int_part[-3:]
                remaining = int_part[:-3]
                groups = []
                while remaining:
                    groups.append(remaining[-2:])
                    remaining = remaining[:-2]
                groups.reverse()
                formatted_int = ",".join(groups) + "," + last_three
            formatted_val = f"₹{'-' if is_neg else ''}{formatted_int}.{dec_part}"
            if formatted_val.endswith(".00"):
                formatted_val = formatted_val[:-3]
            return formatted_val

        # 1. Resolve active version ID
        version_id = None
        if dataset_id:
            from app.models.dataset import Dataset
            ds = await self.db.get(Dataset, dataset_id)
            if ds:
                version_id = ds.active_version_id

        if dataset_id and version_id:
            # Initialize metrics variables
            total_borrowers = 0
            total_exposure = 0.0
            avg_risk_score = 0.0
            high_risk_pct = 0.0
            low_risk_pct = 0.0
            medium_risk_pct = 0.0
            hhi = 0.0
            top_purpose_name = "N/A"
            top_purpose_pct = 0.0
            top_region_name = "N/A"
            top_region_pct = 0.0
            top_employment_name = "N/A"
            top_employment_pct = 0.0
            avg_repayment_burden = 0.0
            burden_exceeded_count = 0
            dq_health_score = 100.0
            completeness_score = 100.0
            missing_value_percentage = 0.0
            duplicate_percentage = 0.0
            rule_violations = 0
            drift_detected = False
            drift_status = "No schema drift detected"

            # Fetch Portfolio Metrics
            try:
                portfolio_engine = PortfolioAnalyticsEngine(self.db)
                portfolio_metrics = await portfolio_engine.get_metrics(dataset_id, version_id)
                total_borrowers = portfolio_metrics.get("total_borrowers", 0)
                total_exposure = portfolio_metrics.get("outstanding_exposure", 0.0)
                avg_risk_score = portfolio_metrics.get("average_risk_score", 0.0)
                
                # Fetch low/medium/high risk count from RiskAssessment table
                from app.models.risk_assessment import RiskAssessment
                stmt = select(RiskAssessment).where(
                    RiskAssessment.dataset_id == dataset_id, RiskAssessment.version_id == version_id
                )
                res = await self.db.execute(stmt)
                assessments = list(res.scalars().all())
                total_ass = len(assessments)
                if total_ass > 0:
                    cats = {"LOW": 0, "MEDIUM": 0, "HIGH": 0}
                    for a in assessments:
                        cat_str = a.risk_category.value if hasattr(a.risk_category, "value") else str(a.risk_category)
                        if cat_str in cats:
                            cats[cat_str] += 1
                    low_risk_pct = (cats["LOW"] / total_ass) * 100.0
                    medium_risk_pct = (cats["MEDIUM"] / total_ass) * 100.0
                    high_risk_pct = (cats["HIGH"] / total_ass) * 100.0

                exposure_dist = portfolio_metrics.get("visualizations", {}).get("exposure_distribution", {})
                
                # Purposes
                purpose_dict = exposure_dist.get("loan_purposes", {})
                if purpose_dict:
                    top_purpose_name, top_purpose_val = max(purpose_dict.items(), key=lambda x: x[1])
                    top_purpose_pct = (top_purpose_val / total_exposure) * 100.0 if total_exposure else 0.0
                
                # Regions
                region_dict = exposure_dist.get("regions", {})
                if region_dict:
                    top_region_name, top_region_val = max(region_dict.items(), key=lambda x: x[1])
                    top_region_pct = (top_region_val / total_exposure) * 100.0 if total_exposure else 0.0
                
                # Employments
                employment_dict = exposure_dist.get("employment_types", {})
                if employment_dict:
                    top_employment_name, top_employment_val = max(employment_dict.items(), key=lambda x: x[1])
                    top_employment_pct = (top_employment_val / total_exposure) * 100.0 if total_exposure else 0.0
            except Exception as e:
                logger.error("Failed to gather portfolio metrics for fallback: %s", e)

            # Fetch Concentration Metrics
            try:
                concentration_engine = ConcentrationEngine(self.db)
                concentration_metrics = await concentration_engine.get_metrics(dataset_id, version_id)
                hhi = concentration_metrics.get("herfindahl_hirschman_index", 0.0)
            except Exception as e:
                logger.error("Failed to gather concentration metrics for fallback: %s", e)

            # Fetch Loan Analytics Metrics
            try:
                loan_engine = LoanAnalyticsEngine(self.db)
                loan_metrics = await loan_engine.get_metrics(dataset_id, version_id)
                burden_val = loan_metrics.get("repayment_burden_ratio")
                if isinstance(burden_val, (int, float)):
                    avg_repayment_burden = burden_val
                else:
                    avg_repayment_burden = 0.0
                if avg_repayment_burden < 1.0:
                    avg_repayment_burden = avg_repayment_burden * 100.0

                from app.models.loan import Loan
                from sqlalchemy import func
                burden_stmt = select(func.count()).select_from(Loan).where(
                    Loan.dataset_id == dataset_id,
                    Loan.version_id == version_id,
                    Loan.repayment_burden_ratio > 0.40
                )
                burden_exceeded_count = (await self.db.execute(burden_stmt)).scalar() or 0
            except Exception as e:
                logger.error("Failed to gather loan metrics for fallback: %s", e)

            # Fetch Data Quality Metrics
            try:
                dq_engine = DataQualityEngine(self.db)
                dq_metrics = await dq_engine.get_metrics(dataset_id, version_id)
                dq_health_score = dq_metrics.get("dataset_health_score", 100.0)
                completeness_score = dq_metrics.get("completeness_score", 100.0)
                missing_value_percentage = dq_metrics.get("missing_value_percentage", 0.0)
                duplicate_percentage = dq_metrics.get("duplicate_percentage", 0.0)
                rule_violations = dq_metrics.get("invalid_business_rule_count", 0)
                
                drift_info = dq_metrics.get("schema_drift_indicator", {})
                if isinstance(drift_info, dict):
                    drift_detected = drift_info.get("drift_detected", False)
                else:
                    drift_detected = "drift" in str(drift_info).lower()
                
                if drift_detected:
                    drift_status = "Schema drift detected between current version and baseline"
                else:
                    drift_status = "No schema drift detected between current version and baseline"
            except Exception as e:
                logger.error("Failed to gather data quality metrics for fallback: %s", e)

            # Determine Statuses
            high_risk_status = "Healthy"
            if high_risk_pct > 25:
                high_risk_status = "Concern"
            elif high_risk_pct >= 15:
                high_risk_status = "Watch"

            hhi_status = "Diversified"
            if hhi > 2500:
                hhi_status = "High Concentration"
            elif hhi >= 1500:
                hhi_status = "Moderate"

            dq_status = "Excellent"
            if dq_health_score < 85:
                dq_status = "Needs Attention"
            elif dq_health_score <= 95:
                dq_status = "Acceptable"

            # Construct Commentary Sections
            formatted_exposure = format_inr(total_exposure)
            executive_summary = (
                f"The portfolio contains {total_borrowers} borrowers with total exposure of {formatted_exposure}. "
                f"Low-risk borrowers account for {low_risk_pct:.1f}%, medium-risk {medium_risk_pct:.1f}%, and high-risk {high_risk_pct:.1f}%. "
                f"Portfolio concentration remains elevated with an HHI score of {hhi:.1f}."
            )

            key_findings = [
                f"The high-risk borrower segment represents {high_risk_pct:.1f}% of the portfolio, which is classified as a {high_risk_status} level.",
                f"Portfolio concentration is {hhi_status} with a regional HHI score of {hhi:.1f}.",
                f"Overall data quality score remains {dq_status} at {dq_health_score:.1f}%."
            ]
            if top_purpose_name != "N/A":
                key_findings.append(
                    f"{top_purpose_name} sector represents largest exposure segment, accounting for {top_purpose_pct:.1f}% of total portfolio value."
                )
            if avg_repayment_burden > 0.0 or burden_exceeded_count > 0:
                key_findings.append(
                    f"Repayment burden exceeds 40% for {burden_exceeded_count} loans/borrowers, with a portfolio average ratio of {avg_repayment_burden:.1f}%."
                )

            # Check Trends
            try:
                trend_engine = TrendEngine(self.db)
                trend_metrics = await trend_engine.get_metrics(dataset_id, version_id)
                risk_trends = trend_metrics.get("visualizations", {}).get("risk_score_trend_line", [])
                if len(risk_trends) >= 2:
                    first_risk = risk_trends[0].get("average_risk_score", 0.0)
                    last_risk = risk_trends[-1].get("average_risk_score", 0.0)
                    if last_risk > first_risk:
                        key_findings.append(f"Historical trend analysis indicates an increasing risk profile, with monthly average risk score rising from {first_risk:.2f} to {last_risk:.2f}.")
                    else:
                        key_findings.append(f"Historical trend analysis indicates a stable risk profile, with monthly average risk score moving from {first_risk:.2f} to {last_risk:.2f}.")
            except Exception as e:
                logger.error("Failed to query trends for fallback findings: %s", e)

            completeness_status = "high-integrity" if completeness_score >= 99.0 else "minor omissions"
            risk_observations = [
                f"Schema drift assessment: {drift_status}.",
                f"Data completeness is at {completeness_score:.1f}%, indicating {completeness_status} coverage of required canonical fields.",
                f"Missing value density remains within acceptable limits at {missing_value_percentage:.2f}%.",
                f"Duplicate ratio remains healthy at {duplicate_percentage:.2f}%.",
                f"Rule violations detected in {rule_violations} records."
            ]

            recommendations = []
            if high_risk_pct > 15:
                recommendations.append("Increase monitoring of high-risk borrower segments.")
            else:
                recommendations.append("Maintain standard credit monitoring controls for high-risk borrower segments.")

            if hhi > 1500 or top_purpose_pct > 25:
                recommendations.append(f"Reduce concentration in dominant sectors, particularly {top_purpose_name}, to mitigate sector concentration risk.")
            else:
                recommendations.append("Continue current diversified sector exposure limits.")

            if burden_exceeded_count > 0:
                recommendations.append("Strengthen underwriting for borrowers with high repayment burden.")
            else:
                recommendations.append("Maintain current debt serviceability check standards.")

            if hhi > 1500 or top_region_pct > 25:
                recommendations.append("Diversify portfolio allocation across regions.")
            else:
                recommendations.append("Continue geographic distribution strategy.")

            if dq_health_score < 95:
                recommendations.append("Enforce stricter validation checks at data ingestion stage and address outstanding rule violations in the system.")
            else:
                recommendations.append("Continue maintaining current data quality controls.")
        else:
            # Fallback if no dataset is active
            executive_summary = (
                "The analysis could not retrieve active credit portfolio metrics. "
                "Please ensure that a valid dataset with an active version is uploaded and selected."
            )
            key_findings = [
                "No active dataset version found for metrics extraction.",
                "Verify schema mapping and validation status of the catalog."
            ]
            risk_observations = [
                "Analysis engine could not determine schema drift or completeness without version scope."
            ]
            recommendations = [
                "Upload a valid CSV loan portfolio file.",
                "Ensure active version is set in the data catalog registry."
            ]

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
            provider="Portfolio Analytics",
            model_name="Rule-based Fallback",
            generated_by=self.user.id,
        )
        self.db.add(insight)
        await self.db.flush()
        return insight
