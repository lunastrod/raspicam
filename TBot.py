from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
import json
import threading
import time

SECRET_FILE = 'camara.secret'

class TBot:
    def __init__(self,name):
        self.extract_secret(name)
        self.bot = Application.builder().token(self.token).build()
        self.register_handlers()
        
    def start_thread(self):
        threading.Thread(target=self.run, daemon=True).start()
        #notes: you need to keep your main alive to keep the bot running

    def run(self):
        self.bot.run_polling(poll_interval=3.0, stop_signals=None)

    def extract_secret(self,name):
        try:
            with open(SECRET_FILE, 'r') as f:
                secrets = json.load(f)
                self.token=secrets[name]["token"]
                
        except FileNotFoundError:
            print(f"Error: Secret file '{SECRET_FILE}' not found in the current directory.")
            return
        except json.JSONDecodeError:
            print(f"Error: Secret file '{SECRET_FILE}' is not valid JSON.")
            return
        except Exception as e:
            print(f"Error parsing credentials from secret file: {e}")
            return
    
    def register_handlers(self):
        pass
def main():
    t=TBot("Bot1")
    t.start_thread()
    while True:
        time.sleep(1)

if __name__ == '__main__':
    main()