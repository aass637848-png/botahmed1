import re
from datetime import datetime
from typing import Tuple, Optional
import pytz


def clean_target_identifier(raw_input: str) -> str:
    """Clean and standardize a chat identifier or username."""
    text = raw_input.strip()
    # If user pasted a telegram link like t.me/channel_name or https://t.me/channel_name
    match_link = re.search(r"(?:https?://)?(?:t\.me|telegram\.me)/([a-zA-Z0-9_]{4,32})/?", text)
    if match_link:
        return f"@{match_link.group(1)}"
    return text


def validate_target_identifier(raw_input: str) -> Tuple[bool, Optional[str], Optional[str]]:
    """
    Validate target input:
    Returns (is_valid, cleaned_value, error_message)
    Supports:
    - Numeric chat_id: e.g. -1001234567890 or 12345678
    - Username: e.g. @channel_username
    """
    cleaned = clean_target_identifier(raw_input)
    if not cleaned:
        return False, None, "المعرف فارغ، يرجى إدخال @username أو chat_id."

    # Check numeric chat_id
    if re.fullmatch(r"-?\d{5,20}", cleaned):
        return True, cleaned, None

    # Check @username
    if re.fullmatch(r"@[a-zA-Z0-9_]{4,32}", cleaned):
        return True, cleaned, None

    # If user forgot the '@' sign for alphanumeric usernames
    if re.fullmatch(r"[a-zA-Z][a-zA-Z0-9_]{3,31}", cleaned):
        return True, f"@{cleaned}", None

    return (
        False,
        None,
        "معرف غير صالح. يرجى إدخال اسم مستخدم يبدأ بـ @ (مثل @my_channel) أو معرف رقمي (مثل -100123456789).",
    )


def validate_positive_int(raw_input: str, min_val: int = 1, max_val: int = 1000) -> Tuple[bool, Optional[int], Optional[str]]:
    """Validate positive integer within range."""
    text = raw_input.strip()
    if not text.isdigit():
        return False, None, f"يرجى إدخال رقم صحيح بين {min_val} و {max_val}."
    val = int(text)
    if not (min_val <= val <= max_val):
        return False, None, f"يجب أن تكون القيمة بين {min_val} و {max_val}."
    return True, val, None


def validate_float_range(raw_input: str, min_val: float = 0.1, max_val: float = 60.0) -> Tuple[bool, Optional[float], Optional[str]]:
    """Validate float delay within range."""
    try:
        val = float(raw_input.strip())
        if not (min_val <= val <= max_val):
            return False, None, f"يجب أن تكون القيمة بين {min_val} و {max_val} ثانية."
        return True, val, None
    except ValueError:
        return False, None, "يرجى إدخال رقم عشري صالح (مثال: 1.5)."


def parse_schedule_datetime(raw_input: str, tz_name: str = "Africa/Cairo") -> Tuple[bool, Optional[datetime], Optional[str]]:
    """
    Parse scheduled datetime string:
    Formats supported:
    - YYYY-MM-DD HH:MM
    - DD/MM/YYYY HH:MM
    - HH:MM (for today or tomorrow if time passed)
    """
    text = raw_input.strip()
    try:
        tz = pytz.timezone(tz_name)
    except Exception:
        tz = pytz.UTC

    now = datetime.now(tz)

    # Check format HH:MM
    if re.fullmatch(r"\d{1,2}:\d{2}", text):
        try:
            parts = [int(p) for p in text.split(":")]
            target_dt = now.replace(hour=parts[0], minute=parts[1], second=0, microsecond=0)
            if target_dt <= now:
                # Add one day
                from datetime import timedelta
                target_dt += timedelta(days=1)
            return True, target_dt.astimezone(pytz.UTC).replace(tzinfo=None), None
        except Exception as e:
            return False, None, f"خطأ في قراءة الوقت: {str(e)}"

    # Check format YYYY-MM-DD HH:MM
    for fmt in ("%Y-%m-%d %H:%M", "%d/%m/%Y %H:%M", "%Y/%m/%d %H:%M"):
        try:
            dt = datetime.strptime(text, fmt)
            dt_localized = tz.localize(dt)
            if dt_localized <= now:
                return False, None, "الوقت المحدد في الماضي! يرجى اختيار وقت مستقبلي."
            return True, dt_localized.astimezone(pytz.UTC).replace(tzinfo=None), None
        except ValueError:
            continue

    return (
        False,
        None,
        "صيغة التاريخ والوقت غير صحيحة. استخدم إما: HH:MM (مثال: 18:30) أو YYYY-MM-DD HH:MM (مثال: 2026-10-15 14:00)",
    )
