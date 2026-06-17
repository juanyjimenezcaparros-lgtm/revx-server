"""
main.py - Servidor RevX (uso personal)
"""

import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv

try:
    from server.ws_manager import bot_manager
except ImportError:
    from ws_manager import bot_manager

load_dotenv()
TOKEN_SECRETO = os.getenv("REVX_TOKEN", "cambia-esto-por-algo-secreto")

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s", datefmt="%H:%M:%S")
log = logging.getLogger("revx.server")

@asynccontextmanager
async def lifespan(app: FastAPI):
    log.info("Servidor RevX arrancado.")
    yield
    log.info("Servidor RevX detenido.")

app = FastAPI(title="RevX Server", version="2.0", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

class DropRequest(BaseModel):
    token: str
    config: dict

@app.get("/estado")
async def estado():
    return {"servidor": "ok", "bot_conectado": bot_manager.conectado}

@app.websocket("/ws/bot")
async def websocket_bot(ws: WebSocket):
    await bot_manager.conectar(ws)
    try:
        while True:
            datos = await ws.receive_text()
            await bot_manager.recibir_resultado(datos)
    except WebSocketDisconnect:
        bot_manager.desconectar()

@app.post("/api/drops/ejecutar")
async def ejecutar_drop(req: DropRequest):
    if req.token != TOKEN_SECRETO:
        raise HTTPException(status_code=401, detail="Token incorrecto.")
    if not bot_manager.conectado:
        raise HTTPException(status_code=503, detail="El bot no esta conectado.")
    try:
        resultado = await bot_manager.enviar_drop(req.config)
    except ConnectionError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except TimeoutError as e:
        raise HTTPException(status_code=504, detail=str(e))
    return {"ok": True, "resultado": resultado}
