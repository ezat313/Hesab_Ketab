"""Shamsi (Solar Hijri) dates and Persian number formatting."""
from datetime import datetime, timedelta, timezone

import jdatetime

MONTH_NAMES = [
    "حمل", "ثور", "جوزا", "سرطان", "اسد", "سنبله",
    "میزان", "عقرب", "قوس", "جدی", "دلو", "حوت",
]

# Afghanistan is UTC+4:30 all year (no daylight saving).
KABUL_TZ = timezone(timedelta(hours=4, minutes=30))

_FA_DIGITS = "۰۱۲۳۴۵۶۷۸۹"
_AR_DIGITS = "٠١٢٣٤٥٦٧٨٩"
_TO_ASCII = str.maketrans(_FA_DIGITS + _AR_DIGITS, "0123456789" * 2)
_TO_FA = str.maketrans("0123456789", _FA_DIGITS)


def to_ascii_digits(text):
    return (text or "").translate(_TO_ASCII)


def fa_digits(value):
    return str(value).translate(_TO_FA)


def fa_number(value):
    return fa_digits(f"{value or 0:,}".replace(",", "٬"))


def parse_amount(text):
    """Parse a whole Afghani amount typed with Persian or English digits."""
    cleaned = to_ascii_digits(text).strip()
    for sep in (",", "٬", "،", " "):
        cleaned = cleaned.replace(sep, "")
    return int(cleaned) if cleaned.isdigit() else None


def normalize_invite_code(text):
    return to_ascii_digits(text).upper().replace("-", "").replace(" ", "").strip()


def today_shamsi():
    return jdatetime.date.fromgregorian(date=datetime.now(KABUL_TZ).date())


def to_shamsi(gregorian_date):
    return jdatetime.date.fromgregorian(date=gregorian_date)


def format_shamsi(gregorian_date):
    j = to_shamsi(gregorian_date)
    return fa_digits(f"{j.day} {MONTH_NAMES[j.month - 1]} {j.year}")


def month_title(year, month):
    return f"{MONTH_NAMES[month - 1]} {fa_digits(year)}"


def shift_month(year, month, delta):
    index = year * 12 + (month - 1) + delta
    return index // 12, index % 12 + 1


def month_bounds(year, month):
    """Gregorian [start, end) range covering one Shamsi month."""
    start = jdatetime.date(year, month, 1).togregorian()
    next_year, next_month = shift_month(year, month, 1)
    end = jdatetime.date(next_year, next_month, 1).togregorian()
    return start, end
