from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError

from app.ai.errors import (
    AIProviderConfigurationError,
    AIProviderMalformedResponseError,
    AIProviderTimeoutError,
    AIProviderUnavailableError,
    AIProviderValidationError,
)
from app.answers.api.routes import router as answers_router
from app.api.health import router as health_router
from app.documents.api.routes import router as documents_router
from app.documents.errors import (
    DocumentNotFoundError,
    DocumentStateConflictError,
    DocumentUnauthorizedError,
    DocumentValidationError,
)
from app.field_detection.api.routes import router as field_detection_router
from app.field_detection.errors import (
    FieldDetectionAlreadyProcessingError,
    FieldDetectionConfigurationError,
    FieldDetectionNotFoundError,
    FieldDetectionProviderUnavailableError,
    FieldDetectionValidationError,
)
from app.forms.api.routes import router as forms_router
from app.forms.services import (
    ResourceNotFoundError,
    StateConflictError,
    ValidationError,
)
from app.ocr.api.routes import router as ocr_router
from app.ocr.errors import (
    OCRAlreadyProcessingError,
    OCRConfigurationError,
    OCRNotFoundError,
    OCRProviderUnavailableError,
    OCRTimeoutError,
    OCRValidationError,
)
from app.pdf.api.routes import router as pdf_router
from app.questions.api.routes import router as questions_router
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


@app.exception_handler(DocumentNotFoundError)
async def document_not_found_handler(
    request: Request, exc: DocumentNotFoundError
) -> JSONResponse:
    return JSONResponse(status_code=404, content={"detail": str(exc)})


@app.exception_handler(DocumentStateConflictError)
async def document_state_conflict_handler(
    request: Request, exc: DocumentStateConflictError
) -> JSONResponse:
    return JSONResponse(status_code=409, content={"detail": str(exc)})


@app.exception_handler(DocumentValidationError)
async def document_validation_handler(
    request: Request, exc: DocumentValidationError
) -> JSONResponse:
    return JSONResponse(
        status_code=422,
        content={"detail": str(exc), "error_code": exc.error_code},
    )


@app.exception_handler(DocumentUnauthorizedError)
async def document_unauthorized_handler(
    request: Request, exc: DocumentUnauthorizedError
) -> JSONResponse:
    return JSONResponse(
        status_code=401, content={"detail": "Invalid document credentials"}
    )


@app.exception_handler(OCRNotFoundError)
async def ocr_not_found_handler(
    request: Request, exc: OCRNotFoundError
) -> JSONResponse:
    return JSONResponse(status_code=404, content={"detail": str(exc)})


@app.exception_handler(OCRValidationError)
async def ocr_validation_handler(
    request: Request, exc: OCRValidationError
) -> JSONResponse:
    return JSONResponse(
        status_code=422,
        content={"detail": str(exc), "error_code": exc.error_code},
    )


@app.exception_handler(OCRAlreadyProcessingError)
async def ocr_already_processing_handler(
    request: Request, exc: OCRAlreadyProcessingError
) -> JSONResponse:
    return JSONResponse(status_code=409, content={"detail": str(exc)})


@app.exception_handler(OCRProviderUnavailableError)
async def ocr_unavailable_handler(
    request: Request, exc: OCRProviderUnavailableError
) -> JSONResponse:
    return JSONResponse(
        status_code=503,
        content={"detail": "OCR service is temporarily unavailable. Please try again."},
    )


@app.exception_handler(OCRTimeoutError)
async def ocr_timeout_handler(request: Request, exc: OCRTimeoutError) -> JSONResponse:
    return JSONResponse(
        status_code=504,
        content={"detail": "OCR processing timed out. Please try again."},
    )


@app.exception_handler(OCRConfigurationError)
async def ocr_config_handler(
    request: Request, exc: OCRConfigurationError
) -> JSONResponse:
    return JSONResponse(
        status_code=500,
        content={"detail": "OCR provider is misconfigured. Contact the administrator."},
    )


@app.exception_handler(FieldDetectionNotFoundError)
async def field_detection_not_found_handler(
    request: Request, exc: FieldDetectionNotFoundError
) -> JSONResponse:
    return JSONResponse(status_code=404, content={"detail": str(exc)})


@app.exception_handler(FieldDetectionValidationError)
async def field_detection_validation_handler(
    request: Request, exc: FieldDetectionValidationError
) -> JSONResponse:
    return JSONResponse(
        status_code=422,
        content={"detail": str(exc), "error_code": exc.error_code},
    )


@app.exception_handler(FieldDetectionAlreadyProcessingError)
async def field_detection_already_processing_handler(
    request: Request, exc: FieldDetectionAlreadyProcessingError
) -> JSONResponse:
    return JSONResponse(status_code=409, content={"detail": str(exc)})


@app.exception_handler(FieldDetectionProviderUnavailableError)
async def field_detection_unavailable_handler(
    request: Request, exc: FieldDetectionProviderUnavailableError
) -> JSONResponse:
    return JSONResponse(
        status_code=503,
        content={
            "detail": "Field detection service is temporarily unavailable. Please try again."
        },
    )


@app.exception_handler(FieldDetectionConfigurationError)
async def field_detection_config_handler(
    request: Request, exc: FieldDetectionConfigurationError
) -> JSONResponse:
    return JSONResponse(
        status_code=500,
        content={
            "detail": "Field detection provider is misconfigured. Contact the administrator."
        },
    )


@app.exception_handler(AIProviderUnavailableError)
async def ai_unavailable_handler(
    request: Request, exc: AIProviderUnavailableError
) -> JSONResponse:
    return JSONResponse(
        status_code=503,
        content={"detail": "AI service is temporarily unavailable. Please try again."},
    )


@app.exception_handler(AIProviderTimeoutError)
async def ai_timeout_handler(
    request: Request, exc: AIProviderTimeoutError
) -> JSONResponse:
    return JSONResponse(
        status_code=504,
        content={"detail": "AI service timed out. Please try again."},
    )


@app.exception_handler(AIProviderMalformedResponseError)
async def ai_malformed_handler(
    request: Request, exc: AIProviderMalformedResponseError
) -> JSONResponse:
    return JSONResponse(
        status_code=502,
        content={"detail": "AI service returned an unexpected response."},
    )


@app.exception_handler(AIProviderValidationError)
async def ai_validation_handler(
    request: Request, exc: AIProviderValidationError
) -> JSONResponse:
    return JSONResponse(
        status_code=502,
        content={"detail": "AI service response did not match the expected format."},
    )


@app.exception_handler(AIProviderConfigurationError)
async def ai_config_handler(
    request: Request, exc: AIProviderConfigurationError
) -> JSONResponse:
    return JSONResponse(
        status_code=500,
        content={"detail": "AI provider is misconfigured. Contact the administrator."},
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
app.include_router(questions_router, prefix="/api")
app.include_router(pdf_router, prefix="/api")
app.include_router(documents_router, prefix="/api")
app.include_router(ocr_router, prefix="/api")
app.include_router(field_detection_router, prefix="/api")
