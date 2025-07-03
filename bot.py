import os
import asyncio
import random
from flask import Flask, request
from telegram import Update, Bot, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    MessageHandler,
    CommandHandler,
    CallbackQueryHandler,
    filters,
    ContextTypes,
)
from pymediainfo import MediaInfo

TOKEN = os.getenv("BOT_TOKEN")
if not TOKEN:
    raise ValueError("BOT_TOKEN env var is not set")

bot = Bot(token=TOKEN)
app = Flask(__name__)
application = Application.builder().token(TOKEN).build()

user_data = {}

async def analyze_video(file_path: str) -> dict:
    media_info = MediaInfo.parse(file_path)
    general = next((t for t in media_info.tracks if t.track_type == "General"), None)
    video = next((t for t in media_info.tracks if t.track_type == "Video"), None)
    audio = next((t for t in media_info.tracks if t.track_type == "Audio"), None)

    data = {}

    if general:
        data["Имя файла"] = os.path.basename(file_path)
        data["Размер файла"] = general.file_size
        data["Формат"] = general.format
        data["Продолжительность (мс)"] = general.duration
        data["Общий битрейт"] = general.overall_bit_rate
        data["Дата создания"] = general.encoded_date or general.tagged_date or "Не указана"
        data["Программа кодирования"] = general.encoded_application or "Не указана"

    if video:
        data["Видео кодек"] = video.codec_id
        data["Разрешение"] = f"{video.width}x{video.height}"
        data["FPS"] = video.frame_rate
        data["Соотношение сторон"] = video.display_aspect_ratio or "Не указано"
        data["Дата съемки"] = video.recorded_date or "Не указана"

    if audio:
        data["Аудио кодек"] = audio.codec_id

    return data


def generate_questions(data: dict, n=4):
    keys = list(data.keys())
    if len(keys) < n:
        n = len(keys)

    selected_keys = random.sample(keys, n)
    questions = []

    for key in selected_keys:
        correct_answer = str(data[key])
        options = {correct_answer}
        while len(options) < 4:
            fake = correct_answer
            if fake.isdigit():
                fake = str(int(fake) + random.choice([-10, -5, 5, 10]))
            elif "x" in fake and all(part.isdigit() for part in fake.split("x")):
                w, h = map(int, fake.split("x"))
                w += random.choice([-20, 20, 30, -30])
                h += random.choice([-20, 20, 30, -30])
                fake = f"{max(w,1)}x{max(h,1)}"
            else:
                fake = fake + random.choice(["_X", "99", "??", "!!"])
            options.add(fake)
        options = list(options)
        random.shuffle(options)

        questions.append({
            "question": f"Что из перечисленного — значение для '{key}'?",
            "correct": correct_answer,
            "options": options,
            "key": key
        })

    return questions


async def start_game(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in user_data or not user_data[user_id].get("metadata"):
        await update.message.reply_text("❌ Сначала отправьте видео для анализа, чтобы начать игру.")
        return

    user_data[user_id]["score"] = 0
    user_data[user_id]["current_q"] = 0
    user_data[user_id]["questions"] = generate_questions(user_data[user_id]["metadata"], 4)
    await send_question(update, context, user_id)


async def send_question(update, context, user_id):
    q_index = user_data[user_id]["current_q"]
    question = user_data[user_id]["questions"][q_index]

    keyboard = [
        [InlineKeyboardButton(opt, callback_data=f"answer|{opt}")] for opt in question["options"]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    if update.callback_query:
        await update.callback_query.answer()
        await update.callback_query.edit_message_text(
            question["question"], reply_markup=reply_markup
        )
    else:
        await context.bot.send_message(
            chat_id=user_id,
            text=question["question"],
            reply_markup=reply_markup,
        )


async def handle_answer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    query = update.callback_query
    await query.answer()

    if user_id not in user_data or "questions" not in user_data[user_id]:
        await query.edit_message_text("❌ Игра не запущена. Напишите /game чтобы начать.")
        return

    selected_option = query.data.split("|", 1)[1]
    q_index = user_data[user_id]["current_q"]
    question = user_data[user_id]["questions"][q_index]
    correct_answer = question["correct"]

    if selected_option == correct_answer:
        user_data[user_id]["score"] += 1
        response = "✅ Правильно!"
    else:
        response = f"❌ Неверно! Правильный ответ: {correct_answer}"

    await query.edit_message_text(response)

    user_data[user_id]["current_q"] += 1

    if user_data[user_id]["current_q"] < len(user_data[user_id]["questions"]):
        await asyncio.sleep(1)
        await send_question(update, context, user_id)
    else:
        score = user_data[user_id]["score"]
        total = len(user_data[user_id]["questions"])
        comment = get_comment(score, total)
        await context.bot.send_message(
            chat_id=user_id,
            text=f"🎉 Игра окончена! Ваш счет: {score} из {total}.\n{comment}",
        )
        user_data[user_id].pop("questions", None)
        user_data[user_id].pop("score", None)
        user_data[user_id].pop("current_q", None)


def get_comment(score, total):
    percent = score / total
    if percent == 1:
        return "🌟 Отлично! Вы эксперт в метаданных!"
    elif percent >= 0.75:
        return "👍 Очень хорошо!"
    elif percent >= 0.5:
        return "🙂 Неплохо, но можно лучше!"
    else:
        return "😢 Нужно потренироваться."


async def handle_video(update: Update, context: ContextTypes.DEFAULT_TYPE):
    video = update.message.video or update.message.document
    if not video or (video.mime_type and not video.mime_type.startswith("video/")):
        await update.message.reply_text("❌ Это не видеофайл. Отправьте файл с видео.")
        return

    file = await context.bot.get_file(video.file_id)
    file_path = f"/tmp/{video.file_id}.mp4"
    await file.download_to_drive(file_path)

    try:
        metadata = await analyze_video(file_path)
        user_data[update.effective_user.id] = user_data.get(update.effective_user.id, {})
        user_data[update.effective_user.id]["metadata"] = metadata

        # После анализа показываем выбор — кнопки
        keyboard = [
            [
                InlineKeyboardButton("📊 Показать метаданные", callback_data="show_data"),
                InlineKeyboardButton("🎮 Запустить игру", callback_data="start_game"),
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await update.message.reply_text(
            "Видео успешно проанализировано! Что вы хотите сделать?",
            reply_markup=reply_markup,
        )
    except Exception as e:
        await update.message.reply_text(f"❌ Ошибка при анализе: {e}")
    finally:
        if os.path.exists(file_path):
            os.remove(file_path)


async def handle_action_buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = update.effective_user.id

    if query.data == "show_data":
        metadata = user_data.get(user_id, {}).get("metadata")
        if not metadata:
            await query.edit_message_text("❌ Метаданные не найдены. Сначала отправьте видео.")
            return

        report_lines = [f"{k}: {v}" for k, v in metadata.items()]
        text = "📊 Метаданные видео:\n" + "\n".join(report_lines)
        await query.edit_message_text(text)

    elif query.data == "start_game":
        # Инициализируем игру заново
        if user_id not in user_data or not user_data[user_id].get("metadata"):
            await query.edit_message_text("❌ Сначала отправьте видео для анализа, чтобы начать игру.")
            return
        user_data[user_id]["score"] = 0
        user_data[user_id]["current_q"] = 0
        user_data[user_id]["questions"] = generate_questions(user_data[user_id]["metadata"], 4)
        await send_question(update, context, user_id)

    else:
        await query.edit_message_text("❌ Неизвестное действие.")


async def handle_non_video(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("❌ Это не видео. Пожалуйста, отправьте видеофайл для анализа метаданных.")


application.add_handler(CallbackQueryHandler(handle_action_buttons, pattern="^(show_data|start_game)$"))
application.add_handler(CallbackQueryHandler(handle_answer, pattern="^answer\|"))
application.add_handler(MessageHandler(filters.VIDEO | filters.Document.VIDEO, handle_video))
application.add_handler(MessageHandler(~(filters.VIDEO | filters.Document.VIDEO), handle_non_video))

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

