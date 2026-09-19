import json
import os
import threading
import time
import asyncio
import logging

logging.getLogger("httpx").setLevel(logging.WARNING)

from telegram import Update
from telegram.ext import (
    CommandHandler,
    ContextTypes
)

from TBot import TBot


class CameraBot(TBot):

    USERS_FILE = "usuarios.json"
    STREAM_DIR = "stream"

    def __init__(self, name):

        self.usuarios = {
            "administradores": [],
            "canales": []
        }

        self.ficheros_enviados = set()

        self.cargar_usuarios()

        super().__init__(name)

    # ---------------------------------------------------------
    # USUARIOS
    # ---------------------------------------------------------

    def cargar_usuarios(self):

        if not os.path.exists(self.USERS_FILE):

            self.guardar_usuarios()

            return

        try:

            with open(
                self.USERS_FILE,
                "r",
                encoding="utf-8"
            ) as f:

                self.usuarios = json.load(f)

        except json.JSONDecodeError:

            print(
                f"Error: '{self.USERS_FILE}' "
                "no contiene un JSON válido."
            )

        except Exception as e:

            print(
                "Error cargando usuarios:",
                e
            )

    def guardar_usuarios(self):

        try:

            with open(
                self.USERS_FILE,
                "w",
                encoding="utf-8"
            ) as f:

                json.dump(
                    self.usuarios,
                    f,
                    indent=4
                )

        except Exception as e:

            print(
                "Error guardando usuarios:",
                e
            )

    def es_admin(self, user_id):

        return user_id in (
            self.usuarios["administradores"]
        )

    # ---------------------------------------------------------
    # COMANDOS
    # ---------------------------------------------------------

    async def ping(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE
    ):

        await update.message.reply_text(
            "pong"
        )

    async def ayuda(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE
    ):

        texto = (
            "/ping - Comprobar que el bot responde\n"
            "/inicio - Añadir este chat a las alertas\n"
            "/ayuda - Mostrar esta ayuda\n"
            "/borrar_canales - Borrar todos los canales"
        )

        await update.message.reply_text(
            texto
        )

    async def inicio(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE
    ):

        user_id = update.effective_user.id
        chat_id = update.effective_chat.id

        if not self.es_admin(user_id):

            await update.message.reply_text(
                "No tienes permisos para ejecutar este comando."
            )

            return

        if chat_id not in self.usuarios["canales"]:

            self.usuarios["canales"].append(
                chat_id
            )

            self.guardar_usuarios()

            await update.message.reply_text(
                "Chat añadido a los canales de alertas."
            )

        else:

            await update.message.reply_text(
                "Este chat ya está configurado como canal de alertas."
            )

    async def borrar_canales(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE
    ):

        user_id = update.effective_user.id

        if not self.es_admin(user_id):

            await update.message.reply_text(
                "No tienes permisos para ejecutar este comando."
            )

            return

        self.usuarios["canales"] = []

        self.guardar_usuarios()

        await update.message.reply_text(
            "Todos los canales de alertas han sido borrados."
        )

    # ---------------------------------------------------------
    # HANDLERS
    # ---------------------------------------------------------

    def register_handlers(self):

        self.bot.add_handler(
            CommandHandler(
                "ping",
                self.ping
            )
        )

        self.bot.add_handler(
            CommandHandler(
                "inicio",
                self.inicio
            )
        )

        self.bot.add_handler(
            CommandHandler(
                "ayuda",
                self.ayuda
            )
        )

        self.bot.add_handler(
            CommandHandler(
                "borrar_canales",
                self.borrar_canales
            )
        )

    # ---------------------------------------------------------
    # VIGILANCIA DE FICHEROS
    # ---------------------------------------------------------

    def iniciar_vigilancia_ficheros(self):

        os.makedirs(
            self.STREAM_DIR,
            exist_ok=True
        )

        # Los ficheros que ya existían al arrancar
        # no se enviarán.
        for filename in os.listdir(
            self.STREAM_DIR
        ):

            if filename.endswith(
                (".jpg", ".mp4")
            ):

                self.ficheros_enviados.add(
                    filename
                )

        print(
            "Ficheros existentes ignorados:",
            len(self.ficheros_enviados)
        )

        self.hilo_ficheros = threading.Thread(
            target=self.vigilar_ficheros,
            daemon=True
        )

        self.hilo_ficheros.start()

    def vigilar_ficheros(self):

        print(
            "Iniciando vigilancia de ficheros..."
        )

        while True:

            try:

                for filename in os.listdir(
                    self.STREAM_DIR
                ):

                    if not filename.endswith(
                        (".jpg", ".mp4")
                    ):

                        continue

                    if filename in self.ficheros_enviados:

                        continue

                    filepath = os.path.join(
                        self.STREAM_DIR,
                        filename
                    )

                    if not os.path.isfile(
                        filepath
                    ):

                        continue

                    # Comprobamos que el fichero
                    # haya terminado de escribirse.
                    try:

                        size1 = os.path.getsize(
                            filepath
                        )

                        time.sleep(0.2)

                        size2 = os.path.getsize(
                            filepath
                        )

                        if size1 != size2:

                            continue

                    except OSError:

                        continue

                    print(
                        "Nuevo fichero:",
                        filename
                    )

                    asyncio.run_coroutine_threadsafe(
                        self.enviar_fichero(
                            filepath,
                            filename
                        ),
                        self.bot_loop
                    )

                    # Lo añadimos temporalmente para que
                    # no se lance otra tarea para el mismo
                    # fichero mientras se está enviando.
                    self.ficheros_enviados.add(
                        filename
                    )

            except Exception as e:

                print(
                    "Error vigilando ficheros:",
                    e
                )

            time.sleep(1)

    # ---------------------------------------------------------
    # ENVÍO DE FICHEROS
    # ---------------------------------------------------------

    async def enviar_fichero(
        self,
        filepath,
        filename
    ):

        canales = list(
            self.usuarios["canales"]
        )

        if not canales:

            print(
                "No hay canales configurados."
            )

            # Permitimos que vuelva a intentarse
            # si posteriormente se configura un canal.
            self.ficheros_enviados.discard(
                filename
            )

            return

        enviado_correctamente = True

        print(
            "Enviando:",
            filename
        )

        for chat_id in canales:

            try:

                if filename.endswith(".jpg"):

                    with open(
                        filepath,
                        "rb"
                    ) as f:

                        await self.bot.bot.send_photo(
                            chat_id=chat_id,
                            photo=f,
                            caption=filename
                        )

                elif filename.endswith(".mp4"):

                    with open(
                        filepath,
                        "rb"
                    ) as f:

                        await self.bot.bot.send_video(
                            chat_id=chat_id,
                            video=f,
                            caption=filename
                        )

                print(
                    "Enviado a:",
                    chat_id
                )

            except Exception as e:

                enviado_correctamente = False

                print(
                    f"Error enviando {filename} "
                    f"a {chat_id}:",
                    e
                )

        if not enviado_correctamente:

            self.ficheros_enviados.discard(
                filename
            )

            print(
                "El fichero se volverá a intentar:",
                filename
            )

        else:

            print(
                "Fichero enviado correctamente:",
                filename
            )

    # ---------------------------------------------------------
    # EJECUCIÓN DEL BOT
    # ---------------------------------------------------------

    def run(self):

        self.bot_loop = asyncio.new_event_loop()

        asyncio.set_event_loop(
            self.bot_loop
        )

        self.bot_loop.run_until_complete(
            self.bot.initialize()
        )

        self.bot_loop.run_until_complete(
            self.bot.start()
        )

        self.bot_loop.run_until_complete(
            self.bot.updater.start_polling(
                poll_interval=3.0
            )
        )

        # El loop ya existe y está preparado.
        self.iniciar_vigilancia_ficheros()

        print(
            "CameraBot iniciado"
        )

        try:

            self.bot_loop.run_forever()

        finally:

            self.bot_loop.run_until_complete(
                self.bot.updater.stop()
            )

            self.bot_loop.run_until_complete(
                self.bot.stop()
            )

            self.bot_loop.run_until_complete(
                self.bot.shutdown()
            )

            self.bot_loop.close()
