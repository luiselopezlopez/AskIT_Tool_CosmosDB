import os
from flask import Flask, request, jsonify
from azure.cosmos import CosmosClient, exceptions
from werkzeug.exceptions import BadRequest
from flasgger import Swagger

app = Flask(__name__)

# Configuración de Swagger/OpenAPI 3.0
swagger_config = {
    "headers": [],
    "specs": [
        {
            "endpoint": 'swagger',
            "route": '/swagger.json',
            "rule_filter": lambda rule: True,
            "model_filter": lambda tag: True,
        }
    ],
    "static_url_path": "/flasgger_static",
    "swagger_ui": True,
    "specs_route": "/swagger",
    "openapi": "3.0.0"
}

swagger_template = {
    "openapi": "3.0.0",
    "info": {
        "title": "AskIT Tool CosmosDB API",
        "description": "API Flask para consultar una base de datos Azure CosmosDB",
        "version": "1.0.0",
        "contact": {
            "name": "API Support"
        }
    },
    "servers": [
        {
            "url": "/",
            "description": "API Server"
        }
    ]
}

swagger = Swagger(app, config=swagger_config, template=swagger_template)

# Configuración de CosmosDB desde variables de entorno
COSMOS_ENDPOINT = os.environ.get('COSMOS_DB_ENDPOINT')
COSMOS_KEY = os.environ.get('COSMOS_DB_KEY')
COSMOS_DATABASE = os.environ.get('COSMOS_DB_DATABASE')

# Inicializar cliente de CosmosDB
cosmos_client = None
if COSMOS_ENDPOINT and COSMOS_KEY:
    cosmos_client = CosmosClient(COSMOS_ENDPOINT, COSMOS_KEY)


@app.route('/query', methods=['POST'])
def query():
    """
    Endpoint POST /query para ejecutar consultas en CosmosDB.
    ---
    tags:
      - CosmosDB
    summary: Ejecutar consulta SQL en CosmosDB
    description: Ejecuta una consulta SQL contra un contenedor específico en Azure CosmosDB
    requestBody:
      required: true
      content:
        application/json:
          schema:
            type: object
            required:
              - contenedor
              - query
            properties:
              contenedor:
                type: string
                description: Nombre del contenedor en CosmosDB
                example: "usuarios"
              query:
                type: string
                description: Consulta SQL a ejecutar
                example: "SELECT * FROM c WHERE c.status = 'active'"
    responses:
      200:
        description: Consulta ejecutada exitosamente
        content:
          application/json:
            schema:
              type: object
              properties:
                success:
                  type: boolean
                  example: true
                count:
                  type: integer
                  example: 2
                results:
                  type: array
                  items:
                    type: object
                  example:
                    - id: "1"
                      name: "Item 1"
                      status: "active"
                    - id: "2"
                      name: "Item 2"
                      status: "active"
      400:
        description: Error en los parámetros de entrada
        content:
          application/json:
            schema:
              type: object
              properties:
                error:
                  type: string
                  example: "El parámetro 'contenedor' es requerido"
      404:
        description: Recurso no encontrado
        content:
          application/json:
            schema:
              type: object
              properties:
                error:
                  type: string
                  example: "Recurso no encontrado: Container not found"
      500:
        description: Error en la ejecución de la consulta
        content:
          application/json:
            schema:
              type: object
              properties:
                error:
                  type: string
                  example: "Error en la consulta de CosmosDB"
    """
    try:
        # Obtener datos del request
        data = request.get_json(force=False, silent=False)
        
        if not data:
            return jsonify({'error': 'El body debe ser un JSON válido'}), 400
        
        contenedor = data.get('contenedor')
        query_sql = data.get('query')
        
        # Validar parámetros
        if not contenedor:
            return jsonify({'error': 'El parámetro "contenedor" es requerido'}), 400
        
        if not query_sql:
            return jsonify({'error': 'El parámetro "query" es requerido'}), 400
        
        # Validar que el cliente de Cosmos esté configurado
        if not cosmos_client:
            return jsonify({
                'error': 'CosmosDB no está configurado correctamente. Verifica las variables de entorno.'
            }), 500
        
        if not COSMOS_DATABASE:
            return jsonify({
                'error': 'La base de datos de CosmosDB no está configurada.'
            }), 500
        
        # Obtener la base de datos y el contenedor
        database = cosmos_client.get_database_client(COSMOS_DATABASE)
        container = database.get_container_client(contenedor)
        
        # Ejecutar la consulta
        items = list(container.query_items(
            query=query_sql,
            enable_cross_partition_query=True
        ))
        
        return jsonify({
            'success': True,
            'count': len(items),
            'results': items
        }), 200
        
    except BadRequest as e:
        return jsonify({
            'error': 'El body debe ser un JSON válido'
        }), 400
    except exceptions.CosmosResourceNotFoundError as e:
        return jsonify({
            'error': f'Recurso no encontrado: {str(e)}'
        }), 404
    except exceptions.CosmosHttpResponseError as e:
        return jsonify({
            'error': f'Error en la consulta de CosmosDB: {str(e)}'
        }), 500
    except Exception as e:
        return jsonify({
            'error': f'Error interno: {str(e)}'
        }), 500


@app.route('/health', methods=['GET'])
def health():
    """
    Endpoint de health check
    ---
    tags:
      - Health
    summary: Verificar el estado de la aplicación
    description: Retorna el estado de la aplicación y si CosmosDB está configurado correctamente
    responses:
      200:
        description: Estado de la aplicación
        content:
          application/json:
            schema:
              type: object
              properties:
                status:
                  type: string
                  example: "healthy"
                cosmos_configured:
                  type: boolean
                  example: true
    """
    cosmos_configured = bool(cosmos_client and COSMOS_DATABASE)
    return jsonify({
        'status': 'healthy',
        'cosmos_configured': cosmos_configured
    }), 200


if __name__ == '__main__':
    debug_mode = os.environ.get('FLASK_DEBUG', 'False').lower() == 'true'
    app.run(host='0.0.0.0', port=5000, debug=debug_mode)
