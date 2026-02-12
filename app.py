import os
import logging
from flask import Flask, request, jsonify
from azure.cosmos import CosmosClient, exceptions
from werkzeug.exceptions import BadRequest
from flasgger import Swagger
from opencensus.ext.azure.log_exporter import AzureLogHandler
from opencensus.ext.azure import metrics_exporter
from opencensus.ext.flask.flask_middleware import FlaskMiddleware
from opencensus.stats import aggregation as aggregation_module
from opencensus.stats import measure as measure_module
from opencensus.stats import stats as stats_module
from opencensus.stats import view as view_module
from opencensus.tags import tag_map as tag_map_module

app = Flask(__name__)

# Configurar Application Insights
APPINSIGHTS_CONNECTION_STRING = os.environ.get('APPLICATIONINSIGHTS_CONNECTION_STRING')
APPINSIGHTS_INSTRUMENTATION_KEY = os.environ.get('APPINSIGHTS_INSTRUMENTATION_KEY')

# Configurar logging con Application Insights si está configurado
if APPINSIGHTS_CONNECTION_STRING or APPINSIGHTS_INSTRUMENTATION_KEY:
    # Configurar el logger para enviar logs a Application Insights
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.INFO)
    
    # Crear el handler de Azure
    if APPINSIGHTS_CONNECTION_STRING:
        azure_handler = AzureLogHandler(connection_string=APPINSIGHTS_CONNECTION_STRING)
    else:
        azure_handler = AzureLogHandler(instrumentation_key=APPINSIGHTS_INSTRUMENTATION_KEY)
    
    logger.addHandler(azure_handler)
    
    # Configurar middleware de Flask para telemetría automática
    try:
        if APPINSIGHTS_CONNECTION_STRING:
            middleware = FlaskMiddleware(
                app,
                exporter=metrics_exporter.new_metrics_exporter(
                    connection_string=APPINSIGHTS_CONNECTION_STRING
                )
            )
        else:
            middleware = FlaskMiddleware(
                app,
                exporter=metrics_exporter.new_metrics_exporter(
                    instrumentation_key=APPINSIGHTS_INSTRUMENTATION_KEY
                )
            )
    except Exception as e:
        # Si hay algún error en la configuración del middleware, solo registrarlo
        print(f"Warning: No se pudo configurar Application Insights middleware: {e}")
        logger = None
else:
    logger = None

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
    # Registrar recepción de solicitud
    if logger:
        logger.info('Solicitud recibida en /query', extra={'custom_dimensions': {'endpoint': '/query'}})
    
    try:
        # Obtener datos del request
        data = request.get_json(force=False, silent=False)
        
        if not data:
            if logger:
                logger.warning('Solicitud con body JSON inválido', extra={'custom_dimensions': {'endpoint': '/query', 'error_type': 'invalid_json'}})
            return jsonify({'error': 'El body debe ser un JSON válido'}), 400
        
        contenedor = data.get('contenedor')
        query_sql = data.get('query')
        
        # Validar parámetros
        if not contenedor:
            if logger:
                logger.warning('Parámetro contenedor faltante', extra={'custom_dimensions': {'endpoint': '/query', 'error_type': 'missing_parameter', 'parameter': 'contenedor'}})
            return jsonify({'error': 'El parámetro "contenedor" es requerido'}), 400
        
        if not query_sql:
            if logger:
                logger.warning('Parámetro query faltante', extra={'custom_dimensions': {'endpoint': '/query', 'error_type': 'missing_parameter', 'parameter': 'query'}})
            return jsonify({'error': 'El parámetro "query" es requerido'}), 400
        
        # Validar que el cliente de Cosmos esté configurado
        if not cosmos_client:
            if logger:
                logger.error('CosmosDB no configurado', extra={'custom_dimensions': {'endpoint': '/query', 'error_type': 'configuration_error'}})
            return jsonify({
                'error': 'CosmosDB no está configurado correctamente. Verifica las variables de entorno.'
            }), 500
        
        if not COSMOS_DATABASE:
            if logger:
                logger.error('Base de datos CosmosDB no configurada', extra={'custom_dimensions': {'endpoint': '/query', 'error_type': 'configuration_error'}})
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
        
        # Registrar resultado exitoso
        if logger:
            logger.info('Consulta ejecutada exitosamente', extra={'custom_dimensions': {
                'endpoint': '/query',
                'contenedor': contenedor,
                'result_count': len(items),
                'success': True
            }})
        
        return jsonify({
            'success': True,
            'count': len(items),
            'results': items
        }), 200
        
    except BadRequest as e:
        if logger:
            logger.error('Error de solicitud inválida', extra={'custom_dimensions': {'endpoint': '/query', 'error_type': 'bad_request', 'error': str(e)}})
        return jsonify({
            'error': 'El body debe ser un JSON válido'
        }), 400
    except exceptions.CosmosResourceNotFoundError as e:
        if logger:
            logger.error('Recurso no encontrado en CosmosDB', extra={'custom_dimensions': {'endpoint': '/query', 'error_type': 'resource_not_found', 'error': str(e)}})
        return jsonify({
            'error': f'Recurso no encontrado: {str(e)}'
        }), 404
    except exceptions.CosmosHttpResponseError as e:
        if logger:
            logger.error('Error HTTP de CosmosDB', extra={'custom_dimensions': {'endpoint': '/query', 'error_type': 'cosmos_http_error', 'error': str(e)}})
        return jsonify({
            'error': f'Error en la consulta de CosmosDB: {str(e)}'
        }), 500
    except Exception as e:
        if logger:
            logger.error('Error interno del sistema', extra={'custom_dimensions': {'endpoint': '/query', 'error_type': 'internal_error', 'error': str(e)}}, exc_info=True)
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
    # Registrar solicitud de health check
    if logger:
        logger.info('Health check solicitado', extra={'custom_dimensions': {'endpoint': '/health'}})
    
    cosmos_configured = bool(cosmos_client and COSMOS_DATABASE)
    return jsonify({
        'status': 'healthy',
        'cosmos_configured': cosmos_configured
    }), 200


if __name__ == '__main__':
    debug_mode = os.environ.get('FLASK_DEBUG', 'False').lower() == 'true'
    app.run(host='0.0.0.0', port=5000, debug=debug_mode)
