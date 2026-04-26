from fastapi import APIRouter, Depends, HTTPException

from depo_stock import (
    DepoStockClient,
    RegistrarStockRequest,
    RegistrarStockResponse,
)
from depo_stock.exceptions import DepoStockError, ValidationError

from ..deps import get_depo_client, verify_api_key

router = APIRouter()


@router.post(
    "",
    response_model=RegistrarStockResponse,
    summary="Registrar stock en depósito fiscal",
    dependencies=[Depends(verify_api_key)],
)
def registrar_stock(
    body: RegistrarStockRequest,
    client: DepoStockClient = Depends(get_depo_client),
):
    """
    Envía el stock completo del depósito a ARCA/AFIP mediante el método
    RegistrarStock del WS wgesStockDepositosFiscales.

    - **id_transaccion**: Identificador único por invocación. Ante un timeout,
      reenviar *exactamente* el mismo id para recuperar la respuesta original.
    - **codigo_aduana**: Código de aduana de 3 dígitos.
    - **codigo_lugar_operativo**: Código LOT asignado por AFIP.
    - **fecha_stock**: Fecha de declaración del stock (no puede ser futura).
    - **stock_exportacion**: Lista de permisos de embarque.
    - **stock_importacion**: Lista de documentos de transporte.
    - **contenedores_vacios**: Lista de contenedores vacíos en el depósito.
    """
    try:
        return client.registrar_stock(body)
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except DepoStockError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
