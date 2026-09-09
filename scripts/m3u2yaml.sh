#!/usr/bin/env bash

# Корневой элемент YAML
echo "playlists:"

# Определяем паттерн для поиска (аргумент $1 или все m3u по умолчанию)
TARGET_PATTERN="${1:-*.m3u}"

# Включаем nullglob для безопасной работы с масками
shopt -s nullglob

# Функция очистки строки от недопустимых символов YAML
clean_string() {
    echo "$1" | \
    # sed -E 's/[^[:alnum:][:space:]\-_.,;:()\/\[\]\{\}\"\']//g' | \
    sed -E 's/[^[:alnum:][:space:]\-_.,;:()\/\[\]\{\}\"]//g' | tr -d "'" | \
    sed 's/[[:cntrl:]]//g' | \
    sed 's/[[:space:]]\+/_/g'  # Заменяем множественные пробелы на _
}

# Функция очистки текстовых метаданных (сохраняет пробелы)
clean_metadata_text() {
    echo "$1" | \
    sed -E 's/[^[:alnum:][:space:]\-_.,;:()\/\[\]\{\}\"]//g' | tr -d "'" | \
    sed 's/[[:cntrl:]]//g'
}

playlist_counter=0

# Сортированный вывод плейлистов через ls -1
ls -1 $TARGET_PATTERN 2>/dev/null | while IFS= read -r playlist_path; do
    ((playlist_counter++))
    
    playlist_name=$(basename "$playlist_path" .m3u)
    playlist_number=$(echo "$playlist_name" | egrep -o '^[0-9]+' | sed -E 's/^0+//')
    
    echo "  - playlist_title: \"$(clean_string "$playlist_name")\""
    echo "    playlist_number: $playlist_number"
    echo "    tracks:"
    
    track_counter=0
    
    # Построчно читаем m3u файл
    while IFS= read -r track_line || [[ -n "$track_line" ]]; do
        track_line=$(echo "$track_line" | tr -d '\r')
        
        # Игнорируем заголовки m3u и пустые строки
        [[ -z "$track_line" || "$track_line" =~ ^# ]] && continue
        
        if [[ -f "$track_line" ]]; then
            ((track_counter++))
            
            # Очищаем строку пути от пробелов по краям
            track_line="${track_line#${track_line%%[![:space:]]*}}"
            track_line="${track_line%${track_line##*[![:space:]]}}"
            
            echo "      - track_number: $track_counter"
            echo "        file_path: \"$(clean_string "$track_line")\""

            if command -v ffprobe >/dev/null 2>&1; then
                echo "        metadata:"
                
                # Читаем теги через ffprobe в формате "ключ=значение"
                ffprobe -v error -show_entries format_tags -of default=noprint_wrappers=1 "$track_line" 2>/dev/null | \
                while IFS='=' read -r full_key value; do
                    
                    local_key="${full_key#TAG:}"
                    if [[ "$local_key" =~ ^TXXX: ]]; then
                        local_key="${local_key#TXXX:}"
                    fi
                    
                    local_key=$(echo "$local_key" | tr '[:upper:]' '[:lower:]' | tr ' ' '_')
                    
                    value=$(echo "$value" | sed -E 's/^[[:space:]]+|[[:space:]]+$//g')
                    [[ -z "$value" ]] && continue
                    [[ "$local_key" =~ ^(track|disc|encoder|major_brand|minor_version|compatible_brands)$ ]] && continue
                    
                    # 🌟 ВОТ ЭТА СТРОКА: Меняем clean_string на clean_metadata_text
                    value=$(clean_metadata_text "$value")
                    
                    if [[ "$local_key" == "genre" ]]; then
                        value=$(echo "$value" | sed -E 's/ \([a-zA-Z0-9 -]+\)$//')
                    fi
                    
                    echo "          ${local_key}: \"${value}\""
                done
            fi
            
        else
            echo "      - track_number: $track_counter"
            echo "        raw_title: \"$(clean_string "$track_line")\""
        fi
    done < "$playlist_path"
done
