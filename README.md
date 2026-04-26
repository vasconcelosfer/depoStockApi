# DepoStock API

Cliente Python y REST API para el WebService **wgesStockDepositosFiscales** de **ARCA/AFIP**.  
Permite registrar el stock de depósitos fiscales aduaneros desde cualquier sistema (Odoo, ERPs, scripts, etc.) sin implementar SOAP directamente.

---

## Tabla de contenidos

- [Descripción](#descripción)
- [Arquitectura](#arquitectura)
- [Requisitos](#requisitos)
- [Instalación](#instalación)
- [Configuración](#configuración)
- [Uso como librería Python](#uso-como-librería-python)
  - [Autenticación WSAA](#autenticación-wsaa)
  - [Verificar estado del servicio (Dummy)](#verificar-estado-del-servicio-dummy)
  - [Registrar Stock](#registrar-stock)
  - [Integración con Odoo](#integración-con-odoo)
- [Uso como REST API](#uso-como-rest-api)
  - [Iniciar el servidor](#iniciar-el-servidor)
  - [Endpoints](#endpoints)
  - [Ejemplos con curl](#ejemplos-con-curl)
- [Modelos de datos](#modelos-de-datos)
- [Códigos de error AFIP](#códigos-de-error-afip)
- [Tests](#tests)
- [Obtener certificado digital AFIP](#obtener-certificado-digital-afip)

---

## Descripción

El WebService `wgesStockDepositosFiscales` es un servicio SOAP de **ARCA** (ex AFIP) que permite a los **depositarios fiscales** (tipo de agente `DEPO`) reportar el stock de mercadería en sus depósitos aduaneros.

En una misma invocación se declara **todo el stock del depósito** en una fecha dada:

- **Stock de Exportación** — permisos de embarque con mercadería en espera de exportar.
- **Stock de Importación** — documentos de transporte con mercadería importada en depósito.
- **Contenedores Vacíos** — contenedores sin carga presentes en el depósito.

> **Importante:** El WS no admite rectificaciones. Cada declaración de stock es definitiva.

### URLs del servicio

| Ambiente | URL |
|----------|-----|
| Homologación (testing) | `https://wsaduhomoext.afip.gob.ar/diav2/wgesstockdepositosfiscales/wgesstockdepositosfiscales.asmx` |
| Producción | `https://webservicesadu.afip.gob.ar/diav2/wgesStockDepositosFiscales/wgesStockDepositosFiscales.asmx` |

---

## Arquitectura

```
depoStockApi/
├── src/
│   └── depo_stock/              # Paquete Python instalable vía pip
│       ├── __init__.py          # Exports públicos
│       ├── wsaa.py              # Cliente WSAA (autenticación AFIP)
│       ├── client.py            # Cliente SOAP wgesStockDepositosFiscales
│       ├── models.py            # Modelos Pydantic con validaciones de negocio
│       └── exceptions.py        # Excepciones tipadas
│
├── api/                         # REST API JSON (FastAPI)
│   ├── main.py                  # Aplicación FastAPI
│   ├── deps.py                  # Inyección de dependencias (singleton del cliente)
│   └── routes/
│       ├── health.py            # GET /health  → llama Dummy
│       └── stock.py             # POST /stock  → llama RegistrarStock
│
├── tests/
│   └── test_models.py           # Tests de validaciones de negocio
│
├── docs/                        # Documentación oficial ARCA/AFIP
│   ├── Manual-Desarrollador.pdf
│   └── Manual-Usuario-Externo.pdf
│
├── pyproject.toml
└── .env.example
```

**Dos formas de uso:**

1. **Librería Python** — instalar con pip e importar directamente en Odoo u otro proyecto Python.
2. **REST API** — levantar el servidor FastAPI y consumirlo via HTTP/JSON desde cualquier lenguaje o sistema.

---

## Requisitos

- Python 3.10+
- Certificado digital X.509 emitido por AFIP para el CUIT del depositario
- CUIT habilitado como tipo de agente `DEPO` en AFIP

---

## Instalación

```bash
# Clonar el repositorio
git clone <repo-url>
cd depoStockApi

# Crear entorno virtual
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
# .venv\Scripts\activate   # Windows

# Instalar dependencias
pip install -e .

# Para desarrollo (incluye pytest, httpx)
pip install -e ".[dev]"
```

---

## Configuración

Copiar el archivo de ejemplo y completar los valores:

```bash
cp .env.example .env
```

| Variable | Descripción | Requerida |
|----------|-------------|-----------|
| `CUIT` | CUIT del depositario fiscal (sin guiones) | Sí |
| `CERT_PATH` | Ruta al certificado X.509 en formato PEM | Sí |
| `KEY_PATH` | Ruta a la clave privada RSA en formato PEM | Sí |
| `PRODUCTION` | `false` = homologación, `true` = producción | No (default: `false`) |
| `TIPO_AGENTE` | Tipo de agente AFIP | No (default: `DEPO`) |
| `ROL` | Rol del usuario | No (default: `DEPO`) |
| `API_KEY` | Clave para proteger los endpoints REST | No |

```bash
# .env
CUIT=20123456789
CERT_PATH=/ruta/al/certificado.crt
KEY_PATH=/ruta/a/la/clave_privada.key
PRODUCTION=false
API_KEY=mi-clave-secreta
```

---

## Uso como librería Python

### Autenticación WSAA

El `WSAAClient` gestiona automáticamente el ciclo de vida del token: lo obtiene al primer uso y lo renueva 2 horas antes de que venza (vigencia de 12 horas).

```python
from depo_stock import WSAAClient

wsaa = WSAAClient(
    cert_path="/ruta/certificado.crt",
    key_path="/ruta/clave.key",
    production=False,  # True para producción
)

# El token se cachea automáticamente
token = wsaa.get_token()
print(token.token)
print(token.sign)
print(token.expiration)
```

### Verificar estado del servicio (Dummy)

```python
from depo_stock import WSAAClient, DepoStockClient

wsaa = WSAAClient("cert.crt", "clave.key")
client = DepoStockClient(cuit="20123456789", wsaa_client=wsaa)

resp = client.dummy()
print(resp.appserver)   # "OK" o "NO"
print(resp.dbserver)    # "OK" o "NO"
print(resp.authserver)  # "OK" o "NO"
```

### Registrar Stock

```python
from datetime import datetime, timezone
from depo_stock import (
    WSAAClient,
    DepoStockClient,
    RegistrarStockRequest,
    PermisoEmbarque,
    DocumentoTransporte,
    ContenedorVacio,
    ContenedorAsociado,
    LineaMercaderia,
)

wsaa = WSAAClient("cert.crt", "clave.key")
client = DepoStockClient(cuit="20123456789", wsaa_client=wsaa)

request = RegistrarStockRequest(
    id_transaccion="TX-20240601-001",   # debe ser único por invocación
    codigo_aduana="033",
    codigo_lugar_operativo="10057",
    fecha_stock=datetime(2024, 6, 1, tzinfo=timezone.utc),

    # Stock de Exportación
    stock_exportacion=[
        PermisoEmbarque(
            identificador_permiso="18001EC01000001N",
            exportador=33504932619,
            destino_mercaderia="203",
            destinatario_exterior="20040410024",
            fecha_ingreso_deposito=datetime(2024, 5, 13, 10, 0, tzinfo=timezone.utc),
            condicion_mercaderia="Buena",   # "Buena" | "Mala"
            ubicacion_partida="Sector A - Nave 3",
            condicion_imo=True,
            numero_imo="1",                 # obligatorio si condicion_imo=True
            impedimento_legal_aduanero=False,
            observaciones="Sin novedades",
            lineas_mercaderia=[
                LineaMercaderia(tipo_embalaje="05", cantidad=10, peso_bruto=2000),
            ],
            contenedores=[
                ContenedorAsociado(
                    tipo_contenedor="House",    # "House" | "Pier" | "Correo"
                    numero_contenedor="CMAU1267465",
                    longitud_contenedor="20",
                    cantidad_bultos=10,
                ),
            ],
        ),
    ],

    # Stock de Importación
    stock_importacion=[
        DocumentoTransporte(
            identificador_manifiesto="16033MANI000441P",
            identificador_documento_transporte="SPTURJORGEPRUE1",
            consignatario=30590428775,
            procedencia_mercaderia="200",
            fecha_ingreso_deposito=datetime(2024, 4, 23, 18, 37, tzinfo=timezone.utc),
            condicion_mercaderia="Mala",
            ubicacion_partida="Sector B",
            condicion_imo=False,
            impedimento_legal_aduanero=True,
            tipo_impedimento_legal_aduanero="causa judicial",
            descripcion_impedimento_legal_aduanero="Embargo preventivo expediente X",
            lineas_mercaderia=[
                LineaMercaderia(tipo_embalaje="05", cantidad=1, peso_bruto=100),
            ],
        ),
    ],

    # Contenedores vacíos
    contenedores_vacios=[
        ContenedorVacio(
            fecha_ingreso_deposito=datetime(2024, 4, 25, tzinfo=timezone.utc),
            numero_contenedor="TRIU5555556",
            longitud_contenedor="25",
        ),
    ],
)

response = client.registrar_stock(request)

if response.mensaje_aceptado:
    print("Stock registrado correctamente")
else:
    for error in response.errores:
        print(f"Error {error.codigo}: {error.descripcion}")
```

> **Idempotencia por timeout:** Si no se recibe respuesta por timeout, reenviar exactamente el mismo mensaje con el **mismo `id_transaccion`**. El WS devuelve la respuesta original sin reprocesar. Usar un `id_transaccion` diferente generaría una segunda transacción duplicada.

### Integración con Odoo

Instalar el paquete en el entorno Python de Odoo:

```bash
# Desde el directorio del repo
pip install -e /ruta/al/depoStockApi

# O empaquetar y distribuir
pip install depo-stock
```

Luego usarlo en un módulo Odoo:

```python
# En un modelo o wizard de Odoo
from odoo import models, fields
from depo_stock import WSAAClient, DepoStockClient, RegistrarStockRequest

class DepositoFiscalWizard(models.TransientModel):
    _name = "deposito.fiscal.wizard"

    def action_registrar_stock(self):
        config = self.env["ir.config_parameter"].sudo()
        wsaa = WSAAClient(
            cert_path=config.get_param("afip.cert_path"),
            key_path=config.get_param("afip.key_path"),
            production=config.get_param("afip.production") == "True",
        )
        client = DepoStockClient(
            cuit=config.get_param("afip.cuit"),
            wsaa_client=wsaa,
        )
        # Construir y enviar el request con datos del depósito...
        response = client.registrar_stock(RegistrarStockRequest(...))
        return response
```

---

## Uso como REST API

### Iniciar el servidor

```bash
# Configurar variables de entorno
cp .env.example .env && nano .env

# Levantar servidor de desarrollo
PYTHONPATH=src uvicorn api.main:app --reload --port 8000

# Producción (con múltiples workers)
PYTHONPATH=src uvicorn api.main:app --host 0.0.0.0 --port 8000 --workers 4
```

La documentación interactiva estará disponible en:
- **Swagger UI:** `http://localhost:8000/docs`
- **ReDoc:** `http://localhost:8000/redoc`

### Endpoints

| Método | Ruta | Descripción |
|--------|------|-------------|
| `GET` | `/health` | Verifica el estado de ARCA/AFIP (Dummy) |
| `POST` | `/stock` | Registra el stock del depósito |

Todos los endpoints requieren el header `X-API-Key` si la variable `API_KEY` está configurada.

### Ejemplos con curl

**Verificar estado:**

```bash
curl -X GET http://localhost:8000/health \
  -H "X-API-Key: mi-clave-secreta"
```

```json
{
  "appserver": "OK",
  "dbserver": "OK",
  "authserver": "OK"
}
```

**Registrar stock:**

```bash
curl -X POST http://localhost:8000/stock \
  -H "Content-Type: application/json" \
  -H "X-API-Key: mi-clave-secreta" \
  -d '{
    "id_transaccion": "TX-20240601-001",
    "codigo_aduana": "033",
    "codigo_lugar_operativo": "10057",
    "fecha_stock": "2024-06-01T00:00:00+00:00",
    "stock_exportacion": [
      {
        "identificador_permiso": "18001EC01000001N",
        "exportador": 33504932619,
        "destino_mercaderia": "203",
        "destinatario_exterior": "20040410024",
        "fecha_ingreso_deposito": "2024-05-13T10:00:00+00:00",
        "condicion_mercaderia": "Buena",
        "ubicacion_partida": "Sector A",
        "condicion_imo": false,
        "impedimento_legal_aduanero": false,
        "lineas_mercaderia": [
          {"tipo_embalaje": "05", "cantidad": 1, "peso_bruto": 1000}
        ],
        "contenedores": [
          {
            "tipo_contenedor": "House",
            "numero_contenedor": "CMAU1267465",
            "longitud_contenedor": "20",
            "cantidad_bultos": 10
          }
        ]
      }
    ],
    "stock_importacion": [],
    "contenedores_vacios": []
  }'
```

```json
{
  "mensaje_aceptado": true,
  "server": "10.30.32.108",
  "timestamp": "2024-06-01T16:08:20-03:00",
  "errores": []
}
```

---

## Modelos de datos

### RegistrarStockRequest

| Campo | Tipo | Req. | Descripción |
|-------|------|------|-------------|
| `id_transaccion` | string | Sí | Identificador único por invocación |
| `codigo_aduana` | string | Sí | Código de aduana (ej: `"033"`) |
| `codigo_lugar_operativo` | string | Sí | Código LOT asignado por AFIP |
| `fecha_stock` | datetime | Sí | Fecha de declaración del stock |
| `stock_exportacion` | lista | No | Permisos de embarque (exportación) |
| `stock_importacion` | lista | No | Documentos de transporte (importación) |
| `contenedores_vacios` | lista | No | Contenedores vacíos en el depósito |

### PermisoEmbarque (Stock de Exportación)

| Campo | Tipo | Req. | Descripción |
|-------|------|------|-------------|
| `identificador_permiso` | string | (1) | ID del permiso de embarque |
| `identificador_remito` | string | (1) | ID del remito |
| `exportador` | int | Sí | CUIT del exportador |
| `destino_mercaderia` | string | Sí | Código de país destino |
| `destinatario_exterior` | string | Sí | Identificador del destinatario |
| `fecha_ingreso_deposito` | datetime | Sí | Fecha de ingreso al depósito |
| `condicion_mercaderia` | string | Sí | `"Buena"` o `"Mala"` |
| `ubicacion_partida` | string | Sí | Ubicación física en el depósito |
| `condicion_imo` | bool | Sí | Si tiene condición IMO |
| `numero_imo` | string | (2) | Número IMO (obligatorio si `condicion_imo=true`) |
| `impedimento_legal_aduanero` | bool | Sí | Si tiene impedimento legal |
| `tipo_impedimento_legal_aduanero` | string | (3) | Tipo de impedimento |
| `descripcion_impedimento_legal_aduanero` | string | (3) | Descripción del impedimento |
| `observaciones` | string | No | Texto libre |
| `lineas_mercaderia` | lista | No | Líneas de mercadería |
| `contenedores` | lista | No | Contenedores asociados |

(1) Se debe informar al menos uno: `identificador_permiso` o `identificador_remito`.  
(2) Obligatorio cuando `condicion_imo = true`.  
(3) Obligatorio cuando `impedimento_legal_aduanero = true`.

### DocumentoTransporte (Stock de Importación)

| Campo | Tipo | Req. | Descripción |
|-------|------|------|-------------|
| `identificador_manifiesto` | string | Sí | ID del manifiesto |
| `identificador_documento_transporte` | string | Sí | ID del documento de transporte |
| `consignatario` | int | Sí | CUIT del consignatario |
| `procedencia_mercaderia` | string | Sí | Código de país de procedencia |
| `fecha_ingreso_deposito` | datetime | Sí | Fecha de ingreso al depósito |
| `condicion_mercaderia` | string | Sí | `"Buena"` o `"Mala"` |
| `ubicacion_partida` | string | Sí | Ubicación en el depósito |
| `condicion_imo` | bool | Sí | Si tiene condición IMO |
| `numero_imo` | string | (1) | Número IMO |
| `impedimento_legal_aduanero` | bool | Sí | Si tiene impedimento legal |
| `tipo_impedimento_legal_aduanero` | string | (2) | Tipo de impedimento |
| `descripcion_impedimento_legal_aduanero` | string | (2) | Descripción |
| `observaciones` | string | No | Texto libre |
| `lineas_mercaderia` | lista | No | Líneas de mercadería |
| `contenedores` | lista | No | Contenedores asociados |

### ContenedorAsociado

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `tipo_contenedor` | string | `"House"`, `"Pier"` o `"Correo"` |
| `numero_contenedor` | string | Número del contenedor |
| `longitud_contenedor` | string | Longitud en pies (ej: `"20"`, `"40"`) |
| `cantidad_bultos` | int | Cantidad de bultos (opcional) |

### LineaMercaderia

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `tipo_embalaje` | string | Código de tipo de embalaje (ej: `"05"`) |
| `cantidad` | int | Cantidad de bultos |
| `peso_bruto` | int | Peso bruto en kg |

### ContenedorVacio

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `fecha_ingreso_deposito` | datetime | Fecha de ingreso al depósito |
| `numero_contenedor` | string | Número del contenedor |
| `longitud_contenedor` | string | Longitud en pies |

---

## Códigos de error AFIP

### Errores de autenticación

| Código | Descripción |
|--------|-------------|
| 6003 | Validación de conexión no coincide con opciones seleccionadas |
| 6005 | CUIT/CUIL y/o tipo de agente inválido para el servicio |
| 6006 | Rol inválido para el tipo de agente |
| 7004 | Error interno del servidor |
| 7005 | Token no vigente o caducado |
| 7006 | Debe ingresar la firma |
| 7007 | Debe ingresar el token |
| 7008 | Token inválido |
| 7013 | El servicio no se corresponde con el informado en el token |
| 7014 | CUIT con el que desea operar no informado |

### Errores de negocio (RegistrarStock)

| Código | Descripción |
|--------|-------------|
| 0 | OK — procesado correctamente |
| 101 | Errores asociados a los parámetros remitidos (CUIT mal formado, datos nulos, etc.) |
| 102 | Errores de negocio (ATA no vigente, manifiesto no encontrado, etc.) |
| 3025 | La longitud máxima del campo fue superada |
| 10066 | Tipo de embalaje inválido |
| 10083 | La fecha no puede ser superior a la fecha del día |
| 10220 | Campo prohibido |
| 10277 | Medida del contenedor inválida |
| 10444 | La fecha debe ser X |
| 10782 | Lugar Operativo inexistente o fuera de vigencia |
| 10968 | La cantidad informada debe ser mayor que cero |
| 10989 | El título no pertenece al manifiesto |
| 11371 | Debe ingresar un contenedor con código de embalaje 05 |
| 19739 | No puede informar contenedores asociados sin embalajes tipo contenedor |
| 20319 | El estado de la Declaración no puede ser ese valor |
| 21248 | Declaración inexistente o inválida |
| 30163 | Código de aduana inexistente o no vigente |
| 30820 | Información duplicada o incoherente |
| 30963 | Código de país inexistente o no vigente |
| 31353 | El campo tiene un formato erróneo |
| 31712 | CUIT no habilitado como tipo de agente |
| 42034 | Falta dato obligatorio |

---

## Tests

```bash
# Ejecutar todos los tests (no requieren conexión a AFIP)
pytest tests/ -v

# Con coverage
pytest tests/ -v --tb=short
```

Los tests cubren todas las validaciones de negocio definidas por AFIP:
- Presencia de `IdentificadorPermiso` o `IdentificadorRemito` (al menos uno)
- `NumeroImo` obligatorio cuando `CondicionImo = true`
- `TipoImpedimentoLegalAduanero` y `DescripcionImpedimentoLegalAduanero` obligatorios cuando `ImpedimentoLegalAduanero = true`
- Construcción correcta de requests completos

---

## Obtener certificado digital AFIP

Para operar con cualquier WS de AFIP se necesita un certificado X.509 vinculado al CUIT de la empresa.

1. **Generar clave privada y CSR:**
   ```bash
   openssl genrsa -out clave_privada.key 2048
   openssl req -new -key clave_privada.key -out solicitud.csr \
     -subj "/C=AR/O=MI EMPRESA SA/CN=mi-empresa/serialNumber=CUIT 20123456789"
   ```

2. **Solicitar el certificado** en el Administrador de Relaciones de AFIP con clave fiscal:
   - Ingresar a `https://auth.afip.gob.ar`
   - Ir a **Administrador de Relaciones** → **WSAA** → **Nueva relación**
   - Pegar el contenido del archivo `solicitud.csr`
   - Descargar el certificado emitido (`.crt`)

3. **Delegar el servicio** al CUIT que operará:
   - En el Administrador de Relaciones, agregar el servicio `wgesStockDepositosFiscales`
   - Asignar al CUIT del depositario con tipo de agente `DEPO`

4. Consultas sobre WSAA en homologación: `sri@afip.gob.ar`  
   Consultas funcionales: `dia_controlara@afip.gob.ar`

---

## Dependencias principales

| Paquete | Uso |
|---------|-----|
| `zeep` | Cliente SOAP para comunicarse con los WS de AFIP |
| `cryptography` | Firma PKCS7/CMS del TRA para autenticación WSAA |
| `pydantic` | Validación y serialización de modelos de datos |
| `fastapi` | Framework para la REST API |
| `uvicorn` | Servidor ASGI para FastAPI |
| `python-dotenv` | Gestión de variables de entorno |

---

## Licencia

MIT
