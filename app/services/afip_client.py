import logging
from zeep import Client
from zeep.exceptions import Fault
from zeep.helpers import serialize_object
from app.core.config import settings
from app.core.wsaa import WSAA
from app.schemas.stock import StockTransmitRequest, StockTransmitResponse
from app.core.exceptions import AFIPException

logger = logging.getLogger(__name__)

class AFIPClient:
    def __init__(self):
        self.client = Client(settings.WGES_STOCK_WSDL_URL)

    def _get_auth_header(self) -> dict:
        credentials = WSAA.get_credentials()
        return {
            "token": credentials["token"],
            "sign": credentials["sign"],
            "cuit": settings.AFIP_CUIT,
            "TipoAgente": "DEPO",
            "Rol": "DEPO"
        }

    def transmit_stock(self, request_data: StockTransmitRequest) -> StockTransmitResponse:
        auth_header = self._get_auth_header()

        # Prepare the payload according to AFIP's schema
        # Note: The exact field names and structure here depend on the WSDL definition
        # The structure is assumed based on the requirement names.

        export_list = [
            {
                "codigoItem": exp.item_code,
                "cantidad": exp.quantity,
                "unidadMedida": exp.unit_of_measure
            } for exp in request_data.export_stock
        ]

        import_list = [
            {
                "codigoItem": imp.item_code,
                "cantidad": imp.quantity,
                "unidadMedida": imp.unit_of_measure
            } for imp in request_data.import_stock
        ]

        empty_containers_list = [
            {
                "identificadorEnvase": ec.container_id,
                "tipoEnvase": ec.container_type
            } for ec in request_data.empty_containers
        ]

        payload = {
            "argWSAutenticacion": auth_header,
            "argStock": {
                "idTransaccion": request_data.transaction_id,
                "codigoAduana": request_data.customs_code,
                "codigoLugarOperativo": request_data.operative_place_code,
                "fechaStock": request_data.stock_date.strftime("%Y-%m-%dT%H:%M:%S"),
                "stockExportacion": export_list if export_list else None,
                "stockImportacion": import_list if import_list else None,
                "envasesVacios": empty_containers_list if empty_containers_list else None
            }
        }

        try:
            # Calling the RegistrarStock method
            response = self.client.service.RegistrarStock(**payload)
            response_data = serialize_object(response)

            # Check for business errors in response
            if response_data and 'errores' in response_data and response_data['errores']:
                error = response_data['errores'][0]
                error_code = error.get('codigo', 500)
                error_msg = error.get('mensaje', 'Unknown AFIP Error')
                raise AFIPException(code=error_code, message=error_msg)

            return StockTransmitResponse(
                transaction_id=request_data.transaction_id,
                status="SUCCESS",
                afip_response=response_data
            )

        except Fault as fault:
            logger.error(f"SOAP Fault: {fault.message}")
            # Try to extract business error code if possible, default to 500
            raise AFIPException(code=500, message=f"SOAP Error: {fault.message}")
        except Exception as e:
            if isinstance(e, AFIPException):
                raise e
            logger.error(f"Unexpected error calling AFIP: {str(e)}")
            raise AFIPException(code=500, message="Internal error communicating with AFIP")
