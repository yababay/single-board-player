#!/usr/bin/env bash

# Считываем поисковую фразу пользователя
USER_QUERY="$1"
if [ -z "$USER_QUERY" ]; then
    echo "Использование: $0 \"запрос на естественном языке\"" >&2
    exit 1
fi

# 1. Загружаем переменные окружения из файла .env
ENV_FILE=".env"
if [ -f "$ENV_FILE" ]; then
    export $(grep -v '^#' "$ENV_FILE" | xargs)
else
    echo "Ошибка: Файл конфигурации .env не найден ($ENV_FILE)." >&2
    exit 1
fi

# 2. Загружаем системную инструкцию для ассистента
PROMPT_FILE="$(dirname "$0")/prompt.txt"
if [ -f "$PROMPT_FILE" ]; then
    SYSTEM_INSTRUCTIONS=$(cat "$PROMPT_FILE")
else
    echo "Ошибка: Файл инструкции не найден ($PROMPT_FILE)." >&2
    exit 1
fi

# Экранируем кавычки в запросе и инструкции для безопасной передачи в JSON
SAFE_QUERY=$(echo "$USER_QUERY" | sed 's/"/\\"/g')
SAFE_INSTRUCTIONS=$(echo "$SYSTEM_INSTRUCTIONS" | sed 's/"/\\"/g')

echo "Отправка запроса в Yandex AI Studio..." >&2
echo "Запрос: $USER_QUERY" >&2
echo "Инструкции: $SYSTEM_INSTRUCTIONS" >&2

# 3. Выполняем быстрый сетевой запрос к Yandex AI Studio (Responses API)
RESPONSE=$(curl -s -X POST "${YC_BASE_URL}/responses" \
  --header "Authorization: Api-Key ${YC_API_KEY}" \
  --header "Content-Type: application/json" \
  --header "x-project: ${YC_FOLDER_ID}" \
  --data "{
    \"model\": \"gpt://${YC_FOLDER_ID}/${YC_MODEL_NAME}\",
    \"instructions\": \"${SAFE_INSTRUCTIONS}\",
    \"tools\": [
      {
        \"type\": \"file_search\",
        \"vector_store_ids\": [\"${YC_VECTOR_STORE_ID}\"]
      }
    ],
    \"input\": \"${SAFE_QUERY}\"
  }")

# 4. Извлекаем чистый текстовый ответ модели с помощью jq
# В структуре ответа Яндекса текст лежит в поле .message.text
echo "Ответ модели: $RESPONSE" >&2
CLEAN_RESULT=$(echo "$RESPONSE" | jq -r '.message.text' 2>/dev/null | xargs)

# Проверяем, что ответ соответствует шаблону "число;число"
if [[ "$CLEAN_RESULT" =~ ^[0-9]+\;[0-9]+$ ]]; then
    # Выводим техническую команду в stdout (её перехватит ESP32/провод)
    echo "$CLEAN_RESULT"
else
    # Если модель вернула ошибку или лишний текст, пишем в лог ошибок (stderr)
    echo "Ошибка ИИ: Модель вернула некорректный формат." >&2
    echo "Сырой ответ: $CLEAN_RESULT" >&2
    exit 1
fi
