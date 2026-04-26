"""
DepoStock REST API
==================
Wrapper HTTP/JSON sobre el WebService SOAP wgesStockDepositosFiscales de ARCA/AFIP.

Cómo ejecutar
-------------
::

    # Instalar dependencias
    pip install -e ".[dev]"

    # Configurar variables de entorno (ver .env.example)
    cp .env.example .env && nano .env

    # Iniciar servidor de desarrollo
    PYTHONPATH=src uvicorn api.main:app --reload --port 8000

    # Documentación interactiva disponible en:
    #   http://localhost:8000/docs   (Swagger UI)
    #   http://localhost:8000/redoc  (ReDoc)
"""
from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI

from .routes import health, stock

load_dotenv()
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)


@asynccontextmanager
async def _lifespan(app: FastAPI):
    logger.info("DepoStock API iniciada")
    yield
    logger.info("DepoStock API detenida")


app = FastAPI(
    title="DepoStock API",
    description=(
        "REST wrapper para el WebService **wgesStockDepositosFiscales** de ARCA/AFIP. "
        "Permite registrar el stock de depósitos fiscales desde cualquier sistema "
        "(Odoo, ERPs, scripts, etc.) sin necesidad de implementar SOAP directamente."
    ),
    version="1.0.0",
    lifespan=_lifespan,
)

app.include_router(health.router, prefix="/health", tags=["Health"])
app.include_router(stock.router, prefix="/stock", tags=["Stock"])


@app.get("/", include_in_schema=False)
def root():
    return {"service": "DepoStock API", "docs": "/docs"}
