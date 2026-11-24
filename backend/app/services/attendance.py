from app.core.constants import CRITICAL_BELOW_PERCENT, MIN_ATTENDANCE_PERCENT, SAFE_AT_PERCENT


def percentage(present: int, total: int) -> float:
    if total <= 0:
        return 0.0
    return round(present * 100 / total, 2)


def attendance_band(percent: float) -> str:
    if percent < CRITICAL_BELOW_PERCENT:
        return "Critical"
    if percent < SAFE_AT_PERCENT:
        return "Watch"
    return "Safe"


def is_shortage(percent: float) -> bool:
    return percent < MIN_ATTENDANCE_PERCENT
