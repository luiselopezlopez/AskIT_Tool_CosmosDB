import os
from flask import Flask, request, jsonify
from azure.cosmos import CosmosClient, exceptions
from werkzeug.exceptions import BadRequest

app = Flask(__name__)

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
    
    Parámetros esperados en el body JSON:
    - contenedor: nombre del contenedor en CosmosDB
    - query: consulta SQL a ejecutar
    
    Retorna:
    - 200: Lista de resultados de la consulta
    - 400: Error en los parámetros
    - 500: Error en la ejecución de la consulta
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
    """Endpoint de health check"""
    cosmos_configured = bool(cosmos_client and COSMOS_DATABASE)
    return jsonify({
        'status': 'healthy',
        'cosmos_configured': cosmos_configured
    }), 200


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
