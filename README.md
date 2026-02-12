# AskIT Tool CosmosDB

API Flask para consultar una base de datos Azure CosmosDB.

## Descripción

Esta aplicación Flask proporciona un endpoint POST `/query` que permite ejecutar consultas SQL contra una base de datos Azure CosmosDB.

## Requisitos

- Python 3.8 o superior
- Azure CosmosDB Account

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

## Uso

### Iniciar la aplicación

```bash
python app.py
```

La aplicación se ejecutará en `http://localhost:5000`

### Endpoints

#### POST /query

Ejecuta una consulta SQL contra un contenedor en CosmosDB.

**Parámetros del body (JSON):**
- `contenedor` (string, requerido): Nombre del contenedor en CosmosDB
- `query` (string, requerido): Consulta SQL a ejecutar

**Ejemplo de uso:**

```bash
curl -X POST http://localhost:5000/query \
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
└── README.md          # Este archivo
```

## Seguridad

- Nunca commitear el archivo `.env` con credenciales reales
- Usar variables de entorno para configuración sensible
- Limitar acceso a las credenciales de CosmosDB
- Considerar implementar autenticación para el endpoint

## Licencia

MIT
