import json
import logging
import os
from typing import Any

import azure.functions as func

from src.config import cosmos_config
from src.cosmos_client import CosmosRepository
from src.app_metadata import SERVER_NAME, SERVER_VERSION
from src.tool_registry import run_tool, tool_definitions

app = func.FunctionApp(http_auth_level=func.AuthLevel.ANONYMOUS)
_logger = logging.getLogger(__name__)
_repo: CosmosRepository | None = None


def _configure_logging() -> None:
    logging.basicConfig(
        level=os.getenv("LOG_LEVEL", "INFO"),
        format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
    )
    logging.getLogger("azure").setLevel(logging.WARNING)
    logging.getLogger("azure.core.pipeline.policies.http_logging_policy").setLevel(logging.WARNING)
    logging.getLogger("azure.monitor").setLevel(logging.WARNING)


_configure_logging()


def get_repo() -> CosmosRepository:
    global _repo
    if _repo is None:
        cfg = cosmos_config()
        _repo = CosmosRepository(
            connection_string=cfg["connection_string"],
            endpoint=cfg["endpoint"],
            key=cfg["key"],
            database_name=cfg["database_name"],
            container_name=cfg["container_name"],
        )
    return _repo


def _headers() -> dict[str, str]:
    return {
        "Content-Type": "application/json",
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Headers": "Content-Type,Authorization,x-functions-key",
        "Access-Control-Allow-Methods": "GET,POST,OPTIONS",
    }


def _json_response(payload: Any, status_code: int = 200) -> func.HttpResponse:
    return func.HttpResponse(json.dumps(payload, ensure_ascii=False), status_code=status_code, headers=_headers())


def _error_response(message: str, status_code: int = 400, details: Any = None) -> func.HttpResponse:
    payload: dict[str, Any] = {"error": message}
    if details is not None:
        payload["details"] = details
    return _json_response(payload, status_code=status_code)


def _parse_json_object(req: func.HttpRequest) -> dict[str, Any]:
    body = req.get_json()
    if body is None:
        return {}
    if not isinstance(body, dict):
        raise ValueError("Invalid payload: expected a JSON object")
    return body


def _tool_input_schema(tool_name: str) -> dict[str, Any]:
    for tool in tool_definitions():
        if tool["name"] == tool_name:
            return tool.get("inputSchema", {"type": "object"})
    return {"type": "object"}


def _run_tool_endpoint(req: func.HttpRequest, tool_name: str) -> func.HttpResponse:
    if req.method == "OPTIONS":
        return func.HttpResponse(status_code=204, headers=_headers())

    try:
        arguments = _parse_json_object(req)
        _logger.info("Tool request received: tool=%s", tool_name)
        result = run_tool(get_repo(), tool_name, arguments)
        return _json_response(result, status_code=200)
    except ValueError as ex:
        return _error_response(str(ex), status_code=400)
    except KeyError as ex:
        return _error_response(f"Missing required parameter: {str(ex)}", status_code=400)
    except Exception as ex:
        _logger.exception("Tool request failed: %s", tool_name)
        return _error_response("Server error", status_code=500, details=str(ex))


def _openapi_spec(req: func.HttpRequest) -> dict[str, Any]:
    base_url = req.url.split("/api/")[0]
    paths: dict[str, Any] = {
        "/health": {
            "get": {
                "operationId": "getHealth",
                "summary": "API health",
                "responses": {
                    "200": {
                        "description": "Service metadata",
                        "content": {
                            "application/json": {
                                "example": {
                                    "name": SERVER_NAME,
                                    "version": SERVER_VERSION,
                                    "status": "ok",
                                }
                            }
                        },
                    }
                },
            }
        },
        "/tools": {
            "get": {
                "operationId": "listTools",
                "summary": "List available tools",
                "responses": {
                    "200": {
                        "description": "Tool catalog",
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "properties": {
                                        "tools": {
                                            "type": "array",
                                            "items": {"type": "object"},
                                        }
                                    },
                                }
                            }
                        },
                    }
                },
                "security": [{"FunctionKey": []}],
            }
        },
    }

    for tool in tool_definitions():
        name = tool["name"]
        paths[f"/tools/{name}"] = {
            "post": {
                "operationId": f"execute_{name}",
                "summary": tool.get("description", f"Execute {name}"),
                "requestBody": {
                    "required": True,
                    "content": {
                        "application/json": {
                            "schema": _tool_input_schema(name),
                        }
                    },
                },
                "responses": {
                    "200": {"description": "Tool result"},
                    "400": {"description": "Invalid request payload"},
                    "500": {"description": "Server error"},
                },
                "security": [{"FunctionKey": []}],
            }
        }

    return {
        "openapi": "3.0.3",
        "info": {
            "title": "CosmosDB Tools API",
            "version": SERVER_VERSION,
            "description": "HTTP endpoints that expose Cosmos tools directly over Azure Functions.",
        },
        "servers": [{"url": f"{base_url}/api"}],
        "paths": paths,
        "components": {
            "securitySchemes": {
                "FunctionKey": {
                    "type": "apiKey",
                    "in": "header",
                    "name": "x-functions-key",
                    "description": "Azure Function key for AuthLevel.Function endpoints.",
                }
            }
        },
    }


@app.route(route="openapi.json", methods=["GET"], auth_level=func.AuthLevel.ANONYMOUS)
def openapi_json(req: func.HttpRequest) -> func.HttpResponse:
    return func.HttpResponse(json.dumps(_openapi_spec(req)), status_code=200, headers=_headers())


@app.route(route="swagger", methods=["GET"], auth_level=func.AuthLevel.ANONYMOUS)
def swagger_ui(req: func.HttpRequest) -> func.HttpResponse:
    swagger_html = """
<!doctype html>
<html>
<head>
  <meta charset=\"utf-8\" />
    <title>CosmosDB Tools Swagger</title>
  <link rel=\"stylesheet\" href=\"https://unpkg.com/swagger-ui-dist@5/swagger-ui.css\" />
</head>
<body>
  <div id=\"swagger-ui\"></div>
  <script src=\"https://unpkg.com/swagger-ui-dist@5/swagger-ui-bundle.js\"></script>
  <script>
    window.ui = SwaggerUIBundle({
      url: './openapi.json',
      dom_id: '#swagger-ui',
      deepLinking: true,
      presets: [SwaggerUIBundle.presets.apis],
      layout: 'BaseLayout'
    });
  </script>
</body>
</html>
"""
    return func.HttpResponse(swagger_html, status_code=200, mimetype="text/html")


@app.route(route="health", methods=["GET", "OPTIONS"], auth_level=func.AuthLevel.ANONYMOUS)
def health(req: func.HttpRequest) -> func.HttpResponse:
    if req.method == "OPTIONS":
        return func.HttpResponse(status_code=204, headers=_headers())
    return _json_response({"name": SERVER_NAME, "version": SERVER_VERSION, "status": "ok"}, status_code=200)


@app.route(route="tools", methods=["GET", "OPTIONS"], auth_level=func.AuthLevel.FUNCTION)
def tools(req: func.HttpRequest) -> func.HttpResponse:
    if req.method == "OPTIONS":
        return func.HttpResponse(status_code=204, headers=_headers())
    return _json_response({"tools": tool_definitions()}, status_code=200)


@app.route(route="tools/cosmos_get_item", methods=["POST", "OPTIONS"], auth_level=func.AuthLevel.FUNCTION)
def cosmos_get_item(req: func.HttpRequest) -> func.HttpResponse:
    return _run_tool_endpoint(req, "cosmos_get_item")


@app.route(route="tools/cosmos_query_items", methods=["POST", "OPTIONS"], auth_level=func.AuthLevel.FUNCTION)
def cosmos_query_items(req: func.HttpRequest) -> func.HttpResponse:
    return _run_tool_endpoint(req, "cosmos_query_items")


@app.route(route="tools/cosmos_upsert_item", methods=["POST", "OPTIONS"], auth_level=func.AuthLevel.FUNCTION)
def cosmos_upsert_item(req: func.HttpRequest) -> func.HttpResponse:
    return _run_tool_endpoint(req, "cosmos_upsert_item")


@app.route(route="tools/cosmos_patch_item", methods=["POST", "OPTIONS"], auth_level=func.AuthLevel.FUNCTION)
def cosmos_patch_item(req: func.HttpRequest) -> func.HttpResponse:
    return _run_tool_endpoint(req, "cosmos_patch_item")


@app.route(route="tools/cosmos_delete_item", methods=["POST", "OPTIONS"], auth_level=func.AuthLevel.FUNCTION)
def cosmos_delete_item(req: func.HttpRequest) -> func.HttpResponse:
    return _run_tool_endpoint(req, "cosmos_delete_item")
