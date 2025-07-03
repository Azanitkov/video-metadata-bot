# Telegram Bot: Анализ видео по метаданным

## Как использовать

1. Установи переменную окружения `BOT_TOKEN` с токеном Telegram-бота.
2. Убедись, что `mediainfo` установлен на сервере.
3. Задеплой на Railway или другой PaaS.
4. Установи webhook вручную:

```
curl -F "url=https://<your-url>/<your-token>" https://api.telegram.org/bot<your-token>/setWebhook
```
