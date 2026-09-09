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
    echo "Ошибка: Файл инструкции assistant_prompt.txt не найден." >&2
    exit 1
fi

# 3. Безопасно формируем JSON-пакет с помощью jq (это исключит ошибку 400 навсегда)
JSON_PAYLOAD=$(jq -n \
  --arg model "gpt://${YC_FOLDER_ID}/${YC_MODEL_NAME}" \
  --arg inst "$SYSTEM_INSTRUCTIONS" \
  --arg input "$USER_QUERY" \
  --arg vs_id "$YC_VECTOR_STORE_ID" \
  '{
    model: $model,
    instructions: $inst,
    tools: [{type: "file_search", vector_store_ids: [$vs_id]}],
    input: $input
  }')

# Выполняем быстрый сетевой запрос к Yandex AI Studio
RESPONSE=$(curl -s -X POST "${YC_BASE_URL}/responses" \
  --header "Authorization: Api-Key ${YC_API_KEY}" \
  --header "Content-Type: application/json" \
  --header "x-project: ${YC_FOLDER_ID}" \
  --data "$JSON_PAYLOAD")


# 2. Загружаем системную инструкцию для ассистента
#PROMPT_FILE="$(dirname "$0")/prompt.txt"
#if [ -f "$PROMPT_FILE" ]; then
#    SYSTEM_INSTRUCTIONS=$(cat "$PROMPT_FILE")
#else
#    echo "Ошибка: Файл инструкции не найден ($PROMPT_FILE)." >&2
#    exit 1
#fi

# Экранируем кавычки в запросе и инструкции для безопасной передачи в JSON
#SAFE_QUERY=$(echo "$USER_QUERY" | sed 's/"/\\"/g')
#SAFE_INSTRUCTIONS=$(echo "$SYSTEM_INSTRUCTIONS" | sed 's/"/\\"/g')

#echo "Отправка запроса в Yandex AI Studio..." >&2
# echo "Запрос: $USER_QUERY" >&2
# echo "Инструкции: $SYSTEM_INSTRUCTIONS" >&2

# 3. Выполняем быстрый сетевой запрос к Yandex AI Studio (Responses API)
#RESPONSE=$(curl -s -X POST "${YC_BASE_URL}/responses" \
#  --header "Authorization: Api-Key ${YC_API_KEY}" \
#  --header "Content-Type: application/json" \
#  --header "x-project: ${YC_FOLDER_ID}" \
#  --data "{
#    \"model\": \"gpt://${YC_FOLDER_ID}/${YC_MODEL_NAME}\",
#    \"instructions\": \"${SAFE_INSTRUCTIONS}\",
#    \"tools\": [
#      {
#        \"type\": \"file_search\",
#        \"vector_store_ids\": [\"${YC_VECTOR_STORE_ID}\"]
#      }
#    ],
#    \"input\": \"${SAFE_QUERY}\"
#  }")

# 4. Извлекаем чистый текстовый ответ модели
# Ищем шаблон "число;число" в любом месте JSON-ответа (включая summary и message.text)
CLEAN_RESULT=$(echo "$RESPONSE" | grep -oE '[0-9]+\;[0-9]+' | head -n 1)

# Проверяем, удалось ли вытащить команду
if [ -n "$CLEAN_RESULT" ]; then
    # Выводим техническую команду в stdout (её перехватит ESP32/провод)
    echo "$CLEAN_RESULT"
else
    # Если в ответе вообще не оказалось цифр с точкой с запятой, пишем в лог ошибок (stderr)
    echo "Ошибка ИИ: В ответе Яндекса не найден технический формат команды." >&2
    echo "Сырой JSON ответа для отладки:" >&2
    echo "$RESPONSE" | jq '.' >&2
    exit 1
fi

