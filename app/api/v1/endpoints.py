from fastapi import APIRouter, Depends
from app.schemas.stock import StockTransmitRequest, StockTransmitResponse
from app.services.afip_client import AFIPClient

router = APIRouter()

def get_afip_client() -> AFIPClient:
    return AFIPClient()

@router.post("/transmit", response_model=StockTransmitResponse)
def transmit_stock(
    request: StockTransmitRequest,
    client: AFIPClient = Depends(get_afip_client)
):
    """
    Transmit daily stock operations to AFIP's wgesStockDepositosFiscales service.
    Validates incoming JSON and converts it to SOAP.
    """
    response = client.transmit_stock(request)
    return response
