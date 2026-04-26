from fastapi import APIRouter, Depends, HTTPException

from depo_stock import DepoStockClient, DummyResponse
from depo_stock.exceptions import DepoStockError

from ..deps import get_depo_client, verify_api_key

router = APIRouter()


@router.get(
    "",
    response_model=DummyResponse,
    summary="Estado del WS de ARCA/AFIP",
    dependencies=[Depends(verify_api_key)],
)
def dummy(client: DepoStockClient = Depends(get_depo_client)):
    """
    Llama al método Dummy de wgesStockDepositosFiscales.
    Verifica que los servidores de aplicación, base de datos y autenticación
    de ARCA/AFIP estén operativos.
    """
    try:
        return client.dummy()
    except DepoStockError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
