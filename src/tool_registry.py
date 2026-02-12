from typing import Any

from .cosmos_client import CosmosRepository, safe_call


def tool_definitions() -> list[dict]:
    return [
        {
            "name": "cosmos_get_item",
            "description": "Reads a Cosmos DB item by id and partition key.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "id": {"type": "string"},
                    "partitionKey": {},
                },
                "required": ["id", "partitionKey"],
            },
        },
        {
            "name": "cosmos_query_items",
            "description": "Executes a SQL query against the Cosmos DB container.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "query": {"type": "string"},
                    "parameters": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "name": {"type": "string"},
                                "value": {},
                            },
                            "required": ["name", "value"],
                        },
                    },
                    "maxItemCount": {"type": "integer", "minimum": 1, "maximum": 1000},
                },
                "required": ["query"],
            },
        },
        {
            "name": "cosmos_upsert_item",
            "description": "Creates or updates a Cosmos DB item.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "item": {"type": "object"},
                },
                "required": ["item"],
            },
        },
        {
            "name": "cosmos_patch_item",
            "description": "Applies JSON patch operations to an item.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "id": {"type": "string"},
                    "partitionKey": {},
                    "operations": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "op": {"type": "string"},
                                "path": {"type": "string"},
                                "value": {},
                            },
                            "required": ["op", "path"],
                        },
                    },
                },
                "required": ["id", "partitionKey", "operations"],
            },
        },
        {
            "name": "cosmos_delete_item",
            "description": "Deletes an item by id and partition key.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "id": {"type": "string"},
                    "partitionKey": {},
                },
                "required": ["id", "partitionKey"],
            },
        },
    ]


def run_tool(repo: CosmosRepository, name: str, args: dict[str, Any]) -> Any:
    if name == "cosmos_get_item":
        return safe_call(lambda: repo.get_item(args["id"], args["partitionKey"]))

    if name == "cosmos_query_items":
        return safe_call(
            lambda: repo.query_items(
                query=args["query"],
                parameters=args.get("parameters"),
                max_item_count=args.get("maxItemCount", 50),
            )
        )

    if name == "cosmos_upsert_item":
        return safe_call(lambda: repo.upsert_item(args["item"]))

    if name == "cosmos_patch_item":
        return safe_call(
            lambda: repo.patch_item(
                item_id=args["id"],
                partition_key=args["partitionKey"],
                operations=args["operations"],
            )
        )

    if name == "cosmos_delete_item":
        return safe_call(lambda: repo.delete_item(args["id"], args["partitionKey"]))

    raise ValueError(f"Unknown tool: {name}")
