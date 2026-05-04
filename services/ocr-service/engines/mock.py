from time import perf_counter

from engines.common import build_ocr_result


MOCK_TEXT = """DATA GATE MOCK OCR
ЗЭЭЛИЙН ГЭРЭЭ / Loan Agreement
Borrower / Зээлдэгч: Бат-Эрдэнэ Болд / Bat-Erdene Bold
Lender / Зээлдүүлэгч: Khan Bank
Company: Altan Trade LLC
Loan amount / Зээлийн дүн: 50,000,000 MNT
Interest rate / Хүү: 2.2% monthly
Term / Хугацаа: 24 months
Start date: 2026-01-15
Maturity date: 2028-01-15
Collateral / Барьцаа: Toyota Land Cruiser 2021, apartment certificate UB-2024-1188
Repayment schedule: monthly equal payments
Signatures detected: yes

ДАНСНЫ ХУУЛГА / Bank Statement
Account holder: Bat-Erdene Bold
Bank name: Khan Bank
Account number: **** **** 1290
Statement period: 2026-01-01 to 2026-01-31
Opening balance: 2,150,000 MNT
Closing balance: 4,375,000 MNT
Total income: 6,800,000 MNT
Total expense: 4,575,000 MNT
Transaction count: 38

ЦАЛИНГИЙН ТОДОРХОЙЛОЛТ / Salary Statement
Employee: Bat-Erdene Bold
Employer: Altan Trade LLC
Monthly salary: 3,500,000 MNT
Statement month: 2026-01
Social insurance paid: 420,000 MNT
Tax paid: 350,000 MNT

НЭХЭМЖЛЭХ / Invoice
Merchant: Altan Trade LLC
Buyer: Bat-Erdene Bold
Invoice number: INV-2026-0042
Invoice date: 2026-01-20
Invoice total: 1,250,000 MNT
VAT / НӨАТ: 125,000 MNT"""


def extract_with_mock(filename: str, content: bytes) -> dict:
    started = perf_counter()
    return build_ocr_result(
        engine="mock",
        engine_version="mock-0.1.0",
        raw_text=f"Source: {filename}\n\n{MOCK_TEXT}",
        confidence=0.91,
        started_at=started,
    )
