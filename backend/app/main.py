from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError

from app.answers.api.routes import router as answers_router
from app.api.health import router as health_router
from app.forms.api.routes import router as forms_router
from app.forms.services import (
    ResourceNotFoundError,
    StateConflictError,
    ValidationError,
)
from app.sessions.api.routes import router as sessions_router
from app.sessions.services import (
    ResourceNotFoundError as SessionResourceNotFoundError,
)
from app.sessions.services import (
    StateConflictError as SessionStateConflictError,
)
from app.sessions.services import (
    UnauthorizedError,
)
from app.sessions.services import (
    ValidationError as SessionValidationError,
)

app = FastAPI(
    title="AI Form Assistant API",
    description="Multilingual AI form assistant API",
    version="1.0.0",
)


# Exception handlers mapping service layer exceptions to HTTP codes
@app.exception_handler(ResourceNotFoundError)
async def resource_not_found_handler(
    request: Request, exc: ResourceNotFoundError
) -> JSONResponse:
    return JSONResponse(status_code=404, content={"detail": str(exc)})


@app.exception_handler(SessionResourceNotFoundError)
async def session_resource_not_found_handler(
    request: Request, exc: SessionResourceNotFoundError
) -> JSONResponse:
    return JSONResponse(status_code=404, content={"detail": str(exc)})


@app.exception_handler(StateConflictError)
async def state_conflict_handler(
    request: Request, exc: StateConflictError
) -> JSONResponse:
    return JSONResponse(status_code=409, content={"detail": str(exc)})


@app.exception_handler(SessionStateConflictError)
async def session_state_conflict_handler(
    request: Request, exc: SessionStateConflictError
) -> JSONResponse:
    return JSONResponse(status_code=409, content={"detail": str(exc)})


@app.exception_handler(IntegrityError)
async def integrity_error_handler(
    request: Request, exc: IntegrityError
) -> JSONResponse:
    return JSONResponse(
        status_code=409,
        content={"detail": "Database integrity violation."},
    )


@app.exception_handler(ValidationError)
async def validation_handler(request: Request, exc: ValidationError) -> JSONResponse:
    return JSONResponse(status_code=422, content={"detail": str(exc)})


@app.exception_handler(SessionValidationError)
async def session_validation_handler(
    request: Request, exc: SessionValidationError
) -> JSONResponse:
    return JSONResponse(status_code=422, content={"detail": str(exc)})


@app.exception_handler(UnauthorizedError)
async def unauthorized_handler(
    request: Request, exc: UnauthorizedError
) -> JSONResponse:
    return JSONResponse(
        status_code=401, content={"detail": "Invalid session credentials"}
    )


# Set up CORS middleware - in dev, allow localhost frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Restrict in production, but * is simple for dev foundation
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health_router, prefix="/api")
app.include_router(forms_router, prefix="/api")
app.include_router(sessions_router, prefix="/api")
app.include_router(answers_router, prefix="/api")
