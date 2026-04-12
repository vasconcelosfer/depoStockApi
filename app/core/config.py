from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional

class Settings(BaseSettings):
    ENVIRONMENT: str = "development"

    # AFIP Web Services URLs (Default to testing/homo environments)
    WSAA_WSDL_URL: str = "https://wsaahomo.afip.gov.ar/ws/services/LoginCms?wsdl"
    WGES_STOCK_WSDL_URL: str = "https://fwshomo.afip.gov.ar/wgesStockDepositosFiscales/WgesStockDepositosFiscalesService?wsdl"

    # AFIP Credentials and Configuration
    AFIP_CERT_PATH: str = "/app/certs/cert.crt"
    AFIP_KEY_PATH: str = "/app/certs/private.key"
    AFIP_CUIT: str

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

settings = Settings()
