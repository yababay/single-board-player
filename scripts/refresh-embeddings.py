#!/usr/bin/env python3
import sys
import os
import hashlib
import psycopg2
from pathlib import Path
from dotenv import load_dotenv
from sentence_transformers import SentenceTransformer

# Жестко переводим библиотеки ИИ в локальный офлайн-режим
os.environ["TRANSFORMERS_OFFLINE"] = "1"
os.environ["HF_HUB_OFFLINE"] = "1"

# 🌟 НАСТРОЙКА ИНФРАСТРУКТУРЫ ОКРУЖЕНИЯ
BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(dotenv_path=BASE_DIR / '.env')

# Считываем параметры из .env с безопасными дефолтами
PG_USER = os.getenv('PG_USER', 'mabel')
PG_PASSWORD = os.getenv('PG_PASSWORD', '')
PG_DATABASE = os.getenv('PG_DATABASE', 'player')

LOCAL_MODEL_PATH = str(BASE_DIR / "scripts" / "models" / "multilingual-e5-large")

def make_ai_text(title, artist, album, genre, style, form):
    """Сборка монолитной смысловой строки для ИИ-эмбеддера (канон нашего проекта)"""
    parts = []
    if title: parts.append(f"Название: {title}")
    if artist: parts.append(f"Исполнитель: {artist}")
    if album: parts.append(f"Альбом: {album}")
    if genre: parts.append(f"Жанр: {genre}")
    if style: parts.append(f"Стиль: {style}")
    if form: parts.append(f"Форма: {form}")
    return " ; ".join(parts)

def main():
    print(f"🔌 Подключение к PostgreSQL (База: {PG_DATABASE}, Пользователь: {PG_USER})...", file=sys.stderr)
    try:
        # 🌟 ДИНАМИЧЕСКИЙ КОННЕКТ ИЗ ВАШИХ ПЕРЕМЕННЫХ
        conn = psycopg2.connect(
            dbname=PG_DATABASE, 
            user=PG_USER, 
            password=PG_PASSWORD, 
            host="localhost"
        )
        cur = conn.cursor()
    except Exception as e:
        print(f"❌ Ошибка подключения к БД: {e}", file=sys.stderr)
        sys.exit(1)

    print("🧠 Загрузка локальной ИИ-модели multilingual-e5-large...", file=sys.stderr)
    if not os.path.exists(LOCAL_MODEL_PATH):
        print(f"❌ Ошибка: Локальная модель не найдена по пути {LOCAL_MODEL_PATH}", file=sys.stderr)
        sys.exit(1)
    model = SentenceTransformer(LOCAL_MODEL_PATH)

    # Теперь в main() вместо выкачивания всей базы мы пишем лаконичный запрос:
    cur.execute("""
        SELECT id, title, artist, album, genre, style, form 
        FROM tracks 
        WHERE embedding IS NULL;
    """)
    rows = cur.fetchall()
    
    print(f"Сканирование таблицы tracks. Всего записей: {len(rows)}", file=sys.stderr)
    
    # Списки для пачковой обработки (батчинга)
    tracks_to_update = []
    texts_to_encode = []

    for row in rows:
        db_id, pl_num, tr_num, title, artist, album, genre, style, form, old_hash = row
        
        # 1. Собираем живой текст и его хэш
        current_text = make_ai_text(title, artist, album, genre, style, form)
        current_hash = hashlib.md5(current_text.encode('utf-8')).hexdigest()
        
        # 2. Если хэш изменился — запоминаем эту строку для пересчета
        if current_hash != old_hash:
            tracks_to_update.append({
                'id': db_id,
                'pl_num': pl_num,
                'tr_num': tr_num,
                'artist': artist,
                'title': title,
                'hash': current_hash
            })
            texts_to_encode.append(current_text)

    if not tracks_to_update:
        print("\n🎉 Все векторы в базе данных находятся в актуальном состоянии! Пересчёт не требуется.", file=sys.stderr)
        cur.close()
        conn.close()
        return

    print(f"\n🔄 Найдено изменений в тексте: {len(tracks_to_update)} треков. Начинаю генерацию векторов...", file=sys.stderr)
    
    # Генерируем векторы сразу для всей пачки (это работает в разы быстрее!)
    # model.encode возвращает двумерную матрицу, где каждая строка — это одномерный вектор трека
    embeddings = model.encode(texts_to_encode, batch_size=32, show_progress_bar=True)

    print("✍️ Запись обновленных векторов в PostgreSQL...", file=sys.stderr)
    for i, track in enumerate(tracks_to_update):
        # Превращаем i-ю строку матрицы в чистый одномерный список чисел для pgvector
        single_embedding = embeddings[i].tolist()
        
        cur.execute("""
            UPDATE tracks 
            SET embedding = %s, meta_hash = %s 
            WHERE id = %s;
        """, (single_embedding, track['hash'], track['id']))
        
        if (i + 1) % 50 == 0:
            conn.commit()
            print(f"Зафиксировано: {i + 1}/{len(tracks_to_update)} треков...", file=sys.stderr)

    conn.commit()
    cur.close()
    conn.close()
    
    print(f"\n🎉 Синхронизация успешно завершена! База данных полностью обновлена.", file=sys.stderr)

if __name__ == "__main__":
    main()
