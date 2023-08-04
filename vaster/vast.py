import os
from typing import *

import requests
from pydantic import BaseModel

from .logger import set_logger

logger = set_logger(__name__)

API_KEY = os.environ.get("VAST_API_KEY")
API_URL = "https://console.vast.ai/api/v0"

VAST_API_KEY_FILE = os.path.join(os.path.expanduser("~"), ".vast_api_key")

if os.path.exists(VAST_API_KEY_FILE) and API_KEY is None:
    with open(VAST_API_KEY_FILE, "r") as f:
        API_KEY = f.read().strip()


class CreateInstanceRequest(BaseModel):
    args_str: str = ""
    client_id: str
    image: str
    env: Optional[dict] = {}
    price: Optional[float] = None
    disk: int
    label: Optional[str] = None
    extra: Optional[str] = None
    onstart: str = ""
    runtype: str = "ssh"
    image_login: Optional[str] = None
    python_utf8: Optional[bool] = None
    lang_utf8: Optional[bool] = None
    use_jupyter_lab: bool = False
    jupyter_dir: Optional[str] = None
    create_from: Optional[str] = None
    force: Optional[bool] = None


class CreateInstanceResponse(BaseModel):
    success: bool
    new_contract: int


def check_api_key():
    if API_KEY is None:
        logger.error("You are not logged in to vast.ai.")
        logger.error("Run `vaster login` to log in.")
        exit(1)


def login(api_key: str):
    with open(VAST_API_KEY_FILE, "w") as f:
        f.write(api_key)
    logger.info("Logged in successfully.")


def api_url(path: str, queries: Dict[str, Any] = {}):
    queries["api_key"] = API_KEY
    url = f"{API_URL}{path}"
    if len(queries) > 0:
        url += "?"
        for k, v in queries.items():
            url += f"{k}={v}&"
        url = url[:-1]
    return url


def get_instances():
    r = requests.get(api_url("/instances"), {"owner": "me"})
    r.raise_for_status()
    return r.json()["instances"]


def create_instance(id: int, req: CreateInstanceRequest):
    r = requests.put(
        api_url(f"/asks/{id}/"),
        json=req.model_dump(),
    )
    r.raise_for_status()
    return CreateInstanceResponse.model_validate(r.json())


def delete_instance(id: int):
    r = requests.delete(
        api_url(f"/instances/{id}/"),
    )
    r.raise_for_status()
    return r.json()
