from fastapi import FastAPI, HTTPException, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from sqlalchemy.exc import IntegrityError

from app.api.auth import router as auth_router
from app.api.student import router as student_router
from app.api.teacher import router as teacher_router
from app.core.config import settings

app = FastAPI(
    title="OIST Mock ERP API",
    version="0.1.0",
    description="Role-scoped mock college ERP API.",
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        origin.strip() for origin in settings.frontend_origins.split(",") if origin.strip()
    ],
    allow_credentials=False,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)


class HealthResponse(BaseModel):
    status: str


class RootResponse(BaseModel):
    service: str
    docs: str
    openapi: str
    health: str


@app.exception_handler(HTTPException)
async def http_error_handler(_: Request, exc: HTTPException) -> JSONResponse:
    detail = exc.detail
    if isinstance(detail, dict) and "code" in detail:
        body = {"error": {**detail, "details": detail.get("details")}}
    else:
        body = {"error": {"code": "request_error", "message": str(detail), "details": None}}
    return JSONResponse(status_code=exc.status_code, content=body, headers=exc.headers)


@app.exception_handler(RequestValidationError)
async def validation_error_handler(_: Request, exc: RequestValidationError) -> JSONResponse:
    safe_errors = [
        {key: value for key, value in error.items() if key in {"loc", "msg", "type"}}
        for error in exc.errors()
    ]
    return JSONResponse(
        status_code=422,
        content=jsonable_encoder(
            {
                "error": {
                    "code": "validation_error",
                    "message": "Request validation failed.",
                    "details": safe_errors,
                }
            }
        ),
    )


@app.exception_handler(IntegrityError)
async def integrity_error_handler(_: Request, __: IntegrityError) -> JSONResponse:
    return JSONResponse(
        status_code=409,
        content={
            "error": {
                "code": "conflict",
                "message": "The request conflicts with existing data.",
                "details": None,
            }
        },
    )


@app.get(
    "/",
    response_model=RootResponse,
    summary="Get API entry points",
    tags=["system"],
)
def root() -> RootResponse:
    return RootResponse(
        service="OIST Mock ERP API",
        docs="/docs",
        openapi="/openapi.json",
        health="/health",
    )


@app.get(
    "/health",
    response_model=HealthResponse,
    summary="Check API availability",
    tags=["system"],
)
def health() -> HealthResponse:
    return HealthResponse(status="ok")


app.include_router(auth_router, prefix="/api/v1")
app.include_router(student_router, prefix="/api/v1")
app.include_router(teacher_router, prefix="/api/v1")
