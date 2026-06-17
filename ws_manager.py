"""
ws_manager.py - Gestion de la conexion WebSocket del bot PC.
"""

import asyncio
import json
import logging
from fastapi import WebSocket

log = logging.getLogger("revx.server")


class BotManager:

    def __init__(self):
        self.bot = None
        self._pending_result = None

    async def conectar(self, ws: WebSocket):
        await ws.accept()
        self.bot = ws
        log.info("Bot PC conectado.")

    def desconectar(self):
        self.bot = None
        log.warning("Bot PC desconectado.")
        if self._pending_result and not self._pending_result.done():
            self._pending_result.set_exception(
                ConnectionError("El bot se desconecto antes de responder.")
            )

    @property
    def conectado(self) -> bool:
        return self.bot is not None

    async def enviar_drop(self, config: dict) -> dict:
        if not self.conectado:
            raise ConnectionError("El bot no esta conectado.")

        loop = asyncio.get_event_loop()
        self._pending_result = loop.create_future()

        mensaje = json.dumps({"tipo": "ejecutar_drop", "config": config})
        await self.bot.send_text(mensaje)
        log.info("Orden enviada al bot PC.")

        try:
            resultado = await asyncio.wait_for(self._pending_result, timeout=300)
        except asyncio.TimeoutError:
            raise TimeoutError("El bot no respondio en 5 minutos.")
        finally:
            self._pending_result = None

        return resultado

    async def recibir_resultado(self, datos: str):
        try:
            msg = json.loads(datos)
        except json.JSONDecodeError:
            log.error(f"Mensaje del bot no es JSON valido: {datos}")
            return

        log.info(f"Respuesta del bot: {msg}")

        if self._pending_result and not self._pending_result.done():
            self._pending_result.set_result(msg)

    async def ping(self) -> bool:
        if not self.conectado:
            return False
        try:
            await self.bot.send_text(json.dumps({"tipo": "ping"}))
            return True
        except Exception:
            self.desconectar()
            return False


bot_manager = BotManager()
