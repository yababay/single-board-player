#!/usr/bin/env python3
import sys
import yaml
import psycopg2
import os
from sentence_transformers import SentenceTransformer
from dotenv import load_dotenv

load_dotenv()  # This loads the variables from the .env file into os.environ
pg_user = os.getenv('PG_USER')
pg_password = os.getenv('PG_PASSWORD')
pg_database = os.getenv('PG_DATABASE')

def main():
    # 1. Читаем все данные из входного потока (stdin)
    print("Ожидание данных из stdin...", file=sys.stderr)
    try:
        raw_data = sys.stdin.read()
        if not raw_data.strip():
            print("Ошибка: На вход поданы пустые данные.", file=sys.stderr)
            sys.exit(1)
        data = yaml.safe_load(raw_data)
    except Exception as e:
        print(f"Ошибка парсинга YAML: {e}", file=sys.stderr)
        sys.exit(1)

    # Проверяем структуру YAML
    if not data or 'playlists' not in data:
        print("Ошибка: В YAML отсутствует корневой элемент 'playlists'.", file=sys.stderr)
        sys.exit(1)

    # 2. Загружаем бесплатную локальную ИИ-модель эмбеддингов
    # Она весит немного, работает быстро на процессоре и дает отличные 1024-мерные векторы
    print("Загрузка локальной ИИ-модели эмбеддингов...", file=sys.stderr)
    model = SentenceTransformer('intfloat/multilingual-e5-large')

    # 3. Подключение к вашей PostgreSQL 17
    # Замените параметры подключения на ваши реальные, если они отличаются
    try:
        conn = psycopg2.connect(f"dbname={pg_database} user={pg_user} password={pg_password} host=localhost")
        cur = conn.cursor()
    except Exception as e:
        print(f"Ошибка подключения к PostgreSQL: {e}", file=sys.stderr)
        sys.exit(1)

    # 4. Цикл обработки данных
    for pl in data.get('playlists', []):
        pl_num = pl.get('playlist_number')
        pl_title = pl.get('playlist_title')
        
        if not pl_num or not pl_title:
            print("Пропуск плейлиста: отсутствуют обязательные поля number или title", file=sys.stderr)
            continue
            
        # Сохраняем/обновляем плейлист
        cur.execute(
            "INSERT INTO playlists (playlist_number, playlist_title) VALUES (%s, %s) ON CONFLICT (playlist_number) DO UPDATE SET playlist_title = EXCLUDED.playlist_title;",
            (pl_num, pl_title)
        )
        
        print(f"Импорт плейлиста {pl_num}: {pl_title}")
        
        for track in pl.get('tracks', []):
            t_num = track.get('track_number')
            f_path = track.get('file_path')
            meta = track.get('metadata', {})
            
            if not t_num or not f_path:
                continue
            
            # Собираем семантическое текстовое ядро для ИИ-поиска по смыслам
            text_components = [
                f"Композитор: {meta.get('composer','')}",
                f"Исполнитель: {meta.get('artist','')}",
                f"Альбом: {meta.get('album','')}",
                f"Название: {meta.get('title','')}",
                f"Форма: {meta.get('form','')}",
                f"Инструмент: {meta.get('instrument','')}",
                f"Стиль: {meta.get('style','')}",
                f"Период: {meta.get('period','')}",
                f"Настроение: {meta.get('mood','')}"
            ]
            text_for_ai = ". ".join([c for c in text_components if c.strip()])
            
            # Генерируем вектор (1024 числа). Добавляем префикс 'query: ' — специфика моделей семейства e5
            embedding = model.encode(f"query: {text_for_ai}").tolist()
            
            # Записываем трек в базу данных
            cur.execute("""
                INSERT INTO tracks (
                    playlist_number, track_number, file_path, title, artist, album, 
                    composer, genre, style, form, instrument, period, mood, recording_date, embedding
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (playlist_number, track_number) DO UPDATE SET 
                    file_path = EXCLUDED.file_path,
                    title = EXCLUDED.title,
                    artist = EXCLUDED.artist,
                    album = EXCLUDED.album,
                    composer = EXCLUDED.composer,
                    genre = EXCLUDED.genre,
                    style = EXCLUDED.style,
                    form = EXCLUDED.form,
                    instrument = EXCLUDED.instrument,
                    period = EXCLUDED.period,
                    mood = EXCLUDED.mood,
                    recording_date = EXCLUDED.recording_date,
                    embedding = EXCLUDED.embedding;
            """, (
                pl_num, t_num, f_path,
                meta.get('title', ''), meta.get('artist', ''), meta.get('album', ''),
                meta.get('composer', ''), meta.get('genre', ''), meta.get('style', ''),
                meta.get('form', ''), meta.get('instrument', ''), meta.get('period', ''),
                meta.get('mood', ''), int(meta.get('date')) if meta.get('date') else None,
                embedding
            ))

    conn.commit()
    cur.close()
    conn.close()
    print("Импорт успешно завершен!")

if __name__ == "__main__":
    main()
