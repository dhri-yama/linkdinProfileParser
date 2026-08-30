from fastapi import Header, HTTPException

from app.config import settings


async def verify_api_key(x_api_key: str = Header(..., alias="X-API-Key")) -> str:
    if x_api_key not in settings.api_keys_list:
        raise HTTPException(status_code=401, detail="Invalid or missing API key")
    return x_api_key
