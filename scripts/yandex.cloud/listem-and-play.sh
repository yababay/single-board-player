#!/usr/bin/env bash

# 1. Загружаем конфигурацию из .env
ENV_FILE=".env"
if [ -f "$ENV_FILE" ]; then
    export $(grep -v '^#' "$ENV_FILE" | xargs)
else
    echo "Ошибка: Файл .env не найден." >&2
    exit 1
fi

. .env

AUDIO_FILE="/tmp/voice_request.ogg"
RECORD_DURATION="4s" # длительность записи

echo "=== Слушаю вашу команду (запись $RECORD_DURATION) ===" >&2

# Запускаем запись через PulseAudio с жестким лимитом времени
# arecord пишет 16кГц в моно, ffmpeg считывает те же 16кГц в моно и пакует в чистый OGG
#arecord -f S16_LE -r 16000 -ac 1 -D hw:0,0 -d 5 2>/dev/null | \
#ffmpeg -y -f s16le -ar 16000 -ac 1 -i - -acodec libvorbis "$AUDIO_FILE" 2>/dev/null
# arecord -f cd -t raw -d 5 | oggenc - --resample 11025 --downmix "$AUDIO_FILE" 2>/dev/null
#arecord -f cd -t raw -d 5 | \
#ffmpeg -y -f s16le -ar 16000 -ac 1 -i - -acodec libvorbis "$AUDIO_FILE" 2>/dev/null
arecord -f cd -t raw -d 5 | oggenc - -r -o  "$AUDIO_FILE" 2>/dev/null

# Проверяем, что файл физически создался и он не пустой
if [ ! -s "$AUDIO_FILE" ]; then
    echo "Ошибка: Не удалось записать аудиофайл. Проверьте устройство $AUDIO_DEVICE" >&2
    exit 1
fi

echo "Распознавание речи через Yandex SpeechKit..." >&2

# 2. Отправляем аудиофайл в API синхронного распознавания Яндекса
# Используем официальный endpoint SpeechKit STT v1
STT_URL="$YC_STT_ENDPOINT?lang=ru-RU&format=oggopus&topic=general&folderId=${YC_FOLDER_ID}"

# Отправляем аудиофайл с использованием YC_IAM_TOKEN
STT_RESPONSE=$(curl -s -X POST "$STT_URL" \
  --header "Authorization: Bearer ${YC_IAM_TOKEN}" \
  --header "Content-Type: audio/ogg" \
  --data-binary @"$AUDIO_FILE")

# Извлекаем распознанный текст (из поля .result JSON-ответа)
USER_TEXT=$(echo "$STT_RESPONSE" | jq -r '.result' 2>/dev/null)
# Эта команда Bash превратит "Найди ноктюрн шопена Найди ноктюрн шопена" в чистую строку
# USER_TEXT=$(echo "$USER_TEXT" | sed -E 's/(Найди.+)\1/\1/')
# USER_TEXT=$(echo "$USER_TEXT" | sed -E 's/Найди/Найди\n/') | head -n 1 | tr -d '\n'
USER_TEXT=$(echo "$USER_TEXT" | python3 -c "import sys; s=sys.stdin.read(); p = r'Най[дт]и[а-я\ ]+$'; import re;  print(re.sub(p, '', s).strip(', '))")

# Проверяем ответ на ошибки авторизации или пустой результат
if [ -z "$USER_TEXT" ] || [ "$USER_TEXT" == "null" ]; then
    echo "Ошибка распознавания. Ответ сервера:" >&2
    echo "$STT_RESPONSE" | jq '.' >&2
    rm -f "$AUDIO_FILE"
    exit 1
fi

echo "Успешно распознано: \"$USER_TEXT\"" >&2
rm -f "$AUDIO_FILE"

# 3. Передаем распознанный текст в ваш готовый и отлаженный плеер!
# Он сам пойдет в AI Studio, найдет плейлист и трек, и запустит mpc
$(dirname "$0")/voice-player.sh "$USER_TEXT"
