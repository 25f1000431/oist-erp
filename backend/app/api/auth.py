from collections import defaultdict, deque
from threading import Lock
from time import monotonic

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.config import settings
from app.core.database import get_db
from app.core.security import DUMMY_PASSWORD_HASH, create_access_token, verify_password
from app.models import AppUser, Student
from app.schemas.auth import LoginRequest, TokenResponse, UserSummary

router = APIRouter(prefix="/auth", tags=["auth"])
_attempts: dict[str, deque[float]] = defaultdict(deque)
_attempts_lock = Lock()


def _rate_keys(request: Request, login_id: str) -> tuple[str, str, str]:
    ip = request.client.host if request.client else "unknown"
    identifier = login_id.strip().casefold()
    return f"ip:{ip}", f"login:{identifier}", f"pair:{ip}:{identifier}"


def _check_rate_limit(keys: tuple[str, ...]) -> None:
    now = monotonic()
    with _attempts_lock:
        for key in list(_attempts):
            attempts = _attempts[key]
            while attempts and now - attempts[0] >= settings.login_rate_limit_window_seconds:
                attempts.popleft()
            if not attempts:
                del _attempts[key]
        if any(len(_attempts.get(key, ())) >= settings.login_rate_limit_attempts for key in keys):
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail={
                    "code": "rate_limited",
                    "message": "Too many login attempts. Try again shortly.",
                },
                headers={"Retry-After": str(settings.login_rate_limit_window_seconds)},
            )
        for key in keys:
            _attempts.setdefault(key, deque()).append(now)


def _find_user(db: Session, login_id: str) -> AppUser | None:
    identifier = login_id.strip()
    normalized = identifier.casefold()
    users = list(
        db.scalars(
            select(AppUser).where(
                or_(
                    func.lower(AppUser.login_id) == normalized,
                    func.lower(AppUser.email) == normalized,
                )
            )
        ).all()
    )
    # Student alternatives use stored identifiers; request fields never define identity.
    matching_students = list(
        db.scalars(
            select(Student).where(
                or_(
                    func.lower(Student.roll_no) == normalized,
                    func.lower(Student.email) == normalized,
                    func.lower(Student.enrollment_no) == normalized,
                )
            )
        ).all()
    )
    users.extend(db.get(AppUser, student.user_id) for student in matching_students)
    unique = {user.id: user for user in users if user is not None}
    return next(iter(unique.values())) if len(unique) == 1 else None


@router.post("/login", response_model=TokenResponse, summary="Log in and receive a bearer token")
def login(payload: LoginRequest, request: Request, db: Session = Depends(get_db)) -> TokenResponse:
    _check_rate_limit(_rate_keys(request, payload.login_id))
    user = _find_user(db, payload.login_id)
    encoded = user.password_hash if user else DUMMY_PASSWORD_HASH
    password_ok = verify_password(payload.password, encoded)
    if not user or not user.is_active or not password_ok:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "login_failed", "message": "Login failed."},
            headers={"WWW-Authenticate": "Bearer"},
        )
    token = create_access_token(user_id=user.id, role=user.role)
    return TokenResponse(access_token=token, role=user.role, user=UserSummary.model_validate(user))


@router.get("/me", response_model=UserSummary, summary="Get the authenticated user's account")
def read_me(user: AppUser = Depends(get_current_user)) -> UserSummary:
    return UserSummary.model_validate(user)
