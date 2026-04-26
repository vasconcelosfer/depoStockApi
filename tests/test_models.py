"""
Tests de validación de modelos Pydantic.
No requieren conexión a AFIP.
"""
from __future__ import annotations

from datetime import datetime, timezone

import pytest

from depo_stock.models import (
    ContenedorAsociado,
    ContenedorVacio,
    DocumentoTransporte,
    LineaMercaderia,
    PermisoEmbarque,
    RegistrarStockRequest,
)

NOW = datetime(2024, 6, 1, 12, 0, 0, tzinfo=timezone.utc)


def _make_linea() -> LineaMercaderia:
    return LineaMercaderia(tipo_embalaje="05", cantidad=1, peso_bruto=100)


def _make_contenedor() -> ContenedorAsociado:
    return ContenedorAsociado(
        tipo_contenedor="House",
        numero_contenedor="CMAU1267465",
        longitud_contenedor="20",
        cantidad_bultos=10,
    )


def _make_permiso(**overrides) -> PermisoEmbarque:
    base = dict(
        identificador_permiso="18001EC01000001N",
        exportador=33504932619,
        destino_mercaderia="203",
        destinatario_exterior="20040410024",
        fecha_ingreso_deposito=NOW,
        condicion_mercaderia="Buena",
        ubicacion_partida="Sector A",
        condicion_imo=False,
        impedimento_legal_aduanero=False,
        lineas_mercaderia=[_make_linea()],
        contenedores=[_make_contenedor()],
    )
    base.update(overrides)
    return PermisoEmbarque(**base)


def _make_doc_transporte(**overrides) -> DocumentoTransporte:
    base = dict(
        identificador_manifiesto="16033MANI000441P",
        identificador_documento_transporte="SPTURJORGEPRUE1",
        consignatario=30590428775,
        procedencia_mercaderia="200",
        fecha_ingreso_deposito=NOW,
        condicion_mercaderia="Buena",
        ubicacion_partida="Sector B",
        condicion_imo=False,
        impedimento_legal_aduanero=False,
        lineas_mercaderia=[_make_linea()],
    )
    base.update(overrides)
    return DocumentoTransporte(**base)


# ------------------------------------------------------------------
# PermisoEmbarque
# ------------------------------------------------------------------

class TestPermisoEmbarque:
    def test_valido_con_permiso(self):
        pe = _make_permiso()
        assert pe.identificador_permiso == "18001EC01000001N"

    def test_valido_con_remito(self):
        pe = _make_permiso(identificador_permiso=None, identificador_remito="REMITO-001")
        assert pe.identificador_remito == "REMITO-001"

    def test_falla_sin_permiso_ni_remito(self):
        with pytest.raises(Exception, match="IdentificadorPermiso o IdentificadorRemito"):
            _make_permiso(identificador_permiso=None)

    def test_falla_imo_sin_numero(self):
        with pytest.raises(Exception, match="NumeroImo"):
            _make_permiso(condicion_imo=True, numero_imo=None)

    def test_valido_imo_con_numero(self):
        pe = _make_permiso(condicion_imo=True, numero_imo="1")
        assert pe.numero_imo == "1"

    def test_falla_impedimento_sin_tipo(self):
        with pytest.raises(Exception, match="TipoImpedimentoLegalAduanero"):
            _make_permiso(
                impedimento_legal_aduanero=True,
                tipo_impedimento_legal_aduanero=None,
                descripcion_impedimento_legal_aduanero="desc",
            )

    def test_falla_impedimento_sin_descripcion(self):
        with pytest.raises(Exception, match="DescripcionImpedimentoLegalAduanero"):
            _make_permiso(
                impedimento_legal_aduanero=True,
                tipo_impedimento_legal_aduanero="causa judicial",
                descripcion_impedimento_legal_aduanero=None,
            )

    def test_valido_impedimento_completo(self):
        pe = _make_permiso(
            impedimento_legal_aduanero=True,
            tipo_impedimento_legal_aduanero="causa judicial",
            descripcion_impedimento_legal_aduanero="Descripción del hecho",
        )
        assert pe.impedimento_legal_aduanero is True


# ------------------------------------------------------------------
# DocumentoTransporte
# ------------------------------------------------------------------

class TestDocumentoTransporte:
    def test_valido(self):
        dt = _make_doc_transporte()
        assert dt.condicion_mercaderia == "Buena"

    def test_falla_imo_sin_numero(self):
        with pytest.raises(Exception, match="NumeroImo"):
            _make_doc_transporte(condicion_imo=True, numero_imo=None)


# ------------------------------------------------------------------
# RegistrarStockRequest
# ------------------------------------------------------------------

class TestRegistrarStockRequest:
    def test_request_solo_exportacion(self):
        req = RegistrarStockRequest(
            id_transaccion="TX-001",
            codigo_aduana="001",
            codigo_lugar_operativo="10057",
            fecha_stock=NOW,
            stock_exportacion=[_make_permiso()],
        )
        assert req.id_transaccion == "TX-001"
        assert len(req.stock_exportacion) == 1
        assert req.stock_importacion == []

    def test_request_con_contenedores_vacios(self):
        req = RegistrarStockRequest(
            id_transaccion="TX-002",
            codigo_aduana="001",
            codigo_lugar_operativo="10057",
            fecha_stock=NOW,
            contenedores_vacios=[
                ContenedorVacio(
                    fecha_ingreso_deposito=NOW,
                    numero_contenedor="FSCU3560768",
                    longitud_contenedor="20",
                )
            ],
        )
        assert len(req.contenedores_vacios) == 1

    def test_request_completo(self):
        req = RegistrarStockRequest(
            id_transaccion="TX-003",
            codigo_aduana="033",
            codigo_lugar_operativo="10057",
            fecha_stock=NOW,
            stock_exportacion=[_make_permiso()],
            stock_importacion=[_make_doc_transporte()],
            contenedores_vacios=[
                ContenedorVacio(
                    fecha_ingreso_deposito=NOW,
                    numero_contenedor="TRIU5555556",
                    longitud_contenedor="25",
                )
            ],
        )
        assert len(req.stock_exportacion) == 1
        assert len(req.stock_importacion) == 1
        assert len(req.contenedores_vacios) == 1
