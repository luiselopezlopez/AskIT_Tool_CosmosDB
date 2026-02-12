import unittest
from unittest.mock import Mock, patch, MagicMock, call
import json
from app import app


class TestFlaskApp(unittest.TestCase):
    def setUp(self):
        """Configurar el cliente de prueba para Flask"""
        self.app = app
        self.client = self.app.test_client()
        self.app.testing = True

    def test_health_endpoint(self):
        """Test del endpoint /health"""
        response = self.client.get('/health')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertIn('status', data)
        self.assertEqual(data['status'], 'healthy')
        self.assertIn('cosmos_configured', data)

    def test_swagger_json_endpoint(self):
        """Test del endpoint /swagger.json"""
        response = self.client.get('/swagger.json')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        # Verificar que la especificación OpenAPI contiene la información básica
        self.assertIn('info', data)
        self.assertIn('title', data['info'])
        self.assertEqual(data['info']['title'], 'AskIT Tool CosmosDB API')
        # Verificar que contiene los endpoints
        self.assertIn('paths', data)
        self.assertIn('/query', data['paths'])
        self.assertIn('/health', data['paths'])

    def test_swagger_ui_endpoint(self):
        """Test del endpoint /swagger (Swagger UI)"""
        response = self.client.get('/swagger')
        self.assertEqual(response.status_code, 200)
        # Verificar que retorna HTML
        self.assertIn('text/html', response.content_type)
        # Verificar que contiene elementos de Swagger UI
        html_content = response.data.decode('utf-8')
        self.assertIn('swagger', html_content.lower())

    @patch('app.cosmos_client', None)
    @patch('app.COSMOS_DATABASE', None)
    def test_query_endpoint_without_cosmos_config(self):
        """Test del endpoint /query sin configuración de CosmosDB"""
        response = self.client.post('/query',
                                   data=json.dumps({
                                       'contenedor': 'test',
                                       'query': 'SELECT * FROM c'
                                   }),
                                   content_type='application/json')
        self.assertEqual(response.status_code, 500)
        data = json.loads(response.data)
        self.assertIn('error', data)

    def test_query_endpoint_missing_contenedor(self):
        """Test del endpoint /query sin el parámetro contenedor"""
        response = self.client.post('/query',
                                   data=json.dumps({
                                       'query': 'SELECT * FROM c'
                                   }),
                                   content_type='application/json')
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.data)
        self.assertIn('error', data)
        self.assertIn('contenedor', data['error'])

    def test_query_endpoint_missing_query(self):
        """Test del endpoint /query sin el parámetro query"""
        response = self.client.post('/query',
                                   data=json.dumps({
                                       'contenedor': 'test'
                                   }),
                                   content_type='application/json')
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.data)
        self.assertIn('error', data)
        self.assertIn('query', data['error'])

    def test_query_endpoint_invalid_json(self):
        """Test del endpoint /query con JSON inválido"""
        response = self.client.post('/query',
                                   data='invalid json',
                                   content_type='application/json')
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.data)
        self.assertIn('error', data)

    @patch('app.cosmos_client')
    @patch('app.COSMOS_DATABASE', 'test_database')
    def test_query_endpoint_success(self, mock_cosmos_client):
        """Test del endpoint /query con ejecución exitosa"""
        # Configurar mocks
        mock_database = MagicMock()
        mock_container = MagicMock()
        mock_cosmos_client.get_database_client.return_value = mock_database
        mock_database.get_container_client.return_value = mock_container
        
        # Simular respuesta de CosmosDB
        mock_items = [
            {'id': '1', 'name': 'Item 1'},
            {'id': '2', 'name': 'Item 2'}
        ]
        mock_container.query_items.return_value = iter(mock_items)
        
        response = self.client.post('/query',
                                   data=json.dumps({
                                       'contenedor': 'test_container',
                                       'query': 'SELECT * FROM c'
                                   }),
                                   content_type='application/json')
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertTrue(data['success'])
        self.assertEqual(data['count'], 2)
        self.assertEqual(len(data['results']), 2)
        self.assertEqual(data['results'][0]['id'], '1')

    @patch('app.cosmos_client')
    @patch('app.COSMOS_DATABASE', 'test_database')
    def test_query_endpoint_resource_not_found(self, mock_cosmos_client):
        """Test del endpoint /query cuando el contenedor no existe"""
        from azure.cosmos import exceptions
        
        # Configurar mocks
        mock_database = MagicMock()
        mock_container = MagicMock()
        mock_cosmos_client.get_database_client.return_value = mock_database
        mock_database.get_container_client.return_value = mock_container
        
        # Simular error de recurso no encontrado
        mock_container.query_items.side_effect = exceptions.CosmosResourceNotFoundError(
            message="Container not found"
        )
        
        response = self.client.post('/query',
                                   data=json.dumps({
                                       'contenedor': 'nonexistent_container',
                                       'query': 'SELECT * FROM c'
                                   }),
                                   content_type='application/json')
        
        self.assertEqual(response.status_code, 404)
        data = json.loads(response.data)
        self.assertIn('error', data)
        self.assertIn('Recurso no encontrado', data['error'])

    @patch('app.cosmos_client')
    @patch('app.COSMOS_DATABASE', 'test_database')
    def test_query_endpoint_cosmos_http_error(self, mock_cosmos_client):
        """Test del endpoint /query con error HTTP de CosmosDB"""
        from azure.cosmos import exceptions
        
        # Configurar mocks
        mock_database = MagicMock()
        mock_container = MagicMock()
        mock_cosmos_client.get_database_client.return_value = mock_database
        mock_database.get_container_client.return_value = mock_container
        
        # Simular error HTTP de Cosmos
        mock_container.query_items.side_effect = exceptions.CosmosHttpResponseError(
            message="Query syntax error"
        )
        
        response = self.client.post('/query',
                                   data=json.dumps({
                                       'contenedor': 'test_container',
                                       'query': 'INVALID QUERY'
                                   }),
                                   content_type='application/json')
        
        self.assertEqual(response.status_code, 500)
        data = json.loads(response.data)
        self.assertIn('error', data)
        self.assertIn('Error en la consulta de CosmosDB', data['error'])

    @patch('app.logger')
    @patch('app.cosmos_client')
    @patch('app.COSMOS_DATABASE', 'test_database')
    def test_query_endpoint_logs_telemetry_on_success(self, mock_cosmos_client, mock_logger):
        """Test que verifica que se registra telemetría en consulta exitosa"""
        # Configurar mocks
        mock_database = MagicMock()
        mock_container = MagicMock()
        mock_cosmos_client.get_database_client.return_value = mock_database
        mock_database.get_container_client.return_value = mock_container
        
        # Simular respuesta de CosmosDB
        mock_items = [{'id': '1', 'name': 'Item 1'}]
        mock_container.query_items.return_value = iter(mock_items)
        
        response = self.client.post('/query',
                                   data=json.dumps({
                                       'contenedor': 'test_container',
                                       'query': 'SELECT * FROM c'
                                   }),
                                   content_type='application/json')
        
        self.assertEqual(response.status_code, 200)
        # Verificar que se llamó al logger para registrar la solicitud
        self.assertTrue(mock_logger.info.called)
        # Verificar que se registró la recepción de la solicitud
        info_calls = [str(call) for call in mock_logger.info.call_args_list]
        self.assertTrue(any('Solicitud recibida' in str(call) for call in info_calls))
        self.assertTrue(any('exitosamente' in str(call) for call in info_calls))

    @patch('app.logger')
    def test_query_endpoint_logs_telemetry_on_error(self, mock_logger):
        """Test que verifica que se registra telemetría en errores"""
        response = self.client.post('/query',
                                   data=json.dumps({
                                       'contenedor': 'test'
                                   }),
                                   content_type='application/json')
        
        self.assertEqual(response.status_code, 400)
        # Verificar que se llamó al logger
        self.assertTrue(mock_logger.info.called or mock_logger.warning.called)

    @patch('app.logger')
    def test_health_endpoint_logs_telemetry(self, mock_logger):
        """Test que verifica que se registra telemetría en health check"""
        response = self.client.get('/health')
        self.assertEqual(response.status_code, 200)
        # Verificar que se llamó al logger
        self.assertTrue(mock_logger.info.called)
        # Verificar que se registró el health check
        info_calls = [str(call) for call in mock_logger.info.call_args_list]
        self.assertTrue(any('Health check' in str(call) for call in info_calls))


if __name__ == '__main__':
    unittest.main()
