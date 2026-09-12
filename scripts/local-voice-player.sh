#!/usr/bin/env bash

# Считываем текстовый запрос пользователя
USER_QUERY="$1"
if [ -z "$USER_QUERY" ]; then
    echo "Использование: $0 \"запрос на естественном языке\""
    exit 1
fi

# 1. Загружаем переменные окружения, чтобы скрипт знал, где лежит mpc
ENV_FILE="$(dirname "$0")/.parent/.env"
if [ -f "$ENV_FILE" ]; then
    export $(grep -v '^#' "$ENV_FILE" | xargs)
fi

# Экранируем пробелы и спецсимволы в запросе для безопасной передачи в URL
URL_ENCODED_QUERY=$(echo "$USER_QUERY" | xxd -plain | tr -d '\n' | sed 's/\(..\)/%\1/g')

# 2. Формируем безопасную команду curl через абстрактную переменную
# Локальный сервер FastAPI по умолчанию слушает порт 8080
LOCAL_IP="127.0.0.1"
PATH_NAME=":8080/search?query=${URL_ENCODED_QUERY}"

CURL_COMMAND="http://${LOCAL_IP}${PATH_NAME}"

# Выполняем моментальный запрос к локальному ИИ-серверу
RESPONSE=$(curl -s "$CURL_COMMAND")

# 3. Извлекаем техническую команду (номер_плейлиста;номер_трека) с помощью jq
AI_COMMAND=$(echo "$RESPONSE" | jq -r '.command' 2>/dev/null)
DEBUG_INFO=$(echo "$RESPONSE" | jq -r '.debug_info' 2>/dev/null)

if [ -z "$AI_COMMAND" ] || [ "$AI_COMMAND" == "null" ]; then
    echo "Ошибка локального ИИ: Ничего не найдено или сервер выключен." >&2
    exit 1
fi

echo "$DEBUG_INFO" >&2

# 4. Разбираем полученную пару чисел
PLAYLIST_NUMBER="${AI_COMMAND%%;*}"
TRACK_NUMBER="${AI_COMMAND#*;}"

# Форматируем номер плейлиста до 4 знаков с лидирующими нулями для mpc
FORMATED_NUM=$(printf "%04d" "$PLAYLIST_NUMBER")

# Ищем плейлист по строгому регулярному выражению с начала строки (защита от коллизий)
PLAYLIST_NAME=$(mpc lsplaylists | grep -E "^${FORMATED_NUM}-" | head -n 1)

if [ -z "$PLAYLIST_NAME" ]; then
    echo "Ошибка: Плейлист под номером ${FORMATED_NUM} не найден в MPD." >&2
    exit 1
fi

# 5. Исполняем физические команды управления локальным проигрывателем
echo "Запуск: $PLAYLIST_NAME -> Трек №$TRACK_NUMBER" >&2

mpc clear >/dev/null
mpc load "$PLAYLIST_NAME" >/dev/null
mpc play "$TRACK_NUMBER" >/dev/null
