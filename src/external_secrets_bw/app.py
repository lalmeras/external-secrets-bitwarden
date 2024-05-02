"""FastAPI application."""
import asyncio
import logging
import os
import subprocess
from contextlib import asynccontextmanager

import aiohttp
from fastapi import FastAPI

logging.basicConfig(level=logging.DEBUG)

BW_ENDPOINT = "http://localhost:8087/list/object/items"
BW_SYNC_ENDPOINT = "http://localhost:8087/sync?force=true"


@asynccontextmanager
async def lifespan(app: FastAPI):  # noqa: ARG001
    """Start bw server at startup, and stops it at shutdown."""
    login_needed = False
    try:
        subprocess.check_call(  # noqa: ASYNC101
            ["bw", "login", "--check", "--raw"],  # noqa: S607
        )
    except subprocess.CalledProcessError as exc:
        # returncode == 1: login is needed
        if exc.returncode != 1:
            raise exc  # noqa: TRY201
        login_needed = True
    if login_needed:
        bw_session = subprocess.check_output(  # noqa: ASYNC101
            [  # noqa: S607
                "bw",
                "login",
                os.getenv("BW_USER"),
                "--passwordenv",
                "BW_PASSWORD",
                "--raw",
            ]
        )
    else:
        bw_session = subprocess.check_output(["bw", "unlock", "--passwordenv", "BW_PASSWORD", "--raw"])  # noqa: ASYNC101,S607
    environ = {}
    environ.update(os.environ)
    environ["BW_SESSION"] = bw_session
    subprocess.check_call(["bw", "unlock", "--check", "--raw"], env=environ)  # noqa: ASYNC101,S607
    bw_serve = await asyncio.create_subprocess_exec("bw", "serve", "--port", "8087", env=environ, start_new_session=True)
    yield
    if bw_serve:
        bw_serve.terminate()


app = FastAPI(lifespan=lifespan)


@app.post("/sync")
async def sync():
    return await bw_sync()


@app.get("/collection/{collection_id}")
async def root(collection_id: str, include_raw: bool = False, include_fields: bool = True):  # noqa: FBT001,FBT002
    return wrap(await bw_call(collection_id), include_raw, include_fields)


def wrap(original, include_raw: bool, include_fields: bool):  # noqa: FBT001
    """Transform raw /list/object/items result to a key / value map.

    The following keys are populated:
    * {item_uuid}/name
    * {item_uuid}/username
    * {item_uuid}/password
    * {item_uuid}/fields/{name}
    """
    key_list = original["data"]["data"]
    result = {}
    for item in key_list:
        if "name" in item:
            result[f"{item['id']}/name"] = item["name"]
        if "login" in item:
            if "password" in item["login"]:
                result[f"{item['id']}/username"] = item["login"]["username"]
            if "password" in item["login"]:
                result[f"{item['id']}/password"] = item["login"]["password"]
        if include_fields:
            for field in item.get("fields", []):
                result[f"{item['id']}/fields/{field['name']}"] = field["value"]
        if include_raw:
            result[f"{item['id']}/raw"] = item
    return result


async def bw_call(collection_id: str):
    """Forward call to `bw serve` server via REST API call."""
    async with aiohttp.ClientSession() as session:
        params = {"collectionId": collection_id}
        async with session.get(BW_ENDPOINT, params=params) as response:
            return await response.json()


async def bw_sync():
    """Forward call to `bw serve` server via REST API call."""
    async with aiohttp.ClientSession() as session, session.post(BW_SYNC_ENDPOINT) as response:
        return await response.json()
