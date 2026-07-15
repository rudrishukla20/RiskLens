import logging
import os
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import fitz  # PyMuPDF
import pandas as pd
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.analytics.concentration_engine import ConcentrationEngine

# Engine imports for metric retrieval grounding
from app.analytics.data_quality_engine import DataQualityEngine
from app.analytics.diagnostic_engine import DiagnosticEngine
from app.analytics.loan_analytics_engine import LoanAnalyticsEngine
from app.analytics.portfolio_analytics_engine import PortfolioAnalyticsEngine
from app.core.config import settings
from app.enums.analysis_type import AnalysisTypeEnum
from app.enums.report_type import ReportTypeEnum
from app.models.ai_insight import AIInsight
from app.models.dataset import Dataset
from app.models.dataset_version import DatasetVersion
from app.models.document_analysis_result import DocumentAnalysisResult as DocumentAnalysisResultModel
from app.models.report import Report
from app.models.user import User
from app.repositories.report_repository import ReportRepository

logger = logging.getLogger(__name__)


class ReportService:
    """Service handling multi-format compliance and performance report compilations."""

    def __init__(self, db: AsyncSession, user: User) -> None:
        self.db = db
        self.user = user
        self.repo = ReportRepository(db)

    async def generate_report(
        self,
        *,
        dataset_id: Optional[uuid.UUID] = None,
        version_id: Optional[uuid.UUID] = None,
        document_id: Optional[uuid.UUID] = None,
        report_type: ReportTypeEnum,
        export_format: str,
    ) -> Report:
        """
        Gathers computed analytics metrics and AI commentary summaries, renders
        the file payload in PDF/Excel/CSV, and persists report metadata.
        """
        export_format = export_format.upper()
        if export_format not in ("PDF", "XLSX", "CSV"):
            raise ValueError(f"Unsupported export format: {export_format}")

        # 1. Gather context details
        user_name = self.user.full_name or "Unknown User"
        user_email = self.user.email or ""
        generated_by_str = f"{user_name} ({user_email})"
        timestamp_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

        dataset_name = "N/A"
        version_num = "N/A"

        if dataset_id:
            ds = await self.db.get(Dataset, dataset_id)
            if ds:
                dataset_name = ds.name
            if version_id:
                ver = await self.db.get(DatasetVersion, version_id)
                if ver:
                    version_num = f"V{ver.version_number}"

        # 2. Retrieve analytics metric tables and KPIs
        kpis, tables, charts, assumptions, missing_notes = await self._gather_report_metrics(
            dataset_id=dataset_id, version_id=version_id, document_id=document_id, report_type=report_type
        )

        # 3. Retrieve latest matching AI commentary
        ai_commentary = await self._get_ai_commentary(
            dataset_id=dataset_id, document_id=document_id, report_type=report_type
        )

        title = self._get_report_title(report_type)

        report_data = {
            "title": title,
            "generated_timestamp": timestamp_str,
            "generated_by": generated_by_str,
            "dataset_name": dataset_name,
            "version": version_num,
            "document_id": str(document_id) if document_id else "N/A",
            "kpis": kpis,
            "tables": tables,
            "charts": charts,
            "ai_commentary": ai_commentary,
            "assumptions": assumptions,
            "missing_notes": missing_notes,
        }

        # 4. Create reports output directory
        os.makedirs(settings.REPORT_DIR, exist_ok=True)
        file_id = uuid.uuid4().hex
        filename = f"report_{report_type.value.lower()}_{file_id}.{export_format.lower()}"
        storage_path = os.path.join(settings.REPORT_DIR, filename)

        # 5. Render file
        if export_format == "PDF":
            self._render_pdf(storage_path, report_data)
        elif export_format == "XLSX":
            self._render_excel(storage_path, report_data)
        elif export_format == "CSV":
            self._render_csv(storage_path, report_data)

        # 6. Persist report record in DB
        report_record = Report(
            id=uuid.uuid4(),
            dataset_id=dataset_id,
            report_type=report_type,
            title=title,
            generated_by=self.user.id,
            export_format=export_format,
            storage_path=storage_path,
            report_metadata_json={
                "kpis": kpis,
                "ai_commentary": ai_commentary,
                "assumptions": assumptions,
                "missing_notes": missing_notes,
                "audit_user": generated_by_str,
            },
        )
        self.db.add(report_record)
        await self.db.flush()
        return report_record

    def _get_report_title(self, report_type: ReportTypeEnum) -> str:
        mapping = {
            ReportTypeEnum.CREDIT_RISK_REPORT: "Credit Risk Assessment Report",
            ReportTypeEnum.PORTFOLIO_REPORT: "Portfolio Performance Report",
            ReportTypeEnum.DATA_QUALITY_REPORT: "Data Quality Scorecard Report",
            ReportTypeEnum.DIAGNOSTIC_ANALYTICS_REPORT: "Diagnostic Analytics & Root-Cause Report",
            ReportTypeEnum.DOCUMENT_ANALYSIS_REPORT: "Compliance Document Analysis Report",
            ReportTypeEnum.EXECUTIVE_SUMMARY_REPORT: "Executive Summary Consolidated Risk Report",
        }
        return mapping.get(report_type, "RiskLens Analytics Report")

    async def _get_ai_commentary(
        self, dataset_id: Optional[uuid.UUID], document_id: Optional[uuid.UUID], report_type: ReportTypeEnum
    ) -> str:
        """Helper to retrieve the latest matching AI commentary string."""
        mapping = {
            ReportTypeEnum.CREDIT_RISK_REPORT: AnalysisTypeEnum.RISK,
            ReportTypeEnum.PORTFOLIO_REPORT: AnalysisTypeEnum.PORTFOLIO,
            ReportTypeEnum.DATA_QUALITY_REPORT: AnalysisTypeEnum.DATA_QUALITY,
            ReportTypeEnum.DIAGNOSTIC_ANALYTICS_REPORT: AnalysisTypeEnum.DIAGNOSTIC,
            ReportTypeEnum.DOCUMENT_ANALYSIS_REPORT: AnalysisTypeEnum.DOCUMENT,
            ReportTypeEnum.EXECUTIVE_SUMMARY_REPORT: AnalysisTypeEnum.DIAGNOSTIC,  # Fallback
        }
        ans_type = mapping.get(report_type, AnalysisTypeEnum.DIAGNOSTIC)

        stmt = select(AIInsight).where(AIInsight.analysis_type == ans_type)
        if dataset_id:
            stmt = stmt.where(AIInsight.dataset_id == dataset_id)
        if document_id:
            stmt = stmt.where(AIInsight.document_id == document_id)

        stmt = stmt.order_by(AIInsight.created_at.desc()).limit(1)
        res = await self.db.execute(stmt)
        insight = res.scalars().first()

        return insight.executive_summary if insight else "No AI commentary generated for this assessment phase."

    async def _gather_report_metrics(
        self,
        dataset_id: Optional[uuid.UUID],
        version_id: Optional[uuid.UUID],
        document_id: Optional[uuid.UUID],
        report_type: ReportTypeEnum,
    ) -> tuple[Dict[str, Any], Dict[str, List[Any]], Dict[str, Any], List[str], List[str]]:
        """Coordinates fetching stats and formatting tables for the different report templates."""
        kpis = {}
        tables = {}
        charts = {}
        assumptions = ["All parameters are derived from deterministic rules without statistical model dependencies."]
        missing_notes = []

        if report_type == ReportTypeEnum.DOCUMENT_ANALYSIS_REPORT:
            if not document_id:
                return kpis, tables, charts, assumptions, ["Missing document target identifier."]

            # Fetch analysis result
            res_stmt = select(DocumentAnalysisResultModel).where(DocumentAnalysisResultModel.document_id == document_id)
            res = (await self.db.execute(res_stmt)).scalar_one_or_none()

            if res:
                kpis = {
                    "Extracted Ratios Count": len(res.extracted_financial_ratios_json or {}),
                    "Key Findings Count": len(res.key_findings_json or []),
                    "Risk Warnings Count": len(res.risk_notes_json or []),
                }
                # Ratios table
                tables["Extracted Ratios"] = [
                    {"Ratio Metric": k, "Extracted Value": str(v)}
                    for k, v in (res.extracted_financial_ratios_json or {}).items()
                ]
                # Findings tables
                tables["Key Findings"] = [
                    {"Severity": f.get("severity", "INFO"), "Detail": f.get("finding_detail", "")}
                    for f in (res.key_findings_json or [])
                ]
                tables["Compliance Observations"] = [
                    {
                        "Clause": f.get("policy_name", ""),
                        "Status": f.get("status", ""),
                        "Observation": f.get("observation", ""),
                    }
                    for f in (res.compliance_observations_json or [])
                ]
            else:
                missing_notes.append("No document analysis result record found in database.")
            return kpis, tables, charts, assumptions, missing_notes

        # All other reports belong to dataset analytics
        if not dataset_id or not version_id:
            return kpis, tables, charts, assumptions, ["Dataset or version identifiers are missing."]

        if report_type == ReportTypeEnum.DATA_QUALITY_REPORT:
            dq = await DataQualityEngine(self.db).get_metrics(dataset_id, version_id)
            if dq.get("status") == "success":
                kpis = {
                    "Total Records": dq.get("total_records"),
                    "Missing Values Percentage": f"{dq.get('missing_value_percentage', 0.0)}%",
                    "Completeness Score": f"{dq.get('completeness_score', 0.0)}/100",
                    "Validity Score": f"{dq.get('validity_score', 0.0)}/100",
                    "Dataset Health Score": f"{dq.get('dataset_health_score', 0.0)}/100",
                }
                # Wrap tables
                tables["Validation Scores"] = [
                    {"Dimension": "Completeness", "Score": dq.get("completeness_score")},
                    {"Dimension": "Validity", "Score": dq.get("validity_score")},
                    {"Dimension": "Uniqueness", "Score": dq.get("uniqueness_score")},
                    {"Dimension": "Consistency", "Score": dq.get("consistency_score")},
                ]
            else:
                missing_notes.append("Data quality engine metrics are unavailable.")

        elif report_type == ReportTypeEnum.CREDIT_RISK_REPORT:
            # Gather loan and borrower metrics
            _ = await LoanAnalyticsEngine(self.db).get_metrics(dataset_id, version_id)
            # Query risk categories directly
            from app.models.risk_assessment import RiskAssessment

            stmt = select(RiskAssessment).where(
                RiskAssessment.dataset_id == dataset_id, RiskAssessment.version_id == version_id
            )
            assessments = (await self.db.execute(stmt)).scalars().all()

            cats = {"LOW": 0, "MEDIUM": 0, "HIGH": 0}
            scores = []
            for a in assessments:
                cat_str = a.risk_category.value if hasattr(a.risk_category, "value") else str(a.risk_category)
                if cat_str in cats:
                    cats[cat_str] += 1
                scores.append(a.risk_score)

            kpis = {
                "Total Loans Analyzed": len(assessments),
                "Average Risk Score": round(sum(scores) / len(scores), 2) if scores else 0.0,
                "High Risk Count": cats["HIGH"],
                "Medium Risk Count": cats["MEDIUM"],
                "Low Risk Count": cats["LOW"],
            }
            tables["Risk Category Breakdown"] = [{"Risk Category": k, "Borrower Count": v} for k, v in cats.items()]
            assumptions.append(
                "Risk assessment categorization relies on threshold cutoffs: Low (< 30), Medium (30-59), High (>= 60)."
            )

        elif report_type == ReportTypeEnum.PORTFOLIO_REPORT:
            port = await PortfolioAnalyticsEngine(self.db).get_metrics(dataset_id, version_id)
            con = await ConcentrationEngine(self.db).get_metrics(dataset_id, version_id)

            kpis = {
                "Portfolio Value": port.get("portfolio_value", 0.0),
                "Outstanding Exposure": port.get("outstanding_exposure", 0.0),
                "Average Loan Size": port.get("average_loan_size", 0.0),
                "Average Risk Score": port.get("average_risk_score", 0.0),
                "Herfindahl-Hirschman Index": con.get("herfindahl_hirschman_index", 0.0),
            }
            # Concentration Segment table
            tables["Top 5 Exposure Segments"] = port.get("top_10_exposure_segments", [])[:5]

        elif report_type == ReportTypeEnum.DIAGNOSTIC_ANALYTICS_REPORT:
            diag = await DiagnosticEngine(self.db).get_metrics(dataset_id, version_id)
            kpis = {
                "Root-Cause Summary": diag.get("root_cause_summary")[:80] + "...",
                "Top Adverse Driver": (
                    diag.get("top_adverse_factors", [{}])[0].get("driver", "N/A")
                    if diag.get("top_adverse_factors")
                    else "N/A"
                ),
                "Identified Anomalies Count": len(diag.get("segment_anomalies", [])),
            }
            tables["Top Adverse Factors"] = diag.get("top_adverse_factors", [])
            tables["Segment Anomalies"] = diag.get("segment_anomalies", [])

        elif report_type == ReportTypeEnum.EXECUTIVE_SUMMARY_REPORT:
            dq = await DataQualityEngine(self.db).get_metrics(dataset_id, version_id)
            port = await PortfolioAnalyticsEngine(self.db).get_metrics(dataset_id, version_id)

            kpis = {
                "Dataset Health Score": dq.get("dataset_health_score", 0.0),
                "Completeness Score": dq.get("completeness_score", 0.0),
                "Portfolio Value": port.get("portfolio_value", 0.0),
                "High Risk Exposure": port.get("high_risk_exposure", 0.0),
                "Average Risk Score": port.get("average_risk_score", 0.0),
            }
            tables["Portfolio Overview KPI"] = [
                {"Metric Parameter": "Total Portfolio Size", "Value": port.get("portfolio_value")},
                {"Metric Parameter": "High Risk Exposure", "Value": port.get("high_risk_exposure")},
                {"Metric Parameter": "Dataset Quality Grade", "Value": dq.get("dataset_health_score")},
            ]

        return kpis, tables, charts, assumptions, missing_notes

    # PDF Renderer
    def _render_pdf(self, path: str, data: Dict[str, Any]) -> None:
        doc = fitz.open()
        page = doc.new_page()

        y = 50
        # Draw title
        page.insert_text((50, y), f"{data['title']}", fontsize=16, color=(0.1, 0.2, 0.5))
        y += 25
        page.insert_text((50, y), f"Generated: {data['generated_timestamp']}", fontsize=10, color=(0.3, 0.3, 0.3))
        y += 15
        page.insert_text((50, y), f"Generated By: {data['generated_by']}", fontsize=10, color=(0.3, 0.3, 0.3))
        y += 15
        page.insert_text(
            (50, y), f"Dataset: {data['dataset_name']} ({data['version']})", fontsize=10, color=(0.3, 0.3, 0.3)
        )
        y += 30

        # AI Summary block
        page.insert_text((50, y), "Executive Summary & AI Commentary:", fontsize=12, color=(0.1, 0.2, 0.5))
        y += 20
        # Simple multiline layout support for summary text
        summary_text = data["ai_commentary"]
        words = summary_text.split()
        lines = []
        curr_line = []
        for w in words:
            curr_line.append(w)
            if len(" ".join(curr_line)) > 90:
                lines.append(" ".join(curr_line))
                curr_line = []
        if curr_line:
            lines.append(" ".join(curr_line))
        for line in lines[:8]:  # restrict to avoid overlap
            page.insert_text((50, y), line, fontsize=9, color=(0.2, 0.2, 0.2))
            y += 15
        y += 15

        # KPIs Grid
        page.insert_text((50, y), "Key Performance Indicators (KPIs):", fontsize=12, color=(0.1, 0.2, 0.5))
        y += 20
        for k, v in data["kpis"].items():
            page.insert_text((50, y), f"• {k}: {v}", fontsize=10, color=(0.2, 0.2, 0.2))
            y += 15
        y += 20

        # Tabular details (List tables)
        for t_name, rows in data["tables"].items():
            if y > 550:  # Page boundary check, add page if overflowing
                page = doc.new_page()
                y = 50
                page.insert_text((50, y), "Analytical Data Tables (Cont.):", fontsize=12, color=(0.1, 0.2, 0.5))
                y += 25

            page.insert_text((50, y), f"Table: {t_name}", fontsize=11, color=(0.15, 0.15, 0.15))
            y += 15

            if rows:
                headers = list(rows[0].keys())
                header_str = " | ".join(headers)
                page.insert_text((50, y), header_str, fontsize=9, color=(0.4, 0.4, 0.4))
                y += 15
                for row in rows[:10]:  # Print up to 10 rows
                    vals = [str(row[h]) for h in headers]
                    row_str = " | ".join(vals)
                    # Line limit
                    if len(row_str) > 100:
                        row_str = row_str[:97] + "..."
                    page.insert_text((50, y), row_str, fontsize=9, color=(0.2, 0.2, 0.2))
                    y += 15
            else:
                page.insert_text((50, y), "No data rows available.", fontsize=9, color=(0.5, 0.5, 0.5))
                y += 15
            y += 15

        # Assumptions & Caveats
        if y > 600:
            page = doc.new_page()
            y = 50
        page.insert_text((50, y), "Methodology & Assumptions:", fontsize=11, color=(0.1, 0.2, 0.5))
        y += 15
        for a in data["assumptions"]:
            page.insert_text((50, y), f"- {a}", fontsize=9, color=(0.3, 0.3, 0.3))
            y += 15

        if data["missing_notes"]:
            y += 10
            page.insert_text((50, y), "Unavailable/Missing Metrics Caveats:", fontsize=11, color=(0.6, 0.2, 0.2))
            y += 15
            for note in data["missing_notes"]:
                page.insert_text((50, y), f"- {note}", fontsize=9, color=(0.5, 0.2, 0.2))
                y += 15

        doc.save(path)
        doc.close()

    # Excel Renderer
    def _render_excel(self, path: str, data: Dict[str, Any]) -> None:
        summary_rows = [
            ("Report Title", data["title"]),
            ("Generated Timestamp", data["generated_timestamp"]),
            ("Generated By", data["generated_by"]),
            ("Dataset Name", data["dataset_name"]),
            ("Dataset Version", data["version"]),
            ("Document ID", data["document_id"]),
            ("AI Commentary Summary", data["ai_commentary"]),
        ]
        summary_rows.append(("", ""))
        summary_rows.append(("--- Key KPIs ---", ""))
        for k, v in data["kpis"].items():
            summary_rows.append((k, v))

        summary_rows.append(("", ""))
        summary_rows.append(("--- Assumptions ---", ""))
        for a in data["assumptions"]:
            summary_rows.append((a, ""))

        if data["missing_notes"]:
            summary_rows.append(("", ""))
            summary_rows.append(("--- Missing/Unavailable Notes ---", ""))
            for note in data["missing_notes"]:
                summary_rows.append((note, ""))

        df_summary = pd.DataFrame(summary_rows, columns=["Parameter / Metric", "Value"])

        with pd.ExcelWriter(path, engine="openpyxl") as writer:
            df_summary.to_excel(writer, sheet_name="Summary", index=False)

            # Write each tabular dataset to another sheet
            for t_name, rows in data["tables"].items():
                # Clean sheet name to fit 31 char limit
                sheet_name = (
                    t_name[:31]
                    .replace("[", "")
                    .replace("]", "")
                    .replace("*", "")
                    .replace(":", "")
                    .replace("?", "")
                    .replace("/", "")
                    .replace("\\", "")
                )
                df_table = pd.DataFrame(rows)
                df_table.to_excel(writer, sheet_name=sheet_name or "Analytics Data", index=False)

    # CSV Renderer
    def _render_csv(self, path: str, data: Dict[str, Any]) -> None:
        lines = []
        lines.append("--- REPORT HEADER ---")
        lines.append(f"Title, {data['title']}")
        lines.append(f"Generated Timestamp, {data['generated_timestamp']}")
        lines.append(f"Generated By, {data['generated_by']}")
        lines.append(f"Dataset, {data['dataset_name']}")
        lines.append(f"Version, {data['version']}")
        lines.append(f"Document ID, {data['document_id']}")
        lines.append("")

        lines.append("--- EXECUTIVE SUMMARY / AI COMMENTARY ---")
        # Strip commas or wrap in quotes to avoid parsing errors
        commentary_safe = data["ai_commentary"].replace('"', '""')
        lines.append(f'"Commentary","{commentary_safe}"')
        lines.append("")

        lines.append("--- KEY KPIs ---")
        for k, v in data["kpis"].items():
            lines.append(f'"{k}","{v}"')
        lines.append("")

        for t_name, rows in data["tables"].items():
            lines.append(f"--- TABLE DATA: {t_name} ---")
            if rows:
                headers = list(rows[0].keys())
                lines.append(",".join(['"' + h + '"' for h in headers]))
                for row in rows:
                    vals = ['"' + str(row[h]).replace('"', '""') + '"' for h in headers]
                    lines.append(",".join(vals))
            else:
                lines.append("No data rows available.")
            lines.append("")

        lines.append("--- ASSUMPTIONS ---")
        for a in data["assumptions"]:
            lines.append(f'"{a}"')

        if data["missing_notes"]:
            lines.append("")
            lines.append("--- MISSING / UNAVAILABLE metric NOTES ---")
            for note in data["missing_notes"]:
                lines.append(f'"{note}"')

        with open(path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))
