import re
from typing import Any

from app.tools.base import ToolResult


class DocumentExtractionTool:
    name = "document.extract"
    description = "Extract simple document signals for banking document intelligence tasks."

    DOCUMENT_HINTS = {
        "bank_statement": ["sao ke", "statement", "giao dich"],
        "financial_statement": ["bao cao tai chinh", "doanh thu", "loi nhuan", "tai san"],
        "loan_application": ["ho so vay", "khoan vay", "tai san dam bao", "muc dich vay"],
        "contract": ["hop dong", "dieu khoan", "ben vay", "ben cho vay"],
    }

    def run(self, **kwargs: Any) -> ToolResult:
        text = str(kwargs.get("text", ""))
        normalized_text = text.lower()
        document_type = "unknown"

        for candidate, keywords in self.DOCUMENT_HINTS.items():
            if any(keyword in normalized_text for keyword in keywords):
                document_type = candidate
                break

        amounts = re.findall(r"\b\d{1,3}(?:[.,]\d{3})+(?:\s?(?:vnd|dong|ty|trieu))?\b", normalized_text)

        return ToolResult(
            name=self.name,
            output={
                "document_type": document_type,
                "amounts": amounts,
                "summary_preview": text[:500],
            },
            metadata={"amount_count": len(amounts)},
        )


class ResearchReportTemplateTool:
    name = "research_report.template"
    description = "Create a banking research report outline for staff drafting."

    def run(self, **kwargs: Any) -> ToolResult:
        topic = str(kwargs.get("topic", "")).strip() or "Chu de nghien cuu"
        sections = [
            "Executive summary",
            "Market and sector context",
            "Company or customer profile",
            "Financial highlights",
            "Key risks",
            "Recommendation and next steps",
            "Sources and assumptions",
        ]

        return ToolResult(
            name=self.name,
            output={"topic": topic[:200], "sections": sections},
            metadata={"section_count": len(sections)},
        )


class BankingProcessChecklistTool:
    name = "banking_process.checklist"
    description = "Return standard operational checklist items for banking staff workflows."

    PROCESS_CHECKLISTS = {
        "card_opening": [
            "Confirm customer identity and eligibility.",
            "Collect required application documents.",
            "Check product terms, fees, and credit limit rules.",
            "Submit application for approval.",
            "Record audit trail and handoff status.",
        ],
        "account_opening": [
            "Confirm KYC/KYB information.",
            "Validate required identification documents.",
            "Screen against internal restrictions.",
            "Create account request and approval record.",
            "Notify customer-facing staff of next steps.",
        ],
        "loan_review": [
            "Collect loan application and supporting documents.",
            "Review repayment source and collateral.",
            "Identify missing evidence and risk factors.",
            "Prepare preliminary credit memo.",
            "Submit to approval workflow.",
        ],
    }

    def run(self, **kwargs: Any) -> ToolResult:
        text = str(kwargs.get("text", "")).lower()
        process_type = "loan_review"

        if "mo the" in text or "the tin dung" in text or "card" in text:
            process_type = "card_opening"
        elif "mo tai khoan" in text or "account" in text:
            process_type = "account_opening"

        return ToolResult(
            name=self.name,
            output={
                "process_type": process_type,
                "checklist": self.PROCESS_CHECKLISTS[process_type],
            },
            metadata={"item_count": len(self.PROCESS_CHECKLISTS[process_type])},
        )

