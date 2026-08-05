from __future__ import annotations

from app.states.workflow import IntentType


INTENT_EXAMPLES: dict[IntentType, list[str]] = {
    IntentType.customer_lookup: [
        "so dien thoai cua khach hang John Smith",
        "email cua khach hang Pham Duc Hai",
        "nghe nghiep cua khach hang Le Minh Quan",
        "khach hang nay sinh nam bao nhieu",
        "dia chi cua anh ta la gi",
        "lay thong tin ho so khach hang",
    ],
    IntentType.masking_request: [
        "hay che thong tin khach hang",
        "mask so dien thoai va cccd",
        "an danh thong tin ca nhan",
        "ma hoa du lieu pii",
        "redact customer information",
    ],
    IntentType.banking_faq: [
        "cach mo tai khoan ngan hang",
        "bao lau toi nhan duoc the",
        "mo tai khoan online nhu the nao",
        "quy trinh mo the",
        "phi mo tai khoan la bao nhieu",
    ],
    IntentType.owner_question: [
        "ai tao ra ban",
        "nguoi tao ra du an nay la ai",
        "owner cua he thong la ai",
        "tac gia cua du an",
        "he thong nay duoc phat trien boi ai",
    ],
    IntentType.realtime_web: [
        "thoi tiet hom nay nhu the nao",
        "gia vang hom nay",
        "ty gia usd hien tai",
        "tin moi nhat ve ngan hang",
        "cap nhat thi truong hom nay",
    ],
    IntentType.document_intelligence: [
        "doc ho so nay giup toi",
        "tom tat tai lieu nay",
        "trich xuat thong tin trong hop dong",
        "kiem tra sao ke",
        "phan tich bao cao tai chinh",
    ],
    IntentType.research_report: [
        "lap bao cao nghien cuu",
        "viet research report ve ngan hang",
        "tao memo phan tich nganh",
        "soan to trinh",
    ],
    IntentType.credit_risk: [
        "danh gia rui ro tin dung",
        "tham dinh khoan vay",
        "kiem tra ho so vay von",
        "credit risk review",
    ],
    IntentType.smalltalk: [
        "xin chao",
        "ban la ai",
        "hello",
        "cam on",
        "ban co the lam gi",
    ],
}
