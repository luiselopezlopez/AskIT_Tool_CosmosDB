import os


def get_setting(name: str, required: bool = True, default: str | None = None) -> str:
    value = os.getenv(name, default)
    if required and (value is None or value == ""):
        raise ValueError(f"Missing required setting: {name}")
    return value or ""


def cosmos_config() -> dict:
    return {
        "connection_string": os.getenv("COSMOS_CONNECTION_STRING", ""),
        "endpoint": os.getenv("COSMOS_ENDPOINT", ""),
        "key": os.getenv("COSMOS_KEY", ""),
        "database_name": get_setting("COSMOS_DATABASE_NAME"),
        "container_name": get_setting("COSMOS_CONTAINER_NAME"),
    }
