# CosmosDB Tools API (Azure Functions)

API HTTP para exponer tools de **Azure Cosmos DB** directamente como endpoints en **Azure Functions** (Python v2 programming model).

## Qué incluye

- Endpoint health: `GET /api/health`
- Endpoint catálogo de tools: `GET /api/tools`
- Endpoint directo: `POST /api/tools/cosmos_get_item`
- Endpoint directo: `POST /api/tools/cosmos_query_items`
- Endpoint directo: `POST /api/tools/cosmos_upsert_item`
- Endpoint directo: `POST /api/tools/cosmos_patch_item`
- Endpoint directo: `POST /api/tools/cosmos_delete_item`
- Tools CosmosDB:
  - `cosmos_get_item`
  - `cosmos_query_items`
  - `cosmos_upsert_item`
  - `cosmos_patch_item`
  - `cosmos_delete_item`

## Requisitos

- Python 3.10+
- Azure Functions Core Tools v4
- Azure Cosmos DB for NoSQL

## Variables de entorno

- `COSMOS_CONNECTION_STRING`
- `COSMOS_DATABASE_NAME`
- `COSMOS_CONTAINER_NAME`
- `LOG_LEVEL` (opcional, por ejemplo `INFO`)

Alternativa a connection string:

- `COSMOS_ENDPOINT`
- `COSMOS_KEY`
- `COSMOS_DATABASE_NAME`
- `COSMOS_CONTAINER_NAME`

## Ejecutar local

1. Crear y activar entorno virtual.
   - `python -m venv .venv`
   - `.venv\Scripts\Activate.ps1`
1. Instalar dependencias.
   - `pip install -r requirements.txt`
1. Definir configuración en `local.settings.json`.
1. Iniciar Functions host.
   - `func start --port 7071`
1. Endpoint local para listar tools.
    - `http://localhost:7071/api/tools`

## Probar endpoints por línea de comando

### PowerShell

- `tools/list`:
  - `Invoke-RestMethod -Uri "http://localhost:7071/api/tools" -Method Get | ConvertTo-Json -Depth 20`
- `cosmos_query_items`:
  - `Invoke-RestMethod -Uri "http://localhost:7071/api/tools/cosmos_query_items" -Method Post -ContentType "application/json" -Body '{"query":"SELECT TOP 1 * FROM c","maxItemCount":1}' | ConvertTo-Json -Depth 20`

## Probar desde Swagger UI

1. Levanta la Function localmente con `func start --port 7071`.
1. Abre Swagger UI en `http://localhost:7071/api/swagger`.
1. Si el endpoint está con `AuthLevel.Function`, pulsa `Authorize` y define el header `x-functions-key` con tu key.
1. Ejecuta directamente `GET /tools` o cualquiera de los endpoints `POST /tools/<tool_name>`.

OpenAPI JSON está disponible en `http://localhost:7071/api/openapi.json`.

## Desplegar como contenedor

1. Construir imagen:
   - `docker build -t cosmosdb-tools-functions:local .`
1. Ejecutar contenedor:
   - `docker run --rm -p 8080:80 -e AzureWebJobsStorage=UseDevelopmentStorage=true -e FUNCTIONS_WORKER_RUNTIME=python -e COSMOS_CONNECTION_STRING="<tu-connection-string>" -e COSMOS_DATABASE_NAME="<tu-db>" -e COSMOS_CONTAINER_NAME="<tu-container>" cosmosdb-tools-functions:local`
1. Endpoint tools en contenedor:
   - `http://localhost:8080/api/tools`

## Configuración en Foundry NEW (HTTP Tool)

1. Desplegar la Function App en Azure.
1. Endpoint base tools:
   - `https://<function-app>.azurewebsites.net/api/tools`
1. Configurar tools HTTP en Foundry usando cada endpoint directo.
1. Header requerido:
   - `x-functions-key: <function-key>`

## Logs en Application Insights

Azure Functions envía logs automáticamente a Application Insights cuando está configurada la app con:

- `APPLICATIONINSIGHTS_CONNECTION_STRING=<tu-connection-string>`

Consulta rápida (Logs):

```kusto
traces
| where timestamp > ago(30m)
| where message contains "Tool request"
| order by timestamp desc
```

## Notas

- `partitionKey` es obligatorio para `get`, `patch` y `delete`.
- Para producción, usa Managed Identity + RBAC (evita keys de larga vida).
