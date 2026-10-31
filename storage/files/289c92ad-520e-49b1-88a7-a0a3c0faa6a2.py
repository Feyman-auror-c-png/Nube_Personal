import asyncio
import logging
import os
import time
from contextlib import asynccontextmanager
from typing import Any

import httpx
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("sat_client")

load_dotenv()

SAT_BASE_URL = os.getenv("SAT_BASE_URL", "https://srvnjs.santotomasport.com.gt")
SAT_USER = os.getenv("SAT_USER", "SAT")
SAT_PASSWORD = os.getenv("SAT_PASSWORD", "5341542d454d504f524e4143")
SAT_LOGIN_KEY = os.getenv("SAT_LOGIN_KEY", "5341542d454d504f524e4143")
TOKEN_REFRESH_MARGIN_SECONDS = 120


class SATClientError(Exception):
    """Error returned while communicating with the SAT service."""


class NotificationPayload(BaseModel):
    payload: dict[str, Any] = Field(..., description="Payload expected by the SAT endpoint")


class SATClient:
    def __init__(self) -> None:
        self._token: str | None = None
        self._expires_at: float = 0
        self._lock = asyncio.Lock()

    @property
    def is_token_valid(self) -> bool:
        return bool(self._token) and time.time() < self._expires_at - TOKEN_REFRESH_MARGIN_SECONDS

    async def start(self) -> None:
        try:
            await self._get_token()
            logger.info("SAT authentication initialized")
        except SATClientError as error:
            logger.warning("SAT authentication will retry on first request: %s", error)

    async def _get_token(self, force_refresh: bool = False) -> str:
        if not force_refresh and self.is_token_valid:
            return self._token or ""

        async with self._lock:
            if not force_refresh and self.is_token_valid:
                return self._token or ""

            login_url = f"{SAT_BASE_URL}/token"
            try:
                async with httpx.AsyncClient(timeout=30) as client:
                    response = await client.post(
                        login_url,
                        params={"SAT": SAT_LOGIN_KEY},
                        auth=httpx.BasicAuth(SAT_USER, SAT_PASSWORD),
                    )
                    response.raise_for_status()
            except httpx.HTTPError as error:
                raise SATClientError(f"No fue posible autenticar con SAT: {error}") from error

            try:
                data = response.json()
            except ValueError:
                data = response.text.strip()

            if isinstance(data, dict):
                token = data.get("access_token") or data.get("token") or data.get("accessToken")
                expires_in = data.get("expires_in", 3600)
            else:
                token = data
                expires_in = 3600

            if not token or not isinstance(token, str):
                raise SATClientError("La respuesta de autenticación de SAT no contiene un token válido")

            try:
                expires_in_seconds = int(expires_in)
            except (TypeError, ValueError):
                expires_in_seconds = 3600

            self._token = token
            self._expires_at = time.time() + max(expires_in_seconds, TOKEN_REFRESH_MARGIN_SECONDS + 1)
            return token

    async def post(self, path: str, payload: dict[str, Any]) -> dict[str, Any] | list[Any] | str:
        async def send(token: str) -> httpx.Response:
            async with httpx.AsyncClient(timeout=60) as client:
                return await client.post(
                    f"{SAT_BASE_URL}{path}",
                    json=payload,
                    headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
                )

        token = await self._get_token()
        try:
            response = await send(token)
            if response.status_code == 401:
                response = await send(await self._get_token(force_refresh=True))
            response.raise_for_status()
        except httpx.HTTPError as error:
            detail = error.response.text if isinstance(error, httpx.HTTPStatusError) else str(error)
            raise SATClientError(f"SAT respondió con un error: {detail}") from error

        try:
            return response.json()
        except ValueError:
            return response.text

    def status(self) -> dict[str, Any]:
        seconds_remaining = max(0, int(self._expires_at - time.time())) if self._token else 0
        return {"authenticated": self.is_token_valid, "seconds_remaining": seconds_remaining}


sat_client = SATClient()


@asynccontextmanager
async def lifespan(_: FastAPI):
    await sat_client.start()
    yield


app = FastAPI(title="SAT Notificaciones", lifespan=lifespan)
app.mount("/static", StaticFiles(directory="static"), name="static")


@app.get("/", include_in_schema=False)
async def index() -> FileResponse:
    return FileResponse("static/index.html")


@app.get("/api/status")
async def status() -> dict[str, Any]:
    return sat_client.status()


@app.post("/api/notificaciones/crear")
async def create_notification(request: NotificationPayload) -> dict[str, Any]:
    try:
        result = await sat_client.post("/sat/listEmb/postNotificacionSAEM", request.payload)
        return {"ok": True, "result": result}
    except SATClientError as error:
        raise HTTPException(status_code=502, detail=str(error)) from error


@app.post("/api/notificaciones/actualizar")
async def update_notification(request: NotificationPayload) -> dict[str, Any]:
    try:
        result = await sat_client.post("/sat/listEmb/postNotificacioAESAEM", request.payload)
        return {"ok": True, "result": result}
    except SATClientError as error:
        raise HTTPException(status_code=502, detail=str(error)) from error
