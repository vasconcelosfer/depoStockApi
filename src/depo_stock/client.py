"""
Cliente SOAP para wgesStockDepositosFiscales (ARCA/AFIP).

Envuelve los métodos Dummy y RegistrarStock con tipado fuerte (Pydantic)
y manejo transparente de la autenticación WSAA.
"""
from __future__ import annotations

import logging
from typing import Optional

import zeep
from zeep.exceptions import Fault
from zeep.transports import Transport

from .exceptions import SOAPError
from .models import (
    ContenedorAsociado,
    DummyResponse,
    ErrorItem,
    LineaMercaderia,
    RegistrarStockRequest,
    RegistrarStockResponse,
)
from .wsaa import WSAAClient

logger = logging.getLogger(__name__)

_WS_WSDL_TESTING = (
    "https://wsaduhomoext.afip.gob.ar/diav2/wgesstockdepositosfiscales/"
    "wgesstockdepositosfiscales.asmx?wsdl"
)
_WS_WSDL_PRODUCTION = (
    "https://webservicesadu.afip.gob.ar/diav2/wgesStockDepositosFiscales/"
    "wgesStockDepositosFiscales.asmx?wsdl"
)


class DepoStockClient:
    """
    Cliente de alto nivel para el WS wgesStockDepositosFiscales.

    Parámetros
    ----------
    cuit : str
        CUIT del depositario (con o sin guiones).
    wsaa_client : WSAAClient
        Instancia que provee Token y Sign desde WSAA.
    production : bool
        False → homologación, True → producción.
    tipo_agente : str
        Código del tipo de agente (default "DEPO").
    rol : str
        Rol del usuario (default "DEPO").

    Ejemplo básico
    --------------
    ::

        from depo_stock import WSAAClient, DepoStockClient, RegistrarStockRequest

        wsaa = WSAAClient("cert.pem", "key.pem")
        client = DepoStockClient(cuit="20123456789", wsaa_client=wsaa)

        resp = client.registrar_stock(RegistrarStockRequest(
            id_transaccion="TX-001",
            codigo_aduana="001",
            codigo_lugar_operativo="10057",
            fecha_stock=datetime.now(timezone.utc),
            stock_exportacion=[...],
        ))
        print(resp.mensaje_aceptado, resp.errores)
    """

    def __init__(
        self,
        cuit: str,
        wsaa_client: WSAAClient,
        production: bool = False,
        tipo_agente: str = "DEPO",
        rol: str = "DEPO",
    ):
        self.cuit = cuit.replace("-", "")
        self.wsaa_client = wsaa_client
        self.production = production
        self.tipo_agente = tipo_agente
        self.rol = rol
        self._wsdl = _WS_WSDL_PRODUCTION if production else _WS_WSDL_TESTING
        self._zeep: Optional[zeep.Client] = None

    # ------------------------------------------------------------------
    # Helpers internos
    # ------------------------------------------------------------------

    def _get_client(self) -> zeep.Client:
        if self._zeep is None:
            transport = Transport(timeout=60, operation_timeout=120)
            self._zeep = zeep.Client(self._wsdl, transport=transport)
        return self._zeep

    def _build_auth(self) -> dict:
        tok = self.wsaa_client.get_token()
        return {
            "Token": tok.token,
            "Sign": tok.sign,
            "CuitEmpresaConectada": int(self.cuit),
            "TipoAgente": self.tipo_agente,
            "Rol": self.rol,
        }

    @staticmethod
    def _lineas_to_dict(lineas: list[LineaMercaderia]) -> Optional[dict]:
        if not lineas:
            return None
        return {
            "LineaMercaderia": [
                {
                    "TipoEmbalaje": lm.tipo_embalaje,
                    "Cantidad": lm.cantidad,
                    "PesoBruto": lm.peso_bruto,
                }
                for lm in lineas
            ]
        }

    @staticmethod
    def _contenedores_to_dict(contenedores: list[ContenedorAsociado]) -> Optional[dict]:
        if not contenedores:
            return None
        items = []
        for c in contenedores:
            item: dict = {
                "TipoContenedor": c.tipo_contenedor,
                "NumeroContenedor": c.numero_contenedor,
                "LongitudContenedor": c.longitud_contenedor,
            }
            if c.cantidad_bultos is not None:
                item["CantidadBultos"] = c.cantidad_bultos
            items.append(item)
        return {"ContenedorAsociado": items}

    def _permiso_to_dict(self, pe) -> dict:
        return {
            "IdentificadorPermiso": pe.identificador_permiso,
            "IdentificadorRemito": pe.identificador_remito,
            "Exportador": pe.exportador,
            "DestinoMercaderia": pe.destino_mercaderia,
            "DestinatarioExterior": pe.destinatario_exterior,
            "FechaIngresoDeposito": pe.fecha_ingreso_deposito,
            "CondicionMercaderia": pe.condicion_mercaderia,
            "UbicacionPartida": pe.ubicacion_partida,
            "CondicionImo": pe.condicion_imo,
            "NumeroImo": pe.numero_imo,
            "ImpedimentoLegalAduanero": pe.impedimento_legal_aduanero,
            "TipoImpedimentoLegalAduanero": pe.tipo_impedimento_legal_aduanero,
            "DescripcionImpedimentoLegalAduanero": pe.descripcion_impedimento_legal_aduanero,
            "Observaciones": pe.observaciones,
            "LineasMercaderia": self._lineas_to_dict(pe.lineas_mercaderia),
            "Contenedores": self._contenedores_to_dict(pe.contenedores),
        }

    def _doc_transporte_to_dict(self, dt) -> dict:
        return {
            "IdentificadorManifiesto": dt.identificador_manifiesto,
            "IdentificadorDocumentoTransporte": dt.identificador_documento_transporte,
            "Consignatario": dt.consignatario,
            "ProcedenciaMercaderia": dt.procedencia_mercaderia,
            "FechaIngresoDeposito": dt.fecha_ingreso_deposito,
            "CondicionMercaderia": dt.condicion_mercaderia,
            "UbicacionPartida": dt.ubicacion_partida,
            "CondicionImo": dt.condicion_imo,
            "NumeroImo": dt.numero_imo,
            "ImpedimentoLegalAduanero": dt.impedimento_legal_aduanero,
            "TipoImpedimentoLegalAduanero": dt.tipo_impedimento_legal_aduanero,
            "DescripcionImpedimentoLegalAduanero": dt.descripcion_impedimento_legal_aduanero,
            "Observaciones": dt.observaciones,
            "LineasMercaderia": self._lineas_to_dict(dt.lineas_mercaderia),
            "Contenedores": self._contenedores_to_dict(dt.contenedores),
        }

    @staticmethod
    def _parse_errores(lista_errores) -> list[ErrorItem]:
        if not lista_errores:
            return []
        items = []
        # zeep puede retornar distintas estructuras según el WSDL
        iterable = lista_errores if hasattr(lista_errores, "__iter__") else [lista_errores]
        for item in iterable:
            if hasattr(item, "codigo"):
                items.append(ErrorItem(codigo=item.codigo, descripcion=item.descripcion))
        return items

    # ------------------------------------------------------------------
    # Métodos públicos
    # ------------------------------------------------------------------

    def dummy(self) -> DummyResponse:
        """
        Verifica el estado de la infraestructura del WS.
        No requiere autenticación.
        """
        client = self._get_client()
        try:
            result = client.service.Dummy()
        except Fault as exc:
            raise SOAPError(str(exc), fault_code=str(exc.code)) from exc
        except Exception as exc:
            raise SOAPError(str(exc)) from exc

        return DummyResponse(
            appserver=getattr(result, "Appserver", "NO") or "NO",
            dbserver=getattr(result, "Dbserver", "NO") or "NO",
            authserver=getattr(result, "AuthServer", "NO") or "NO",
        )

    def registrar_stock(self, params: RegistrarStockRequest) -> RegistrarStockResponse:
        """
        Envía el stock del depósito a ARCA/AFIP.

        En una misma invocación se registra toda la mercadería del depósito:
        exportación, importación y contenedores vacíos. El WS no admite
        rectificaciones posteriores.

        Parámetros
        ----------
        params : RegistrarStockRequest
            Datos validados del stock. Verificar que id_transaccion sea único.
        """
        client = self._get_client()
        auth = self._build_auth()

        stock_exp = None
        if params.stock_exportacion:
            stock_exp = {
                "PermisoEmbarque": [
                    self._permiso_to_dict(pe) for pe in params.stock_exportacion
                ]
            }

        stock_imp = None
        if params.stock_importacion:
            stock_imp = {
                "DocumentoTransporte": [
                    self._doc_transporte_to_dict(dt) for dt in params.stock_importacion
                ]
            }

        cont_vacios = None
        if params.contenedores_vacios:
            cont_vacios = {
                "ContenedorVacio": [
                    {
                        "FechaIngresoDeposito": cv.fecha_ingreso_deposito,
                        "NumeroContenedor": cv.numero_contenedor,
                        "LongitudContenedor": cv.longitud_contenedor,
                    }
                    for cv in params.contenedores_vacios
                ]
            }

        stock_payload = {
            "IdTransaccion": params.id_transaccion,
            "CodigoAduana": params.codigo_aduana,
            "CodigoLugarOperativo": params.codigo_lugar_operativo,
            "FechaStock": params.fecha_stock,
            "StockExportacion": stock_exp,
            "StockImportacion": stock_imp,
            "ContenedoresVacios": cont_vacios,
        }

        logger.info(
            "RegistrarStock CUIT=%s TRX=%s aduana=%s LOT=%s",
            self.cuit,
            params.id_transaccion,
            params.codigo_aduana,
            params.codigo_lugar_operativo,
        )

        try:
            result = client.service.RegistrarStock(
                argWSAutenticacion=auth,
                stock=stock_payload,
            )
        except Fault as exc:
            raise SOAPError(str(exc), fault_code=str(exc.code)) from exc
        except Exception as exc:
            raise SOAPError(str(exc)) from exc

        return RegistrarStockResponse(
            mensaje_aceptado=bool(result.MensajeAceptado),
            server=getattr(result, "Server", None),
            timestamp=getattr(result, "TimeStamp", None),
            errores=self._parse_errores(getattr(result, "ListaErrores", None)),
        )
