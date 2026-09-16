import re


def indian_mobile_last10(value):
    digits = re.sub(r"\D+", "", value or "")
    if len(digits) >= 10:
        return digits[-10:]
    return digits


def normalize_indian_mobile(value):
    digits = re.sub(r"\D+", "", value or "")
    if digits.startswith("0") and len(digits) == 11:
        digits = digits[1:]
    elif digits.startswith("91") and len(digits) == 12:
        digits = digits[2:]
    elif digits.startswith("091") and len(digits) == 13:
        digits = digits[3:]
    elif len(digits) > 10:
        digits = digits[-10:]

    if not re.fullmatch(r"[6-9]\d{9}", digits):
        raise ValueError("Enter a valid 10-digit Indian mobile number.")
    return f"+91{digits}"


def indian_whatsapp_number(value):
    return normalize_indian_mobile(value).lstrip("+")
