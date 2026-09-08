#!/bin/bash

# Выходим незамедлительно при любой ошибке
set -e

# Подгружаем переменные окружения из .env
. .env

# Настройки путей
BACKEND_DIR="backend"
TMP_DIR="tmp_deploy"
FUNCTION_NAME="$1" # Имя функции передается как аргумент скрипта

if [ -z "$FUNCTION_NAME" ]; then
    echo "🚀 Начинаем деплой всех облачных функций..."
fi  

# Проверяем наличие утилиты zip
if ! command -v zip &> /dev/null; then
    echo "❌ Ошибка: Утилита zip не найдена. Установите её."
    exit 1
fi

# Подготавливаем временную папку для сборки изолированных архивов
rm -rf "$TMP_DIR"
mkdir -p "$TMP_DIR"

# ─── ШАГ 1: Деплой функции ASSISTANT ─────────────────────────────
if [ "$FUNCTION_NAME" == "assistant" ] || [ -z "$FUNCTION_NAME" ]; then
    echo "🤖 Подготовка и деплой функции ASSISTANT..."

    mkdir -p "$TMP_DIR/assistant"
    cp "$BACKEND_DIR/assistant.js" "$TMP_DIR/assistant/index.js"
    cp "$BACKEND_DIR/package.json" "$TMP_DIR/assistant/package.json"
    cp "$BACKEND_DIR/system-instruction.md" "$TMP_DIR/assistant/system-prompt.md"

    cd "$TMP_DIR/assistant"
    zip -q -r "../assistant.zip" ./*
    cd ../..

    echo "📤 Загрузка новой версии функции assistant в облако с переменными..."
    # 💡 Добавлен флаг --environment для проброса настроек AI Studio
    yc serverless function version create \
        --function-name assistant \
        --runtime nodejs22 \
        --entrypoint index.handler \
        --memory 256m \
        --execution-timeout 40s \
        --folder-id "$YC_FOLDER_ID" \
        --service-account-id "$YC_ACCOUNT_ID" \
        --source-path "$TMP_DIR/assistant.zip" \
        --environment "BASE_URL=$YC_BASE_URL,YANDEX_API_KEY=$YC_API_KEY,MODEL_NAME=$YC_MODEL_NAME,FOLDER_ID=$YC_FOLDER_ID"

    echo "✅ Функция ASSISTANT успешно обновлена!"
fi

# ─── ШАГ 2: Деплой функции PLAYLISTS ─────────────────────────────
if [ "$FUNCTION_NAME" == "playlists" ] || [ -z "$FUNCTION_NAME" ]; then
    echo "📂 Подготовка и деплой функции PLAYLISTS..."

    mkdir -p "$TMP_DIR/playlists"
    cp "$BACKEND_DIR/playlists.js" "$TMP_DIR/playlists/index.js"
    cp "$BACKEND_DIR/package.json" "$TMP_DIR/playlists/package.json"

    cd "$TMP_DIR/playlists"
    zip -q -r "../playlists.zip" ./*
    cd ../..

    echo "📤 Загрузка новой версии функции playlists с двойным монтированием..."
    # 💡 Каждый ресурс монтируется через СВОЙ собственный флаг --mount
    yc serverless function version create \
        --function-name playlists \
        --runtime nodejs22 \
        --entrypoint index.handler \
        --memory 128m \
        --execution-timeout 10s \
        --folder-id "$YC_FOLDER_ID" \
        --service-account-id "$YC_ACCOUNT_ID" \
        --source-path "$TMP_DIR/playlists.zip" \
        --mount type=object-storage,mount-point=playlists,bucket=playlists-dispatcher,prefix=playlists \
        --mount type=object-storage,mount-point=instructions,bucket=playlists-dispatcher,prefix=instructions

    echo "✅ Функция PLAYLISTS успешно обновлена!"
fi

# ─── ОЧИСТКА ─────────────────────────────────────────────────────
rm -rf "$TMP_DIR"

if [ -z "$FUNCTION_NAME" ]; then
    echo "🎉 Весь бэкенд успешно задеплоен!"
fi  
