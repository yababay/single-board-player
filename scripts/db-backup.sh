#!/usr/bin/env bash

# Путь к вашей музыкальной директории, подключенной к Git
MUSIC_DIR="$HOME/Music"
BACKUP_FILE="${MUSIC_DIR}/player_semantic_db.sql"

echo "Запуск текстового резервного копирования для Git-репозитория..."

# Делаем plain-text дамп (-F p), который Git сможет легко диффить.
# Флаг --clean заставит скрипт автоматически очищать старые таблицы перед восстановлением
pg_dump -h localhost -U mabel -F p --clean -b -f "$BACKUP_FILE" player

if [ $? -eq 0 ]; then
    echo "Текстовый бэкап успешно обновлен: $BACKUP_FILE"
    echo "Теперь вы можете сделать: cd $MUSIC_DIR && git add player_semantic_db.sql && git commit -m 'Update DB'"
else
    echo "Ошибка при создании бэкапа!" >&2
    exit 1
fi
