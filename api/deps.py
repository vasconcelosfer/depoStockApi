"""
Dependencias inyectadas por FastAPI.
El cliente WSAA y el cliente SOAP se construyen una sola vez (singleton via lru_cache).
"""
from __future__ import annotations

import os
from functools import lru_cache
from typing import Annotated

from fastapi import Depends, HTTPException, Security
from fastapi.security import APIKeyHeader

from depo_stock import WSAAClient, DepoStockClient

_api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


def verify_api_key(api_key: str | None = Security(_api_key_header)) -> None:
    expected = os.getenv("API_KEY", "")
    if expected and api_key != expected:
        raise HTTPException(status_code=401, detail="API key inválida")


@lru_cache(maxsize=1)
def _wsaa_client() -> WSAAClient:
    return WSAAClient(
        cert_path=os.environ["CERT_PATH"],
        key_path=os.environ["KEY_PATH"],
        production=os.getenv("PRODUCTION", "false").lower() == "true",
    )


@lru_cache(maxsize=1)
def _depo_client() -> DepoStockClient:
    return DepoStockClient(
        cuit=os.environ["CUIT"],
        wsaa_client=_wsaa_client(),
        production=os.getenv("PRODUCTION", "false").lower() == "true",
        tipo_agente=os.getenv("TIPO_AGENTE", "DEPO"),
        rol=os.getenv("ROL", "DEPO"),
    )


def get_depo_client() -> DepoStockClient:
    return _depo_client()
