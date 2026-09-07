#!/bin/bash

# Выходим незамедлительно при любой ошибке
set -e

. .env

# Настройки путей
BACKEND_DIR="backend"
TMP_DIR="tmp_deploy"
FUNCTION_NAME="$1" # Имя функции передается как аргумент скрипта

if [ -z "$FUNCTION_NAME" ]; then
    echo "🚀 Начинаем деплой облачных функций..."
fi  

# Проверяем наличие утилиты zip
if ! command -v zip &> /dev/null; then
    echo "❌ Ошибка: Утилита zip не найдена. Установите её (apt install zip / brew install zip)."
    exit 1
fi

# Подготавливаем временную папку для сборки изолированных архивов
rm -rf "$TMP_DIR"
mkdir -p "$TMP_DIR"

# ─── ШАГ 1: Деплой функции ASSISTANT ─────────────────────────────
if [ $FUNCTION_NAME == "assistant" ] || [ -z "$FUNCTION_NAME" ]; then
    echo "🤖 Подготовка и деплой функции ASSISTANT..."

    # Для ассистента нужны: assistant.js (переименованный в index.js), package.json и инструкция .md
    mkdir -p "$TMP_DIR/assistant"
    cp "$BACKEND_DIR/assistant.js" "$TMP_DIR/assistant/index.js"
    cp "$BACKEND_DIR/package.json" "$TMP_DIR/assistant/package.json"
    cp "$BACKEND_DIR/system-instruction.md" "$TMP_DIR/assistant/system-prompt.md" # Переименовываем в соответствии с PROMPT_PATH

    # Создаем zip-архив
    cd "$TMP_DIR/assistant"
    zip -q -r "../assistant.zip" ./*
    cd ../..

    # Отправляем в Яндекс Облако
    echo "📤 Загрузка новой версии функции assistant в облако..."
    #    --function-id "$ASSISTANT_FUNC_ID" \
    yc serverless function version create \
        --function-name assistant \
        --runtime nodejs22 \
        --entrypoint index.handler \
        --memory 256m \
        --execution-timeout 40s \
        --folder-id $YC_FOLDER_ID \
        --source-path "$TMP_DIR/assistant.zip"

    echo "✅ Функция ASSISTANT успешно обновлена!"
fi

# ─── ШАГ 2: Деплой функции PLAYLISTS ─────────────────────────────
if [ $FUNCTION_NAME == "playlists" ] || [ -z "$FUNCTION_NAME" ]; then
    echo "📂 Подготовка и деплой функции PLAYLISTS..."

    # Для файлового менеджера нужны: playlists.js (переименованный в index.js) и package.json
    mkdir -p "$TMP_DIR/playlists"
    cp "$BACKEND_DIR/playlists.js" "$TMP_DIR/playlists/index.js"
    cp "$BACKEND_DIR/package.json" "$TMP_DIR/playlists/package.json"

    # Создаем zip-архив
    cd "$TMP_DIR/playlists"
    zip -q -r "../playlists.zip" ./*
    cd ../..

    # Отправляем в Яндекс Облако
    echo "📤 Загрузка новой версии функции playlists в облако..."
    yc serverless function version create \
        --function-name playlists \
        --runtime nodejs22 \
        --entrypoint index.handler \
        --memory 128m \
        --execution-timeout 10s \
        --folder-id $YC_FOLDER_ID \
        --source-path "$TMP_DIR/playlists.zip"

    echo "✅ Функция PLAYLISTS успешно обновлена!"
fi

# ─── ОЧИСТКА ─────────────────────────────────────────────────────
rm -rf "$TMP_DIR"

if [ -z "$FUNCTION_NAME" ]; then
    echo "🎉 Весь бэкенд успешно задеплоен!"
fi  
