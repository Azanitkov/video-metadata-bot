import os
import asyncio
from flask import Flask, request
from telegram import Update, Bot
from telegram.ext import Application, MessageHandler, filters, ContextTypes
from pymediainfo import MediaInfo

TOKEN = os.getenv("BOT_TOKEN")
if not TOKEN:
    raise ValueError("BOT_TOKEN env var is not set")

bot = Bot(token=TOKEN)
application = Application.builder().token(TOKEN).build()
app = Flask(__name__)

async def analyze_video(file_path: str) -> str:
    media_info = MediaInfo.parse(file_path)
    data = media_info.to_data()

    def format_dict(d, indent=0):
        lines = []
        for key, value in d.items():
            if isinstance(value, dict):
                lines.append(" " * indent + f"{key}:")
                lines.extend(format_dict(value, indent + 2))
            elif isinstance(value, list):
                lines.append(" " * indent + f"{key}:")
                for i, item in enumerate(value):
                    if isinstance(item, dict):
                        lines.append(" " * (indent + 2) + f"- item {i+1}:")
                        lines.extend(format_dict(item, indent + 4))
                    else:
                        lines.append(" " * (indent + 2) + f"- {item}")
            else:
                lines.append(" " * indent + f"{key}: {value}")
        return lines

    lines = format_dict(data)
    report = "\n".join(lines)

    if len(report) > 4000:
        report = report[:3990] + "\n...[truncated]..."

    return report

async def handle_video(update: Update, context: ContextTypes.DEFAULT_TYPE):
    video = update.message.video or update.message.document
    if not video:
        await update.message.reply_text("❌ Это не видео. Пожалуйста, отправьте видеофайл.")
        return

    file = await context.bot.get_file(video.file_id)
    file_path = f"/tmp/{video.file_id}.mp4"
    await file.download_to_drive(file_path)

    try:
        report = await analyze_video(file_path)
        await update.message.reply_text(f"📊 Метаданные видео:\n{report}")
    except Exception as e:
        await update.message.reply_text(f"Ошибка при анализе видео: {e}")
    finally:
        if os.path.exists(file_path):
            os.remove(file_path)

async def handle_non_video(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("❌ Пожалуйста, отправьте видеофайл для анализа метаданных.")

application.add_handler(MessageHandler(filters.VIDEO | filters.Document.VIDEO, handle_video))
application.add_handler(MessageHandler(~(filters.VIDEO | filters.Document.VIDEO), handle_non_video))

@app.route(f"/{TOKEN}", methods=["POST"])
def webhook():
    update = Update.de_json(request.get_json(force=True), bot)
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    # 👉 Важно: сначала initialize()
    loop.run_until_complete(application.initialize())
    loop.run_until_complete(application.process_update(update))

    return "ok"

@app.route("/")
def index():
    return "Бот работает!"

if __name__ == "__main__":
    PORT = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=PORT)
