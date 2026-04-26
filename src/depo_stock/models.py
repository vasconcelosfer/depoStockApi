from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field, model_validator


class LineaMercaderia(BaseModel):
    tipo_embalaje: str
    cantidad: int
    peso_bruto: int


class ContenedorAsociado(BaseModel):
    """ContenedorAsociadoType — contenedor vinculado a un permiso o documento."""
    tipo_contenedor: str  # House | Pier | Correo
    numero_contenedor: str
    longitud_contenedor: str
    cantidad_bultos: Optional[int] = None


class ContenedorVacio(BaseModel):
    """ContenedorVacioType — contenedor sin mercadería en el depósito."""
    fecha_ingreso_deposito: datetime
    numero_contenedor: str
    longitud_contenedor: str


class PermisoEmbarque(BaseModel):
    """PermisoEmbarqueType — unidad de Stock de Exportación."""
    identificador_permiso: Optional[str] = None
    identificador_remito: Optional[str] = None
    exportador: int
    destino_mercaderia: str
    destinatario_exterior: str
    fecha_ingreso_deposito: datetime
    condicion_mercaderia: str  # Buena | Mala
    ubicacion_partida: str
    condicion_imo: bool
    numero_imo: Optional[str] = None  # obligatorio si condicion_imo=True
    impedimento_legal_aduanero: bool
    tipo_impedimento_legal_aduanero: Optional[str] = None   # obligatorio si impedimento=True
    descripcion_impedimento_legal_aduanero: Optional[str] = None  # obligatorio si impedimento=True
    observaciones: Optional[str] = None
    lineas_mercaderia: list[LineaMercaderia] = Field(default_factory=list)
    contenedores: list[ContenedorAsociado] = Field(default_factory=list)

    @model_validator(mode="after")
    def _validar_campos_condicionales(self) -> "PermisoEmbarque":
        if not self.identificador_permiso and not self.identificador_remito:
            raise ValueError(
                "Debe informar al menos IdentificadorPermiso o IdentificadorRemito"
            )
        if self.condicion_imo and not self.numero_imo:
            raise ValueError("NumeroImo es obligatorio cuando CondicionImo es verdadero")
        if self.impedimento_legal_aduanero:
            if not self.tipo_impedimento_legal_aduanero:
                raise ValueError(
                    "TipoImpedimentoLegalAduanero es obligatorio cuando ImpedimentoLegalAduanero es verdadero"
                )
            if not self.descripcion_impedimento_legal_aduanero:
                raise ValueError(
                    "DescripcionImpedimentoLegalAduanero es obligatorio cuando ImpedimentoLegalAduanero es verdadero"
                )
        return self


class DocumentoTransporte(BaseModel):
    """DocumentoTransporteType — unidad de Stock de Importación."""
    identificador_manifiesto: str
    identificador_documento_transporte: str
    consignatario: int
    procedencia_mercaderia: str
    fecha_ingreso_deposito: datetime
    condicion_mercaderia: str  # Buena | Mala
    ubicacion_partida: str
    condicion_imo: bool
    numero_imo: Optional[str] = None  # obligatorio si condicion_imo=True
    impedimento_legal_aduanero: bool
    tipo_impedimento_legal_aduanero: Optional[str] = None   # obligatorio si impedimento=True
    descripcion_impedimento_legal_aduanero: Optional[str] = None  # obligatorio si impedimento=True
    observaciones: Optional[str] = None
    lineas_mercaderia: list[LineaMercaderia] = Field(default_factory=list)
    contenedores: list[ContenedorAsociado] = Field(default_factory=list)

    @model_validator(mode="after")
    def _validar_campos_condicionales(self) -> "DocumentoTransporte":
        if self.condicion_imo and not self.numero_imo:
            raise ValueError("NumeroImo es obligatorio cuando CondicionImo es verdadero")
        if self.impedimento_legal_aduanero:
            if not self.tipo_impedimento_legal_aduanero:
                raise ValueError(
                    "TipoImpedimentoLegalAduanero es obligatorio cuando ImpedimentoLegalAduanero es verdadero"
                )
            if not self.descripcion_impedimento_legal_aduanero:
                raise ValueError(
                    "DescripcionImpedimentoLegalAduanero es obligatorio cuando ImpedimentoLegalAduanero es verdadero"
                )
        return self


class RegistrarStockRequest(BaseModel):
    """
    Parámetros completos para el método RegistrarStock.

    IMPORTANTE: id_transaccion debe ser único por invocación. Si se reenvía
    el mismo id ante un timeout, el WS retorna la respuesta original sin
    reprocesar (idempotencia por diseño de AFIP).
    """
    id_transaccion: str
    codigo_aduana: str
    codigo_lugar_operativo: str
    fecha_stock: datetime
    stock_exportacion: list[PermisoEmbarque] = Field(default_factory=list)
    stock_importacion: list[DocumentoTransporte] = Field(default_factory=list)
    contenedores_vacios: list[ContenedorVacio] = Field(default_factory=list)


class ErrorItem(BaseModel):
    codigo: int
    descripcion: str


class RegistrarStockResponse(BaseModel):
    mensaje_aceptado: bool
    server: Optional[str] = None
    timestamp: Optional[datetime] = None
    errores: list[ErrorItem] = Field(default_factory=list)


class DummyResponse(BaseModel):
    appserver: str
    dbserver: str
    authserver: str
