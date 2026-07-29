import re
from typing import Any

from app.tools.base import ToolResult


class CustomerDataMaskingTool:
    name = "customer_data.mask"
    description = "Mask CCCD/CMND, Vietnamese phone numbers, and account-like numbers."

    CCCD_PATTERN = r"\b\d{12}\b"
    PHONE_PATTERN = r"\b0[35789]\d{8}\b"
    ACCOUNT_PATTERN = r"\b\d{8,16}\b"

    def run(self, **kwargs: Any) -> ToolResult:
        text = str(kwargs.get("text", ""))
        masked_text = re.sub(self.CCCD_PATTERN, "[MASKED_CCCD]", text)
        masked_text = re.sub(self.PHONE_PATTERN, "[MASKED_PHONE]", masked_text)
        masked_text = re.sub(self.ACCOUNT_PATTERN, "[MASKED_ACCOUNT]", masked_text)

        return ToolResult(
            name=self.name,
            output=masked_text,
            metadata={
                "has_cccd": bool(re.search(self.CCCD_PATTERN, text)),
                "has_phone": bool(re.search(self.PHONE_PATTERN, text)),
                "has_account": bool(re.search(self.ACCOUNT_PATTERN, text)),
            },
        )


class CustomerProfileChecklistTool:
    name = "customer_profile.checklist"
    description = "Check whether common KYC/KYB profile fields appear in customer text."

    REQUIRED_FIELDS = {
        "identity": ["cccd", "cmnd", "passport", "ma so thue"],
        "contact": ["so dien thoai", "sdt", "email", "dia chi"],
        "employment_or_business": ["nghe nghiep", "cong ty", "doanh thu", "nganh nghe"],
        "banking_relationship": ["tai khoan", "khoan vay", "the tin dung", "han muc"],
    }

    def run(self, **kwargs: Any) -> ToolResult:
        text = str(kwargs.get("text", "")).lower()
        missing_groups = [
            group
            for group, keywords in self.REQUIRED_FIELDS.items()
            if not any(keyword in text for keyword in keywords)
        ]

        return ToolResult(
            name=self.name,
            output={
                "status": "incomplete" if missing_groups else "complete",
                "missing_groups": missing_groups,
            },
            metadata={"checked_groups": list(self.REQUIRED_FIELDS)},
        )

