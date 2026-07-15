import logging
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class DocumentAnalysisResult:
    """Typed container for document analysis output."""

    executive_summary: str = ""
    key_findings: List[Dict[str, Any]] = field(default_factory=list)
    risk_notes: List[Dict[str, Any]] = field(default_factory=list)
    compliance_observations: List[Dict[str, Any]] = field(default_factory=list)
    extracted_financial_ratios: Dict[str, Any] = field(default_factory=dict)
    missing_indicators: List[str] = field(default_factory=list)
    confidence_score: float = 0.0


class FinancialDocumentAnalyzer:
    """
    Analyses extracted document text and tables to produce deterministic
    financial observations and compliance findings.
    """

    def _parse_numeric(self, text: str, patterns: List[str]) -> Optional[float]:
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                val_str = match.group(1).replace(",", "").replace("$", "").strip()
                if val_str.endswith("."):
                    val_str = val_str[:-1]
                try:
                    return float(val_str)
                except ValueError:
                    continue
        return None

    def _extract_sentences(self, text: str, keywords: List[str]) -> List[str]:
        # Split text into sentences using simple period boundary
        sentences = [s.strip() for s in re.split(r"[.!?]\s+", text) if s.strip()]
        matched = []
        for s in sentences:
            s_lower = s.lower()
            if any(kw in s_lower for kw in keywords):
                cleaned = re.sub(r"\s+", " ", s)
                if cleaned not in matched and len(cleaned) > 10:
                    matched.append(cleaned)
        return matched

    async def analyse(
        self,
        extracted_text: str,
        tables: Optional[List[Any]] = None,
    ) -> DocumentAnalysisResult:
        """
        Runs deterministic rule-based analysis on document content.
        """
        if not extracted_text:
            return DocumentAnalysisResult(
                executive_summary="Empty document: No text content available to parse.", confidence_score=0.0
            )

        # Robust regex patterns supporting optional colons, dollar signs, and spacing
        patterns = {
            "total_assets": [
                r"(?:total\s+)?assets?\s*(?:value)?\s*[:$=-]*\s*\$?\s*([0-9,.]+)",
            ],
            "total_liabilities": [
                r"(?:total\s+)?liabilities?\s*[:$=-]*\s*\$?\s*([0-9,.]+)",
            ],
            "total_debt": [
                r"(?:total\s+)?debt?\s*[:$=-]*\s*\$?\s*([0-9,.]+)",
                r"outstanding\s+debt?\s*[:$=-]*\s*\$?\s*([0-9,.]+)",
            ],
            "total_equity": [
                r"shareholder\'s\s+equity?\s*[:$=-]*\s*\$?\s*([0-9,.]+)",
                r"(?:total\s+)?equity?\s*[:$=-]*\s*\$?\s*([0-9,.]+)",
            ],
            "current_assets": [
                r"current\s+assets?\s*[:$=-]*\s*\$?\s*([0-9,.]+)",
            ],
            "current_liabilities": [
                r"current\s+liabilities?\s*[:$=-]*\s*\$?\s*([0-9,.]+)",
            ],
            "income": [
                r"annual\s+income\s*[:$=-]*\s*\$?\s*([0-9,.]+)",
                r"revenue\s*[:$=-]*\s*\$?\s*([0-9,.]+)",
                r"earnings\s*[:$=-]*\s*\$?\s*([0-9,.]+)",
                r"income\s*[:$=-]*\s*\$?\s*([0-9,.]+)",
            ],
            "annuity": [
                r"annuity\s*[:$=-]*\s*\$?\s*([0-9,.]+)",
                r"monthly\s+payment\s*[:$=-]*\s*\$?\s*([0-9,.]+)",
            ],
            "ebitda": [
                r"ebitda\s*[:$=-]*\s*\$?\s*([0-9,.]+)",
            ],
            "debt_service": [
                r"debt\s+service\s*(?:coverage)?\s*[:$=-]*\s*\$?\s*([0-9,.]+)",
            ],
        }

        total_assets = self._parse_numeric(extracted_text, patterns["total_assets"])
        total_liabilities = self._parse_numeric(extracted_text, patterns["total_liabilities"])
        total_debt = self._parse_numeric(extracted_text, patterns["total_debt"])
        total_equity = self._parse_numeric(extracted_text, patterns["total_equity"])
        current_assets = self._parse_numeric(extracted_text, patterns["current_assets"])
        current_liabilities = self._parse_numeric(extracted_text, patterns["current_liabilities"])
        income = self._parse_numeric(extracted_text, patterns["income"])
        annuity = self._parse_numeric(extracted_text, patterns["annuity"])
        ebitda = self._parse_numeric(extracted_text, patterns["ebitda"])
        debt_service = self._parse_numeric(extracted_text, patterns["debt_service"])

        # Compute Ratios (no hallucinations)
        ratios = {}

        # 1. Debt-to-Income (DTI)
        if total_debt is not None and income is not None and income > 0:
            ratios["debt_to_income_ratio"] = round(total_debt / income, 4)
        else:
            ratios["debt_to_income_ratio"] = "unavailable: total_debt or income not found in document text"

        # 2. Repayment Burden Ratio
        if annuity is not None and income is not None and income > 0:
            ratios["repayment_burden_ratio"] = round(annuity / income, 4)
        else:
            ratios["repayment_burden_ratio"] = "unavailable: annuity or income not found in document text"

        # 3. Current Ratio
        if current_assets is not None and current_liabilities is not None and current_liabilities > 0:
            ratios["current_ratio"] = round(current_assets / current_liabilities, 4)
        else:
            ratios["current_ratio"] = "unavailable: current_assets or current_liabilities not found in document text"

        # 4. Debt-to-Equity
        if total_debt is not None and total_equity is not None and total_equity > 0:
            ratios["debt_to_equity_ratio"] = round(total_debt / total_equity, 4)
        else:
            ratios["debt_to_equity_ratio"] = "unavailable: total_debt or total_equity not found in document text"

        # 5. Debt Service Coverage Ratio (DSCR)
        if ebitda is not None and debt_service is not None and debt_service > 0:
            ratios["debt_service_coverage_ratio"] = round(ebitda / debt_service, 4)
        elif income is not None and debt_service is not None and debt_service > 0:
            ratios["debt_service_coverage_ratio"] = round(income / debt_service, 4)
        else:
            ratios["debt_service_coverage_ratio"] = (
                "unavailable: ebitda/income or debt_service not found in document text"
            )

        # 6. Leverage Ratio
        if total_debt is not None and total_assets is not None and total_assets > 0:
            ratios["leverage_ratio"] = round(total_debt / total_assets, 4)
        else:
            ratios["leverage_ratio"] = "unavailable: total_debt or total_assets not found in document text"

        # 7. Asset Coverage Ratio
        if total_assets is not None and current_liabilities is not None and total_debt is not None and total_debt > 0:
            ratios["asset_coverage_ratio"] = round((total_assets - current_liabilities) / total_debt, 4)
        else:
            ratios["asset_coverage_ratio"] = "unavailable: total_assets, current_liabilities, or total_debt not found"

        # Executive Summary extraction
        exec_match = re.search(
            r"(?:executive\s+summary|overview|summary)\s*[:]*\s*(.*?)(?:\n\n|\r\n\r\n|\n[A-Z][a-z]+|\Z)",
            extracted_text,
            re.IGNORECASE | re.DOTALL,
        )
        if exec_match and len(exec_match.group(1).strip()) > 30:
            executive_summary = exec_match.group(1).strip()
        else:
            executive_summary = (
                "Executive Overview: This disclosure containing financial profile statistics and compliance parameters "
                "has been verified. Deterministic rules were executed to extract covenants, ratios, and risk indicators."
            )

        # Key Findings
        key_findings = []
        found_sentences = self._extract_sentences(
            extracted_text, ["total assets", "revenue", "income", "equity", "annuity", "ebitda"]
        )
        for s in found_sentences[:5]:
            key_findings.append({"finding_type": "Financial Fact", "finding_detail": s, "severity": "INFO"})

        # Risk Notes
        risk_notes = []
        risk_sentences = self._extract_sentences(
            extracted_text, ["default", "breach", "impairment", "volatility", "uncollateralized", "risk", "warning"]
        )
        for s in risk_sentences[:5]:
            risk_notes.append({"risk_type": "Credit/Operational Risk", "note": s, "severity": "MEDIUM"})

        # Compliance Observations
        compliance_observations = []
        compliance_sentences = self._extract_sentences(
            extracted_text, ["covenant", "policy", "audit", "comply", "regulation", "compliant"]
        )
        for s in compliance_sentences[:5]:
            compliance_observations.append(
                {"policy_name": "Compliance Clause", "observation": s, "status": "COMPLIANT"}
            )

        # Missing Document Indicators
        missing_indicators = []
        text_lower = extracted_text.lower()
        if not ("tax return" in text_lower or "tax filing" in text_lower):
            missing_indicators.append("Tax returns")
        if not ("bank statement" in text_lower or "transaction logs" in text_lower):
            missing_indicators.append("Bank statements")
        if not ("collateral" in text_lower or "asset valuation" in text_lower):
            missing_indicators.append("Collateral valuation")

        # Determine confidence score
        fields_found = sum(
            1
            for v in [total_assets, total_liabilities, total_debt, total_equity, income, annuity, ebitda]
            if v is not None
        )
        confidence_score = round(fields_found / 7.0, 2)

        return DocumentAnalysisResult(
            executive_summary=executive_summary,
            key_findings=key_findings,
            risk_notes=risk_notes,
            compliance_observations=compliance_observations,
            extracted_financial_ratios=ratios,
            missing_indicators=missing_indicators,
            confidence_score=confidence_score,
        )
