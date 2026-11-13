from fastapi import FastAPI, Request
from fastapi.exceptions import HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.encoders import jsonable_encoder
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import settings
from app.routers import catalog, comparison, geospatial, health


app = FastAPI(title=settings.app_name, version=settings.app_version)
app.add_middleware(CORSMiddleware, allow_origins=list(settings.cors_origins), allow_credentials=False, allow_methods=["GET", "POST"], allow_headers=["*"])
app.include_router(health.router, prefix="/api", tags=["system"])
app.include_router(catalog.router, prefix="/api", tags=["catalog"])
app.include_router(comparison.router, prefix="/api", tags=["comparison"])
app.include_router(geospatial.router, prefix="/api", tags=["geospatial provenance"])


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(_: Request, exc: RequestValidationError):
    return JSONResponse(status_code=422, content=jsonable_encoder({"error": {"code": "validation_error", "message": "Request validation failed", "details": exc.errors()}}))


@app.exception_handler(HTTPException)
async def http_exception_handler(_: Request, exc: HTTPException):
    detail = exc.detail if isinstance(exc.detail, dict) else {"code": "http_error", "message": str(exc.detail)}
    return JSONResponse(status_code=exc.status_code, content={"error": detail})


@app.get("/")
def root():
    return {"service": settings.app_name, "docs": "/docs", "health": "/api/health"}

