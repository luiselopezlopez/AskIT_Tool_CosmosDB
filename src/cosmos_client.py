from typing import Any

from azure.cosmos import CosmosClient
from azure.cosmos.exceptions import CosmosHttpResponseError


class CosmosRepository:
    def __init__(self, connection_string: str, endpoint: str, key: str, database_name: str, container_name: str):
        if connection_string:
            self._client = CosmosClient.from_connection_string(connection_string)
        elif endpoint and key:
            self._client = CosmosClient(endpoint, credential=key)
        else:
            raise ValueError("Cosmos credentials are missing. Provide COSMOS_CONNECTION_STRING or COSMOS_ENDPOINT + COSMOS_KEY.")

        self._database = self._client.get_database_client(database_name)
        self._container = self._database.get_container_client(container_name)

    def get_item(self, item_id: str, partition_key: Any) -> dict:
        return self._container.read_item(item=item_id, partition_key=partition_key)

    def query_items(self, query: str, parameters: list[dict] | None = None, max_item_count: int = 50) -> list[dict]:
        items = self._container.query_items(
            query=query,
            parameters=parameters or [],
            enable_cross_partition_query=True,
            max_item_count=max_item_count,
        )
        return list(items)

    def upsert_item(self, item: dict) -> dict:
        return self._container.upsert_item(body=item)

    def patch_item(self, item_id: str, partition_key: Any, operations: list[dict]) -> dict:
        return self._container.patch_item(item=item_id, partition_key=partition_key, patch_operations=operations)

    def delete_item(self, item_id: str, partition_key: Any) -> dict:
        self._container.delete_item(item=item_id, partition_key=partition_key)
        return {"deleted": True, "id": item_id}


def safe_call(fn):
    try:
        return fn()
    except CosmosHttpResponseError as ex:
        raise RuntimeError(f"CosmosDB error: {ex.status_code} - {ex.message}") from ex
