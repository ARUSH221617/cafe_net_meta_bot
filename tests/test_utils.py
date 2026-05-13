from app.database.repositories.users import normalize_phone_number
from app.utils.money import format_irr


def test_format_irr() -> None:
    assert format_irr(1234567) == "1,234,567 ریال"


def test_normalize_phone_number() -> None:
    assert normalize_phone_number(" +98 912 345 6789 ") == "+989123456789"
