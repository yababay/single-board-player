#!/usr/bin/env bash

INPUT_YAML="${1:-combined_playlists.yaml}"
# OUTPUT_TXT="${2:-rag_knowledge_base.txt}"

if [ ! -f "$INPUT_YAML" ]; then
    echo "Ошибка: Файл $INPUT_YAML не найден." >&2
    exit 1
fi

OUTPUT_TXT="$(echo $INPUT_YAML | sed 's/\.yaml$/.txt/')"

if command -v yq >/dev/null 2>&1; then
    echo "Используется yq для парсинга YAML."
else
    echo "Ошибка: yq не установлен. Пожалуйста, установите его." >&2
    exit 1
fi

echo "Конвертация $INPUT_YAML в плоский вид для RAG..." >&2
> "$OUTPUT_TXT"

# Парсим YAML с помощью yq и собираем плоские строки
yq e '.playlists[] | .playlist_number as $pl_num | .tracks[] | 
  "Композитор: " + .metadata.composer + 
  ". Исполнитель: " + .metadata.artist + 
  ". Альбом: " + .metadata.album + 
  ". Название: " + .metadata.title + 
  ". Форма: " + .metadata.form + 
  ". Инструмент: " + .metadata.instrument + 
  ". Стиль: " + .metadata.style + 
  ". Период: " + .metadata.period + 
  ". Команда: " + ($pl_num | cast("string")) + ";" + (.track_number | cast("string"))' "$INPUT_YAML" >> "$OUTPUT_TXT"

echo "Готово! Результат сохранен в $OUTPUT_TXT. Загрузите этот файл в AI Studio." >&2
