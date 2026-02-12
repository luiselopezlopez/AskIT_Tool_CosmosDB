# AskIT Tool CosmosDB

API Flask para consultar una base de datos Azure CosmosDB.

## Descripción

Esta aplicación Flask proporciona un endpoint POST `/query` que permite ejecutar consultas SQL contra una base de datos Azure CosmosDB.

## Requisitos

- Python 3.12 o superior
- Azure CosmosDB Account
- Docker (opcional, para deployment en contenedores)

## Instalación

1. Clonar el repositorio:
```bash
git clone https://github.com/luiselopezlopez/AskIT_Tool_CosmosDB.git
cd AskIT_Tool_CosmosDB
```

2. Instalar dependencias:
```bash
pip install -r requirements.txt
```

3. Configurar variables de entorno:
```bash
cp .env.example .env
# Editar .env con tus credenciales de CosmosDB
```

## Configuración

La aplicación requiere las siguientes variables de entorno:

- `COSMOS_DB_ENDPOINT`: URL del endpoint de CosmosDB (e.g., `https://your-account.documents.azure.com:443/`)
- `COSMOS_DB_KEY`: Primary o Secondary Key de CosmosDB
- `COSMOS_DB_DATABASE`: Nombre de la base de datos en CosmosDB
- `FLASK_DEBUG`: (Opcional) Habilitar modo debug de Flask. Por defecto: `False`. **No usar `True` en producción**

### Application Insights (Opcional)

La aplicación incluye integración con Azure Application Insights para telemetría, métricas y logs. Para habilitarlo, configura una de las siguientes variables de entorno:

- `APPLICATIONINSIGHTS_CONNECTION_STRING`: (Recomendado) Connection string completo de Application Insights
  - Ejemplo: `InstrumentationKey=your-key;IngestionEndpoint=https://your-region.in.applicationinsights.azure.com/;LiveEndpoint=https://your-region.livediagnostics.monitor.azure.com/`
  - Puedes obtenerlo desde el portal de Azure en tu recurso de Application Insights
  
- `APPINSIGHTS_INSTRUMENTATION_KEY`: (Legacy) Solo la Instrumentation Key
  - Ejemplo: `your-instrumentation-key-here`

**Telemetría registrada:**
- Recepción de todas las solicitudes HTTP (automático)
- Resultado de consultas exitosas en CosmosDB
- Errores de validación (parámetros faltantes, JSON inválido)
- Errores de configuración de CosmosDB
- Errores de consulta en CosmosDB (recursos no encontrados, errores HTTP)
- Errores internos del sistema
- Health checks

Si no se configura Application Insights, la aplicación funcionará normalmente sin telemetría.

## Uso

### Opción 1: Ejecutar con Docker (Recomendado para Producción)

#### Construir la imagen

```bash
docker build -t askit-cosmosdb:latest .
```

#### Ejecutar el contenedor

```bash
docker run -d \
  --name askit-cosmosdb \
  -p 8000:8000 \
  -e COSMOS_DB_ENDPOINT="https://your-account.documents.azure.com:443/" \
  -e COSMOS_DB_KEY="your-primary-key" \
  -e COSMOS_DB_DATABASE="your-database" \
  askit-cosmosdb:latest
```

#### Configuración avanzada

El contenedor soporta las siguientes variables de entorno para configuración:

- **PORT** (default: 8000): Puerto en el que escucha la aplicación
- **GUNICORN_WORKERS** (default: 4): Número de procesos workers de Gunicorn
- **GUNICORN_THREADS** (default: 2): Número de threads por worker
- **COSMOS_DB_ENDPOINT**: URL del endpoint de CosmosDB (requerido)
- **COSMOS_DB_KEY**: Primary o Secondary Key de CosmosDB (requerido)
- **COSMOS_DB_DATABASE**: Nombre de la base de datos (requerido)
- **APPLICATIONINSIGHTS_CONNECTION_STRING**: Connection string de Application Insights (opcional)

Ejemplo con configuración personalizada:

```bash
docker run -d \
  --name askit-cosmosdb \
  -p 9000:9000 \
  -e PORT=9000 \
  -e GUNICORN_WORKERS=8 \
  -e GUNICORN_THREADS=4 \
  -e COSMOS_DB_ENDPOINT="https://your-account.documents.azure.com:443/" \
  -e COSMOS_DB_KEY="your-primary-key" \
  -e COSMOS_DB_DATABASE="your-database" \
  -e APPLICATIONINSIGHTS_CONNECTION_STRING="InstrumentationKey=..." \
  askit-cosmosdb:latest
```

#### Verificar el estado del contenedor

```bash
# Ver logs
docker logs askit-cosmosdb

# Verificar health
curl http://localhost:8000/health
```

### Opción 2: Ejecutar localmente con Python

#### Iniciar la aplicación

```bash
python app.py
```

La aplicación se ejecutará en `http://localhost:5000`

### Endpoints

#### OpenAPI/Swagger Documentation

La API cuenta con documentación interactiva generada automáticamente con OpenAPI 3.0:

- **GET /swagger.json**: Especificación OpenAPI en formato JSON
- **GET /swagger**: Interfaz Swagger UI para explorar y probar la API de forma interactiva

Accede a `http://localhost:5000/swagger` (o `http://localhost:8000/swagger` si usas Docker) para explorar la documentación interactiva de la API.

#### POST /query

Ejecuta una consulta SQL contra un contenedor en CosmosDB.

**Parámetros del body (JSON):**
- `contenedor` (string, requerido): Nombre del contenedor en CosmosDB
- `query` (string, requerido): Consulta SQL a ejecutar

**Ejemplo de uso:**

```bash
# Con Python local (puerto 5000)
curl -X POST http://localhost:5000/query \
  -H "Content-Type: application/json" \
  -d '{
    "contenedor": "mi-contenedor",
    "query": "SELECT * FROM c WHERE c.status = '\''active'\''"
  }'

# Con Docker (puerto 8000)
curl -X POST http://localhost:8000/query \
  -H "Content-Type: application/json" \
  -d '{
    "contenedor": "mi-contenedor",
    "query": "SELECT * FROM c WHERE c.status = '\''active'\''"
  }'
```

**Respuesta exitosa (200):**
```json
{
  "success": true,
  "count": 5,
  "results": [
    {
      "id": "1",
      "name": "Item 1",
      "status": "active"
    }
  ]
}
```

**Respuestas de error:**
- `400`: Parámetros faltantes o inválidos
- `404`: Contenedor no encontrado
- `500`: Error en la configuración o ejecución de la consulta

#### GET /health

Verifica el estado de la aplicación.

**Respuesta (200):**
```json
{
  "status": "healthy",
  "cosmos_configured": true
}
```

## Ejemplos de Consultas

### Obtener todos los documentos
```json
{
  "contenedor": "usuarios",
  "query": "SELECT * FROM c"
}
```

### Filtrar por campo
```json
{
  "contenedor": "usuarios",
  "query": "SELECT * FROM c WHERE c.edad > 18"
}
```

### Limitar resultados
```json
{
  "contenedor": "usuarios",
  "query": "SELECT TOP 10 * FROM c"
}
```

## Desarrollo

### Ejecutar en modo desarrollo

```bash
python app.py
```

### Estructura del proyecto

```
.
├── app.py              # Aplicación Flask principal
├── requirements.txt    # Dependencias Python
├── .env.example        # Plantilla de variables de entorno
├── Dockerfile          # Dockerfile multi-stage optimizado para producción
├── .dockerignore       # Archivos excluidos del build de Docker
└── README.md          # Este archivo
```

## Deployment en Producción

### Docker

La imagen Docker incluye las siguientes optimizaciones:

- **Multi-stage build**: Reduce el tamaño de la imagen final (aprox. 180MB)
- **Python 3.12-slim**: Imagen base oficial y ligera
- **Usuario no privilegiado**: Ejecuta la aplicación como usuario `appuser` para mayor seguridad
- **Gunicorn**: WSGI server de producción con soporte para múltiples workers y threads
- **Healthcheck**: Verificación automática del estado de la aplicación
- **Configuración flexible**: Puerto y workers configurables via variables de entorno

### Recomendaciones para producción

- Configurar Application Insights para monitoreo y telemetría
- Ajustar `GUNICORN_WORKERS` según los CPU cores disponibles (recomendado: 2-4 x cores)
- Usar proxy reverso (nginx/traefik) para SSL/TLS termination
- Implementar autenticación y autorización en los endpoints
- Configurar límites de recursos en el contenedor
- Usar secretos seguros para las credenciales de CosmosDB (Azure Key Vault, Docker secrets, etc.)

## Seguridad

- Nunca commitear el archivo `.env` con credenciales reales
- Usar variables de entorno para configuración sensible
- Limitar acceso a las credenciales de CosmosDB
- Considerar implementar autenticación para el endpoint

## Licencia

MIT
