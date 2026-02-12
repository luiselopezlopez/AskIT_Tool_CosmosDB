import unittest
from unittest.mock import Mock, patch, MagicMock
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


if __name__ == '__main__':
    unittest.main()
