from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
import os

def read_token(filename):
    script_dir = os.path.dirname(os.path.abspath(__file__))
    key_file_path = os.path.join(script_dir, filename)
    try:
        with open(key_file_path, 'r') as f:
            token = f.read().strip()
        print("Token loaded successfully.")
    except FileNotFoundError:
        print(f"Error: The file {key_file_path} was not found.")
    except Exception as e:
        print(f"An error occurred: {e}")
    return token

# Define the async function for the /start command
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a message when the command /start is issued."""
    user = update.effective_user
    await update.message.reply_html(
        f"Hola, {user.mention_html()}! soy un bot",
        # reply_markup=ForceReply(selective=True),
    )

# Define the async function for echoing messages
async def echo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Echo the user message."""
    await update.message.reply_text(update.message.text)

def main() -> None:
    """Start the bot."""
    BOT_TOKEN=read_token("key.secret")
    application = Application.builder().token(BOT_TOKEN).build()

    # on different commands - answer in Telegram
    application.add_handler(CommandHandler("start", start))

    # on non command i.e. message - echo the message on Telegram
    # filters.TEXT & ~filters.COMMAND means only text messages that are NOT commands
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, echo))

    # Run the bot until the user presses Ctrl-C
    print("Bot started, press Ctrl+C to stop.")
    application.run_polling(poll_interval=3.0)

if __name__ == '__main__':
    main()