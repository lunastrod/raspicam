import Cam
import TBot
import UserDB

from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
import time
import sqlite3

class CameraBot(TBot.TBot):
    def __init__(self,bot_name,cam_name):
        super().__init__(bot_name)
        self.cam_name=cam_name
        self.cam=None
        
        self.reconnect_camera()
        self.db=UserDB.UserDB()
        self.vigilancia=True

    def register_handlers(self):
        self.bot.add_handler(CommandHandler("start", self.start))
        self.bot.add_handler(CommandHandler("ayuda", self.ayuda))
        self.bot.add_handler(CommandHandler("ping", self.ping))

        self.bot.add_handler(CommandHandler("foto", self.foto))
        self.bot.add_handler(CommandHandler("vigilancia", self.cambiar_vigilancia))
        self.bot.add_handler(CommandHandler("estado", self.estado))

        self.bot.add_handler(CommandHandler("register", self.register))
        self.bot.add_handler(CommandHandler("unregister", self.unregister))
        self.bot.add_handler(CommandHandler("ver_usuarios", self.ver_usuarios))

    def reconnect_camera(self):
        try:
            if self.cam is None:
                self.cam=Cam.Cam(self.cam_name)
        except Exception as e:
            print(f"Error reconectando la cámara: {e}")

    async def ayuda(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Lista de comandos disponibles"""
        mensaje = "Lista de comandos disponibles:\n\n"
        for handler in self.bot.handlers[0]:
            if isinstance(handler, CommandHandler):
                command_names = [f"/{cmd}" for cmd in sorted(handler.commands)]
                desc = (getattr(handler.callback, "__doc__", "") or "").strip().split("\n")[0]

                if desc:
                    mensaje += f"{' , '.join(command_names)} - {desc}\n"
                else:
                    mensaje += f"{' , '.join(command_names)}\n"

        await update.message.reply_text(mensaje)

    async def ping (self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Ping"""
        await update.message.reply_text("Pong!")


    #comando estado
    async def estado(self,update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Muestra el estado del bot"""
        if self.db.get_user(update.effective_user.id) is None:
            await update.message.reply_text("No tienes autorización para usar este bot.")
            return
        mensaje="Estado:\n"
        if self.cam is None:
            mensaje+="- Cámara desconectada.\n"
        else:
            mensaje+="- Cámara conectada.\n"
            mensaje+=f"    Nombre: {self.cam_name}\n"
            mensaje+=f"    IP: {self.cam.ip}\n"
            mensaje+=f"    Puerto: {self.cam.port}\n"
            mensaje+=f"    Usuario: {self.cam.user}\n"
            mensaje+=f"    Contraseña: {self.cam.password}\n"
        if self.vigilancia:
            mensaje+="- Modo: vigilancia\n"
        else:
            mensaje+="- Modo: Estás en casa\n"
        await update.message.reply_text(mensaje)

    async def foto(self,update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Captura una foto de la cámara"""

        if self.db.get_user(update.effective_user.id) is None: #COMPRUEBA AUTORIZACION
            await update.message.reply_text("No tienes autorización para usar este bot.")
            return

        self.reconnect_camera()
        if self.cam is None:
            await update.message.reply_text("Cámara no conectada.")
            return

        #TODO: hilo de ejecucion bot no deberia sacar fotos para no entrar en colisión con el hilo principal

        path=self.cam.take_picture()
        try:
            with open(path, "rb") as photo:
                await update.message.reply_photo(photo)
        except Exception as e:
            print(f"Error taking picture: {e}")
            await update.message.reply_text(f"Error al capturar la foto: {e}")

    #cambiar modo vigilancia
    async def cambiar_vigilancia(self,update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """cambiar modo vigilancia"""
        if self.db.get_user(update.effective_user.id) is None:
            await update.message.reply_text("No tienes autorización para usar este bot.")
            return
        self.vigilancia=not self.vigilancia
        if self.vigilancia:
            await update.message.reply_text("Vigilancia activada")
        else:
            await update.message.reply_text("Vigilancia desactivada")

    #=========================== users =============================
    async def start(self,update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Inicia el bot"""
        try:
            admin=self.db.get_admin()
            if admin is None:
                self.db.add_user(update.effective_user.id,update.effective_user.username,is_admin=1)
                await update.message.reply_text("Eres el nuevo admin")
                return
            if self.db.is_user_admin(update.effective_user.id):
                await update.message.reply_text("Ya eres admin")
                return
            if self.db.get_user(update.effective_user.id) is not None:
                await update.message.reply_text("Ya tienes autorización")
                return
            username=update.effective_user.username
            user_id=update.effective_user.id
            await update.message.reply_text("Solcitando acceso")
            await context.bot.send_message(chat_id=admin[0],text=f"Solicitud de acceso de @{username} (ID: {user_id})\nUsa este comando para autorizar")
            await context.bot.send_message(chat_id=admin[0],text=f"/register {user_id}")
            return
        except Exception as e:
            print(f"Error: {e}")
            await update.message.reply_text("Error al iniciar el bot.")
    
    async def register(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """ADMIN: Registra un nuevo usuario"""
        try:
            admin_id = update.effective_user.id
            if not self.db.is_user_admin(admin_id):
                await update.message.reply_text("No eres administrador.")
                return
            args = update.message.text.split(" ")
            if len(args) < 2:
                await update.message.reply_text("Uso correcto: /register <user_id>")
                return
            user_id = int(args[1])

            # Check if user already exists
            if self.db.get_user(user_id) is not None:
                await update.message.reply_text("Ya existe un usuario con ese ID.")
                return

            try:
                chat = await context.bot.get_chat(user_id)
                username = chat.username or chat.first_name or "Desconocido"
            except Exception as e:
                print(f"No se pudo obtener el nombre de usuario: {e}")
                username = "Desconocido"

            self.db.add_user(user_id, username, is_admin=0)
            await update.message.reply_text(f"Usuario {username} ({user_id}) registrado correctamente.")

            # Notify the new user
            try:
                await context.bot.send_message(
                    chat_id=user_id,
                    text="Has sido autorizado para usar el bot de la cámara."
                )
            except Exception as e:
                print(f"No se pudo enviar mensaje al nuevo usuario: {e}")

        except Exception as e:
            print(f"Error en /register: {e}")
            await update.message.reply_text("Error al registrar usuario.")

    async def unregister(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """ADMIN: Elimina un usuario"""
        try:
            admin_id = update.effective_user.id
            if not self.db.is_user_admin(admin_id):
                await update.message.reply_text("No eres administrador.")
                return
                
            args = update.message.text.split(" ")
            if len(args) < 2:
                await update.message.reply_text("Uso correcto: /unregister <user_id>")
                return
                
            user_id = int(args[1])
            
            # Check if user exists
            if self.db.get_user(user_id) is None:
                await update.message.reply_text("No existe un usuario con ese ID.")
                return
                
            self.db.delete_user(user_id)
            await update.message.reply_text(f"Usuario {user_id} eliminado correctamente.")

        except Exception as e:
            print(f"Error en /unregister: {e}")
            await update.message.reply_text("Error al eliminar usuario.")

    async def ver_usuarios(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """ADMIN: Ver usuarios registrados"""
        try:
            admin_id = update.effective_user.id
            if not self.db.is_user_admin(admin_id):
                await update.message.reply_text("No eres administrador.")
                return

            mensaje="Usuarios:\n"
            for user in self.db.get_all_users():
                if self.db.is_user_admin(user[0]):
                    mensaje+="(admin) "
                mensaje+=f"{user[0]}: {user[1]}\n"
            await update.message.reply_text(mensaje)
        except Exception as e:
            print(f"Error en /ver_usuarios: {e}")
            await update.message.reply_text("Error al mostrar usuarios.")


def main():
    t=CameraBot("Bot1","Camara2")
    t.start_thread()
    while True:
        time.sleep(1)
        if(t.vigilancia):
            t.cam.take_picture()


if __name__ == '__main__':
    main()
