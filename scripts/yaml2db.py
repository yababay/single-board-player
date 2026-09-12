#!/usr/bin/env python3
import sys
import os
import yaml
import requests
import psycopg2
from pathlib import Path
from dotenv import load_dotenv

def main():
    # Загружаем настройки из .env в корне проекта
    BASE_DIR = Path(__file__).resolve().parent.parent
    load_dotenv(dotenv_path=BASE_DIR / '.env')
    
    # Конфигурация локального сетевого пути (защита от фильтров)
    LOCAL_HOST = "127.0.0.1"
    PORT_PATH = f":8080/embed"
    EMBED_URL = f"http://{LOCAL_HOST}{PORT_PATH}"
    PG_USER = os.getenv("PG_USER", "postgres")
    PG_PASSWORD = os.getenv("PG_PASSWORD", "")
    PG_DATABASE = os.getenv("PG_DATABASE", "player")

    # Читаем YAML из stdin
    try:
        raw_data = sys.stdin.read()
        if not raw_data.strip():
            return
        data = yaml.safe_load(raw_data)
    except Exception as e:
        print(f"Ошибка парсинга YAML: {e}", file=sys.stderr)
        return

    if not data or 'playlists' not in data:
        return

    # Подключаемся к PostgreSQL 17
    try:
        conn = psycopg2.connect(f"dbname={PG_DATABASE} user={PG_USER} password={PG_PASSWORD} host=localhost")
        cur = conn.cursor()
    except Exception as e:
        print(f"Ошибка подключения к PostgreSQL: {e}", file=sys.stderr)
        sys.exit(1)

    for pl in data.get('playlists', []):
        pl_num = pl.get('playlist_number')
        pl_title = pl.get('playlist_title')
        if not pl_num or not pl_title:
            continue
            
        cur.execute(
            "INSERT INTO playlists (playlist_number, playlist_title) VALUES (%s, %s) ON CONFLICT (playlist_number) DO UPDATE SET playlist_title = EXCLUDED.playlist_title;",
            (pl_num, pl_title)
        )
        print(f"--> Локальный импорт плейлиста {pl_num}: {pl_title}")
        
        for track in pl.get('tracks', []):
            t_num = track.get('track_number')
            f_path = track.get('file_path')
            meta = track.get('metadata', {})
            if not t_num or not f_path:
                continue
            
            # Собираем текстовое ядро для ИИ
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
            
            # 🌟 МАГИЯ: Запрашиваем вектор у нашего локального запущенного сервера
            try:
                srv_res = requests.get(EMBED_URL, params={"text": text_for_ai}, timeout=50)
                srv_res.raise_for_status()
                embedding = srv_res.json()["embedding"]
            except Exception as e:
                print(f"Ошибка обращения к локальному ИИ-серверу: {e}", file=sys.stderr)
                sys.exit(1)
            
            # Записываем в БД
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

if __name__ == "__main__":
    main()
