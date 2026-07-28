import re

class PIIDetector:
    # Regex cơ bản cho CCCD (12 số) và Số điện thoại Việt Nam
    CCCD_PATTERN = r"\b\d{12}\b"
    PHONE_PATTERN = r"(\b0[3|5|7|8|9]\d{8}\b)"

    @classmethod
    def mask_pii(cls, text: str) -> str:
        text = re.sub(cls.CCCD_PATTERN, "[MASKED_CCCD]", text)
        text = re.sub(cls.PHONE_PATTERN, "[MASKED_PHONE]", text)
        return text

    @classmethod
    def has_pii(cls, text: str) -> bool:
        return bool(re.search(cls.CCCD_PATTERN, text) or re.search(cls.PHONE_PATTERN, text))