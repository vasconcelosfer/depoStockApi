class DepoStockError(Exception):
    """Base exception."""


class WSAAError(DepoStockError):
    """WSAA authentication/signing error."""


class SOAPError(DepoStockError):
    """SOAP service communication error."""

    def __init__(self, message: str, fault_code: str | None = None):
        super().__init__(message)
        self.fault_code = fault_code


class ValidationError(DepoStockError):
    """Business data validation error."""
