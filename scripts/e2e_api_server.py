"""Start an isolated, fake-data API for the browser smoke test."""

import os
from pathlib import Path

import uvicorn

from app.core.config import settings
from app.core.database import Base, SessionLocal, engine
from app.seed import seed_demo_data


def main() -> None:
    if not settings.seed_default_password:
        raise SystemExit(
            "Set SEED_DEFAULT_PASSWORD in the project .env before running the browser test."
        )
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    with SessionLocal() as db:
        seed_demo_data(
            db,
            students_file=Path(__file__).resolve().parents[1]
            / "backend"
            / "seed"
            / "sample"
            / "students.sample.csv",
            reset=True,
        )
    uvicorn.run(
        "app.main:app",
        host="127.0.0.1",
        port=int(os.environ.get("E2E_API_PORT", "18000")),
        log_level="warning",
    )


if __name__ == "__main__":
    main()
