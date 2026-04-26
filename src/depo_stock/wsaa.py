"""
WSAA — Web Service de Autenticación y Autorización de ARCA/AFIP.

Genera y cachea el par (Token, Sign) necesario para invocar cualquier
web service de AFIP. El token tiene vigencia de 12 horas; se renueva
automáticamente 2 horas antes de su vencimiento.
"""
from __future__ import annotations

import base64
import logging
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional

import zeep
from zeep.transports import Transport
from cryptography import x509
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.serialization import pkcs7

from .exceptions import WSAAError

logger = logging.getLogger(__name__)

_WSAA_WSDL_TESTING = "https://wsaahomo.afip.gov.ar/ws/services/LoginCms?wsdl"
_WSAA_WSDL_PRODUCTION = "https://wsaa.afip.gov.ar/ws/services/LoginCms?wsdl"
_SERVICE_NAME = "wgesStockDepositosFiscales"
_REFRESH_MARGIN = timedelta(hours=2)


class WSAAToken:
    def __init__(self, token: str, sign: str, expiration: datetime):
        self.token = token
        self.sign = sign
        self.expiration = expiration

    def is_valid(self) -> bool:
        return datetime.now(timezone.utc) < (self.expiration - _REFRESH_MARGIN)


class WSAAClient:
    """
    Obtiene y cachea tokens WSAA para el servicio wgesStockDepositosFiscales.

    Parámetros
    ----------
    cert_path : str
        Ruta al certificado X.509 en formato PEM emitido por AFIP.
    key_path : str
        Ruta a la clave privada RSA en formato PEM.
    production : bool
        False → ambiente de homologación, True → producción.

    Ejemplo
    -------
    ::

        wsaa = WSAAClient("certificado.crt", "clave.key")
        token = wsaa.get_token()
        print(token.token, token.sign)
    """

    def __init__(self, cert_path: str, key_path: str, production: bool = False):
        self.cert_path = Path(cert_path)
        self.key_path = Path(key_path)
        self.production = production
        self._wsdl = _WSAA_WSDL_PRODUCTION if production else _WSAA_WSDL_TESTING
        self._cached: Optional[WSAAToken] = None

    # ------------------------------------------------------------------
    # Construcción y firma del TRA
    # ------------------------------------------------------------------

    def _build_tra(self) -> str:
        now = datetime.now(timezone.utc)
        expiration = now + timedelta(hours=12)
        fmt = "%Y-%m-%dT%H:%M:%S+00:00"
        return (
            '<?xml version="1.0" encoding="UTF-8"?>'
            '<loginTicketRequest version="1.0">'
            "<header>"
            f"<uniqueId>{int(now.timestamp())}</uniqueId>"
            f"<generationTime>{now.strftime(fmt)}</generationTime>"
            f"<expirationTime>{expiration.strftime(fmt)}</expirationTime>"
            "</header>"
            f"<service>{_SERVICE_NAME}</service>"
            "</loginTicketRequest>"
        )

    def _sign_tra(self, tra: str) -> str:
        try:
            cert_pem = self.cert_path.read_bytes()
            key_pem = self.key_path.read_bytes()
        except OSError as exc:
            raise WSAAError(f"No se pudo leer cert/key: {exc}") from exc

        try:
            cert = x509.load_pem_x509_certificate(cert_pem, default_backend())
            key = serialization.load_pem_private_key(key_pem, password=None, backend=default_backend())
        except Exception as exc:
            raise WSAAError(f"Error al cargar certificado/clave: {exc}") from exc

        try:
            signed_der = (
                pkcs7.PKCS7SignatureBuilder()
                .set_data(tra.encode("utf-8"))
                .add_signer(cert, key, hashes.SHA256())
                .sign(serialization.Encoding.DER, [pkcs7.PKCS7Options.DetachedSignature])
            )
            return base64.b64encode(signed_der).decode("ascii")
        except Exception as exc:
            raise WSAAError(f"Error al firmar TRA: {exc}") from exc

    # ------------------------------------------------------------------
    # Parseo de la respuesta
    # ------------------------------------------------------------------

    def _parse_response(self, xml_response: str) -> WSAAToken:
        try:
            root = ET.fromstring(xml_response)
        except ET.ParseError as exc:
            raise WSAAError(f"Respuesta WSAA no válida: {exc}") from exc

        token = root.findtext(".//token")
        sign = root.findtext(".//sign")
        exp_str = root.findtext(".//expirationTime")

        if not token or not sign or not exp_str:
            raise WSAAError("Respuesta WSAA incompleta: faltan token/sign/expirationTime")

        expiration = datetime.fromisoformat(exp_str)
        if expiration.tzinfo is None:
            expiration = expiration.replace(tzinfo=timezone.utc)

        return WSAAToken(token=token, sign=sign, expiration=expiration)

    # ------------------------------------------------------------------
    # API pública
    # ------------------------------------------------------------------

    def get_token(self, force_refresh: bool = False) -> WSAAToken:
        """
        Devuelve un token válido, renovándolo si es necesario.

        Parámetros
        ----------
        force_refresh : bool
            Si True, ignora la caché y solicita un token nuevo.
        """
        if not force_refresh and self._cached and self._cached.is_valid():
            return self._cached

        logger.info("Solicitando token WSAA (produccion=%s)", self.production)

        try:
            client = zeep.Client(self._wsdl, transport=Transport(timeout=30))
        except Exception as exc:
            raise WSAAError(f"No se pudo conectar al WSAA: {exc}") from exc

        tra = self._build_tra()
        cms = self._sign_tra(tra)

        try:
            response_xml = client.service.loginCms(in0=cms)
        except Exception as exc:
            raise WSAAError(f"WSAA loginCms falló: {exc}") from exc

        self._cached = self._parse_response(response_xml)
        logger.info("Token WSAA obtenido, vence: %s", self._cached.expiration)
        return self._cached
