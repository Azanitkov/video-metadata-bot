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
app = Flask(__name__)
application = Application.builder().token(TOKEN).build()


# 🔍 Анализ и форматирование ВСЕХ метаданных
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
                        lines.append(" " * (indent + 2) + f"- item {i + 1}:")
                        lines.extend(format_dict(item, indent + 4))
                    else:
                        lines.append(" " * (indent + 2) + f"- {item}")
            else:
                lines.append(" " * indent + f"{key}: {value}")
        return lines

    report = "\n".join(format_dict(data))

    if len(report) > 4000:
        return report[:3990] + "\n...[Обрезано из-за лимита Telegram]..."
    return report or "⚠️ Не удалось получить метаданные."


# ✅ Обработка видео
async def handle_video(update: Update, context: ContextTypes.DEFAULT_TYPE):
    video = update.message.video or update.message.document
    if not video or (video.mime_type and not video.mime_type.startswith("video/")):
        await update.message.reply_text("❌ Это не видеофайл. Отправьте файл с видео.")
        return

    file = await context.bot.get_file(video.file_id)
    file_path = f"/tmp/{video.file_id}.mp4"
    await file.download_to_drive(file_path)

    try:
        report = await analyze_video(file_path)
        await update.message.reply_text(f"📊 Метаданные видео:\n{report}")
    except Exception as e:
        await update.message.reply_text(f"❌ Ошибка при анализе: {e}")
    finally:
        if os.path.exists(file_path):
            os.remove(file_path)


# 🚫 Обработка не-видео
async def handle_non_video(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("❌ Это не видео. Пожалуйста, отправьте видеофайл для анализа метаданных.")


# 📥 Роутинг сообщений
application.add_handler(MessageHandler(filters.VIDEO | filters.Document.VIDEO, handle_video))
application.add_handler(MessageHandler(~(filters.VIDEO | filters.Document.VIDEO), handle_non_video))


# 🌐 Flask + Telegram Webhook
loop = asyncio.new_event_loop()
asyncio.set_event_loop(loop)

async def init_app():
    await application.initialize()
    await application.start()

loop.run_until_complete(init_app())


@app.route(f"/{TOKEN}", methods=["POST"])
def webhook():
    json_update = request.get_json(force=True)
    update = Update.de_json(json_update, bot)
    loop.run_until_complete(application.process_update(update))
    return "ok"


@app.route("/")
def index():
    return "✅ Бот работает!"


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))
