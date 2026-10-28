"""
Indian Financial Institutions & Bank Directory Service for SecurePay.

Provides a maintained directory of Indian public-sector banks, private-sector banks,
small finance banks, payments banks, and regional rural banks.
Distinguishes between institutions listed in the directory and those verified as
supported for instant account linking by the active payment provider sandbox.
"""

from dataclasses import dataclass
from typing import Literal

BankCategory = Literal[
    "public_sector",
    "private_sector",
    "small_finance",
    "payments_bank",
    "regional_rural",
]


@dataclass(frozen=True)
class BankInstitution:
    code: str
    name: str
    short_name: str
    category: BankCategory
    ifsc_prefix: str
    popular: bool
    active: bool
    supported_for_linking: bool
    linking_method: str  # "instant_sandbox", "penny_drop", "netbanking", "manual_statement"
    supported_features: tuple[str, ...]
    tagline: str


# Comprehensive directory of verified Indian banks
INDIAN_BANKS: list[BankInstitution] = [
    # --- Public Sector Banks ---
    BankInstitution(
        code="SBIN",
        name="State Bank of India",
        short_name="SBI",
        category="public_sector",
        ifsc_prefix="SBIN",
        popular=True,
        active=True,
        supported_for_linking=True,
        linking_method="instant_sandbox",
        supported_features=("upi", "imps", "neft", "rtgs", "e_mandate"),
        tagline="India's largest public sector bank",
    ),
    BankInstitution(
        code="PUNB",
        name="Punjab National Bank",
        short_name="PNB",
        category="public_sector",
        ifsc_prefix="PUNB",
        popular=True,
        active=True,
        supported_for_linking=True,
        linking_method="instant_sandbox",
        supported_features=("upi", "imps", "neft", "rtgs"),
        tagline="The name you can bank upon",
    ),
    BankInstitution(
        code="BARB",
        name="Bank of Baroda",
        short_name="BOB",
        category="public_sector",
        ifsc_prefix="BARB",
        popular=True,
        active=True,
        supported_for_linking=True,
        linking_method="instant_sandbox",
        supported_features=("upi", "imps", "neft", "rtgs"),
        tagline="India's international bank",
    ),
    BankInstitution(
        code="CNRB",
        name="Canara Bank",
        short_name="Canara",
        category="public_sector",
        ifsc_prefix="CNRB",
        popular=False,
        active=True,
        supported_for_linking=True,
        linking_method="instant_sandbox",
        supported_features=("upi", "imps", "neft", "rtgs"),
        tagline="Together we can",
    ),
    BankInstitution(
        code="UBIN",
        name="Union Bank of India",
        short_name="Union Bank",
        category="public_sector",
        ifsc_prefix="UBIN",
        popular=False,
        active=True,
        supported_for_linking=True,
        linking_method="instant_sandbox",
        supported_features=("upi", "imps", "neft", "rtgs"),
        tagline="Good people to bank with",
    ),
    BankInstitution(
        code="BKID",
        name="Bank of India",
        short_name="BOI",
        category="public_sector",
        ifsc_prefix="BKID",
        popular=False,
        active=True,
        supported_for_linking=True,
        linking_method="instant_sandbox",
        supported_features=("upi", "imps", "neft", "rtgs"),
        tagline="Relationship beyond banking",
    ),
    BankInstitution(
        code="IDIB",
        name="Indian Bank",
        short_name="Indian Bank",
        category="public_sector",
        ifsc_prefix="IDIB",
        popular=False,
        active=True,
        supported_for_linking=True,
        linking_method="instant_sandbox",
        supported_features=("upi", "imps", "neft", "rtgs"),
        tagline="Taking banking technology to the common man",
    ),
    BankInstitution(
        code="CBIN",
        name="Central Bank of India",
        short_name="Central Bank",
        category="public_sector",
        ifsc_prefix="CBIN",
        popular=False,
        active=True,
        supported_for_linking=True,
        linking_method="instant_sandbox",
        supported_features=("upi", "imps", "neft"),
        tagline="Central to you since 1911",
    ),
    BankInstitution(
        code="IOBA",
        name="Indian Overseas Bank",
        short_name="IOB",
        category="public_sector",
        ifsc_prefix="IOBA",
        popular=False,
        active=True,
        supported_for_linking=False,
        linking_method="penny_drop",
        supported_features=("upi", "imps", "neft"),
        tagline="Good people to grow with",
    ),
    BankInstitution(
        code="UCBA",
        name="UCO Bank",
        short_name="UCO",
        category="public_sector",
        ifsc_prefix="UCBA",
        popular=False,
        active=True,
        supported_for_linking=False,
        linking_method="penny_drop",
        supported_features=("upi", "imps", "neft"),
        tagline="Honours your trust",
    ),
    BankInstitution(
        code="MAHB",
        name="Bank of Maharashtra",
        short_name="BOM",
        category="public_sector",
        ifsc_prefix="MAHB",
        popular=False,
        active=True,
        supported_for_linking=False,
        linking_method="penny_drop",
        supported_features=("upi", "imps", "neft"),
        tagline="One family, one bank",
    ),
    BankInstitution(
        code="PSIB",
        name="Punjab & Sind Bank",
        short_name="PSB",
        category="public_sector",
        ifsc_prefix="PSIB",
        popular=False,
        active=True,
        supported_for_linking=False,
        linking_method="penny_drop",
        supported_features=("upi", "imps"),
        tagline="Where service is a way of life",
    ),

    # --- Private Sector Banks ---
    BankInstitution(
        code="HDFC",
        name="HDFC Bank",
        short_name="HDFC",
        category="private_sector",
        ifsc_prefix="HDFC",
        popular=True,
        active=True,
        supported_for_linking=True,
        linking_method="instant_sandbox",
        supported_features=("upi", "imps", "neft", "rtgs", "e_mandate"),
        tagline="We understand your world",
    ),
    BankInstitution(
        code="ICIC",
        name="ICICI Bank",
        short_name="ICICI",
        category="private_sector",
        ifsc_prefix="ICIC",
        popular=True,
        active=True,
        supported_for_linking=True,
        linking_method="instant_sandbox",
        supported_features=("upi", "imps", "neft", "rtgs", "e_mandate"),
        tagline="Hum Hai Na, Khayal Aapka",
    ),
    BankInstitution(
        code="UTIB",
        name="Axis Bank",
        short_name="Axis",
        category="private_sector",
        ifsc_prefix="UTIB",
        popular=True,
        active=True,
        supported_for_linking=True,
        linking_method="instant_sandbox",
        supported_features=("upi", "imps", "neft", "rtgs", "e_mandate"),
        tagline="Badhti Ka Naam Zindagi",
    ),
    BankInstitution(
        code="KKBK",
        name="Kotak Mahindra Bank",
        short_name="Kotak",
        category="private_sector",
        ifsc_prefix="KKBK",
        popular=True,
        active=True,
        supported_for_linking=True,
        linking_method="instant_sandbox",
        supported_features=("upi", "imps", "neft", "rtgs"),
        tagline="Let's make money simple",
    ),
    BankInstitution(
        code="INDB",
        name="IndusInd Bank",
        short_name="IndusInd",
        category="private_sector",
        ifsc_prefix="INDB",
        popular=False,
        active=True,
        supported_for_linking=True,
        linking_method="instant_sandbox",
        supported_features=("upi", "imps", "neft", "rtgs"),
        tagline="We make you feel richer",
    ),
    BankInstitution(
        code="FDRL",
        name="Federal Bank",
        short_name="Federal",
        category="private_sector",
        ifsc_prefix="FDRL",
        popular=False,
        active=True,
        supported_for_linking=True,
        linking_method="instant_sandbox",
        supported_features=("upi", "imps", "neft"),
        tagline="Your perfect banking partner",
    ),
    BankInstitution(
        code="YESB",
        name="Yes Bank",
        short_name="Yes Bank",
        category="private_sector",
        ifsc_prefix="YESB",
        popular=False,
        active=True,
        supported_for_linking=True,
        linking_method="instant_sandbox",
        supported_features=("upi", "imps", "neft"),
        tagline="Experience our expertise",
    ),
    BankInstitution(
        code="IDFB",
        name="IDFC FIRST Bank",
        short_name="IDFC FIRST",
        category="private_sector",
        ifsc_prefix="IDFB",
        popular=False,
        active=True,
        supported_for_linking=True,
        linking_method="instant_sandbox",
        supported_features=("upi", "imps", "neft", "rtgs"),
        tagline="Always you first",
    ),
    BankInstitution(
        code="SIBL",
        name="South Indian Bank",
        short_name="South Indian",
        category="private_sector",
        ifsc_prefix="SIBL",
        popular=False,
        active=True,
        supported_for_linking=False,
        linking_method="penny_drop",
        supported_features=("upi", "imps", "neft"),
        tagline="Experience next generation banking",
    ),
    BankInstitution(
        code="RATN",
        name="RBL Bank",
        short_name="RBL",
        category="private_sector",
        ifsc_prefix="RATN",
        popular=False,
        active=True,
        supported_for_linking=False,
        linking_method="penny_drop",
        supported_features=("upi", "imps", "neft"),
        tagline="Apno Ka Bank",
    ),
    BankInstitution(
        code="BDBL",
        name="Bandhan Bank",
        short_name="Bandhan",
        category="private_sector",
        ifsc_prefix="BDBL",
        popular=False,
        active=True,
        supported_for_linking=False,
        linking_method="penny_drop",
        supported_features=("upi", "imps", "neft"),
        tagline="Aapka Bhala, Sabki Bhalai",
    ),
    BankInstitution(
        code="CIUB",
        name="City Union Bank",
        short_name="CUB",
        category="private_sector",
        ifsc_prefix="CIUB",
        popular=False,
        active=True,
        supported_for_linking=False,
        linking_method="penny_drop",
        supported_features=("upi", "imps"),
        tagline="Trust and excellence since 1904",
    ),

    # --- Small Finance Banks ---
    BankInstitution(
        code="AUBL",
        name="AU Small Finance Bank",
        short_name="AU Bank",
        category="small_finance",
        ifsc_prefix="AUBL",
        popular=False,
        active=True,
        supported_for_linking=True,
        linking_method="instant_sandbox",
        supported_features=("upi", "imps", "neft"),
        tagline="Badlaav Humse Hai",
    ),
    BankInstitution(
        code="ESFB",
        name="Equitas Small Finance Bank",
        short_name="Equitas",
        category="small_finance",
        ifsc_prefix="ESFB",
        popular=False,
        active=True,
        supported_for_linking=True,
        linking_method="instant_sandbox",
        supported_features=("upi", "imps", "neft"),
        tagline="It's fun banking",
    ),
    BankInstitution(
        code="UJVN",
        name="Ujjivan Small Finance Bank",
        short_name="Ujjivan",
        category="small_finance",
        ifsc_prefix="UJVN",
        popular=False,
        active=True,
        supported_for_linking=True,
        linking_method="instant_sandbox",
        supported_features=("upi", "imps", "neft"),
        tagline="Build a better life",
    ),
    BankInstitution(
        code="JSFB",
        name="Jana Small Finance Bank",
        short_name="Jana Bank",
        category="small_finance",
        ifsc_prefix="JSFB",
        popular=False,
        active=True,
        supported_for_linking=False,
        linking_method="penny_drop",
        supported_features=("upi", "imps"),
        tagline="Likho Apni Kahaani",
    ),

    # --- Payments Banks ---
    BankInstitution(
        code="AIRP",
        name="Airtel Payments Bank",
        short_name="Airtel Money",
        category="payments_bank",
        ifsc_prefix="AIRP",
        popular=True,
        active=True,
        supported_for_linking=True,
        linking_method="instant_sandbox",
        supported_features=("upi", "imps"),
        tagline="Banking is now on your fingertips",
    ),
    BankInstitution(
        code="IPOS",
        name="India Post Payments Bank",
        short_name="IPPB",
        category="payments_bank",
        ifsc_prefix="IPOS",
        popular=False,
        active=True,
        supported_for_linking=True,
        linking_method="instant_sandbox",
        supported_features=("upi", "imps"),
        tagline="Aapka Bank, Aapke Dwaar",
    ),
    BankInstitution(
        code="FINO",
        name="Fino Payments Bank",
        short_name="Fino",
        category="payments_bank",
        ifsc_prefix="FINO",
        popular=False,
        active=True,
        supported_for_linking=False,
        linking_method="penny_drop",
        supported_features=("upi", "imps"),
        tagline="Qadar Aapki Mehnat Ki",
    ),
    BankInstitution(
        code="JIOP",
        name="Jio Payments Bank",
        short_name="Jio Bank",
        category="payments_bank",
        ifsc_prefix="JIOP",
        popular=False,
        active=True,
        supported_for_linking=False,
        linking_method="penny_drop",
        supported_features=("upi", "imps"),
        tagline="Digital banking for every Indian",
    ),

    # --- Regional Rural Banks (RRBs) ---
    BankInstitution(
        code="KLGB",
        name="Kerala Gramin Bank",
        short_name="Kerala Gramin",
        category="regional_rural",
        ifsc_prefix="KLGB",
        popular=False,
        active=True,
        supported_for_linking=False,
        linking_method="penny_drop",
        supported_features=("upi", "imps"),
        tagline="Empowering rural Kerala",
    ),
    BankInstitution(
        code="BUPB",
        name="Baroda UP Bank",
        short_name="Baroda UP",
        category="regional_rural",
        ifsc_prefix="BUPB",
        popular=False,
        active=True,
        supported_for_linking=False,
        linking_method="penny_drop",
        supported_features=("upi", "imps"),
        tagline="Rural banking excellence",
    ),
    BankInstitution(
        code="ARYA",
        name="Aryavart Bank",
        short_name="Aryavart",
        category="regional_rural",
        ifsc_prefix="ARYA",
        popular=False,
        active=True,
        supported_for_linking=False,
        linking_method="penny_drop",
        supported_features=("upi", "imps"),
        tagline="Serving Uttar Pradesh",
    ),
    BankInstitution(
        code="PKGB",
        name="Karnataka Gramin Bank",
        short_name="Karnataka Gramin",
        category="regional_rural",
        ifsc_prefix="PKGB",
        popular=False,
        active=True,
        supported_for_linking=False,
        linking_method="penny_drop",
        supported_features=("upi", "imps"),
        tagline="Leading RRB in Karnataka",
    ),
]


def get_bank_directory(
    search: str | None = None,
    category: str | None = None,
    popular_only: bool = False,
    supported_only: bool = False,
) -> list[dict]:
    """
    Search and filter banks from the directory.
    """
    banks = INDIAN_BANKS

    if popular_only:
        banks = [b for b in banks if b.popular]

    if supported_only:
        banks = [b for b in banks if b.supported_for_linking]

    if category and category != "all":
        banks = [b for b in banks if b.category == category]

    if search and search.strip():
        term = search.strip().lower()
        banks = [
            b
            for b in banks
            if term in b.name.lower()
            or term in b.short_name.lower()
            or term in b.code.lower()
            or term in b.ifsc_prefix.lower()
        ]

    return [
        {
            "code": b.code,
            "name": b.name,
            "short_name": b.short_name,
            "category": b.category,
            "ifsc_prefix": b.ifsc_prefix,
            "popular": b.popular,
            "active": b.active,
            "supported_for_linking": b.supported_for_linking,
            "linking_method": b.linking_method,
            "supported_features": list(b.supported_features),
            "tagline": b.tagline,
        }
        for b in banks
    ]


def find_bank_by_ifsc(ifsc_code: str) -> dict | None:
    """
    Look up bank details from an IFSC prefix (first 4 characters).
    """
    if not ifsc_code or len(ifsc_code) < 4:
        return None
    prefix = ifsc_code[:4].upper()
    for b in INDIAN_BANKS:
        if b.ifsc_prefix == prefix:
            return {
                "code": b.code,
                "name": b.name,
                "short_name": b.short_name,
                "category": b.category,
                "ifsc_prefix": b.ifsc_prefix,
                "supported_for_linking": b.supported_for_linking,
                "linking_method": b.linking_method,
            }
    return None
