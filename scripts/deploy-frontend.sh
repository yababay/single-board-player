#!/bin/bash

# Выходим незамедлительно при любой ошибке
set -e

# ─── НАСТРОЙКИ ПРОЕКТА ───────────────────────────────────────────
BUCKET_NAME="playlists-dispatcher"
BUILD_DIR="build"
INSTRUCTIONS_DIR="src/lib/assets/instructions"

# Официальный S3-эндпоинт Яндекс Облака
YC_S3_ENDPOINT="https://storage.yandexcloud.net"

echo "🚀 Начинаем безопасный деплой статики в бакет: $BUCKET_NAME"

# Проверяем, установлен ли AWS CLI
if ! command -v aws &> /dev/null; then
    echo "❌ Ошибка: AWS CLI не установлен."
    echo "Установите его, чтобы загружать файлы по S3 протоколу."
    exit 1
fi

# ─── ШАГ 1: Сборка SvelteKit ─────────────────────────────────────
echo "📦 Шаг 1: Сборка SvelteKit проекта..."
if [ -d "$BUILD_DIR" ]; then
    rm -rf "$BUILD_DIR"
fi

npm run build

cp -r "$INSTRUCTIONS_DIR" "$BUILD_DIR"

if [ ! -d "$BUILD_DIR" ]; then
    echo "❌ Ошибка: Директория '$BUILD_DIR' не найдена после сборки."
    exit 1
fi

# ─── ШАГ 2: Загрузка файлов (Перезапись статики без удаления YAML) ──
echo "📤 Шаг 2: Накат новой сборки в бакет через S3 API..."

# 1. Загружаем изолированную папку сборки SvelteKit (_app) с долгим кэхом
echo "🔹 Синхронизация папки _app с длительным кэшированием..."
aws s3 cp "$BUILD_DIR/_app" "s3://$BUCKET_NAME/_app" \
    --endpoint-url="$YC_S3_ENDPOINT" \
    --recursive \
    --cache-control "public, max-age=31536000, immutable"
aws s3 cp "$BUILD_DIR/fonts" "s3://$BUCKET_NAME/fonts" \
    --endpoint-url="$YC_S3_ENDPOINT" \
    --recursive \
    --cache-control "public, max-age=31536000, immutable"
aws s3 cp "$BUILD_DIR/instructions" "s3://$BUCKET_NAME/instructions" \
    --endpoint-url="$YC_S3_ENDPOINT" \
    --recursive \
    --cache-control "public, max-age=31536000, immutable"

# 2. Загружаем точечно корневые файлы сайта без кэша (не трогая файлы .yaml в корне бакета)
echo "🔹 Обновление корневых файлов сайта (index.html, favicon.svg)..."

if [ -f "$BUILD_DIR/index.html" ]; then
    aws s3 cp "$BUILD_DIR/index.html" "s3://$BUCKET_NAME/index.html" \
        --endpoint-url="$YC_S3_ENDPOINT" \
        --cache-control "no-store, no-cache, must-revalidate"
fi

if [ -f "$BUILD_DIR/favicon.svg" ]; then
    aws s3 cp "$BUILD_DIR/favicon.svg" "s3://$BUCKET_NAME/favicon.svg" \
        --endpoint-url="$YC_S3_ENDPOINT" \
        --cache-control "no-store, no-cache, must-revalidate"
fi

# 3. Если в корне папки build появились другие файлы (но НЕ .yaml), загружаем их
find "$BUILD_DIR" -maxdepth 1 -type f | while read -r file; do
    filename=$(basename "$file")
    # Пропускаем уже загруженные index и favicon
    if [ "$filename" != "index.html" ] && [ "$filename" != "favicon.svg" ]; then
        # Строгая защита: проверяем, чтобы случайно не затереть yaml файлы плейлистов
        if [[ "$filename" != *.yaml ]] && [[ "$filename" != *.yml ]]; then
            aws s3 cp "$file" "s3://$BUCKET_NAME/$filename" \
                --endpoint-url="$YC_S3_ENDPOINT" \
                --cache-control "public, max-age=86400"
        fi
    fi
done

echo "🎉 Безопасный деплой успешно завершен!"
