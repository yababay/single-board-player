#!/usr/bin/env python3
import os
import sys
import psycopg2
from sentence_transformers import SentenceTransformer
from dotenv import load_dotenv

load_dotenv()  # This loads the variables from the .env file into os.environ
pg_user = os.getenv('PG_USER')
pg_password = os.getenv('PG_PASSWORD')
pg_database = os.getenv('PG_DATABASE')

def main():
    # 1. Считываем текстовый запрос пользователя
    if len(sys.argv) < 2:
        print("Использование: ./search_music.py \"ваш запрос на естественном языке\"", file=sys.stderr)
        sys.exit(1)
        
    user_query = " ".join(sys.argv[1:])

    # 2. Подключаем локальную ИИ-модель
    # Она возьмет файлы из кэша мгновенно, ничего скачивать больше не будет
    model = SentenceTransformer('intfloat/multilingual-e5-large')

    # 3. Генерируем вектор для запроса (важно использовать префикс 'query: ')
    query_embedding = model.encode(f"query: {user_query}").tolist()

    # 4. Подключаемся к PostgreSQL 17
    try:
        conn = psycopg2.connect(f"dbname={pg_database} user={pg_user} password={pg_password} host=localhost")
        cur = conn.cursor()
    except Exception as e:
        print(f"Ошибка БД: {e}", file=sys.stderr)
        sys.exit(1)

    # 5. Делаем векторный запрос через оператор <=> (косинусное расстояние)
    # HNSW-индекс в базе мгновенно найдет самый близкий по смыслу трек
    cur.execute("""
        SELECT playlist_number, track_number, title, composer, style
        FROM tracks 
        ORDER BY embedding <=> %s::vector 
        LIMIT 1;
    """, (query_embedding,))

    result = cur.fetchone()

    cur.close()
    conn.close()

    if result:
        pl_num, tr_num, title, composer, style = result
        
        # Выводим техническую строку для ESP32 / MPC в stdout
        print(f"{pl_num};{tr_num}")
        
        # Дублируем человекочитаемую отладочную информацию в stderr, чтобы не засорять вывод
        print(f"[Найдено]: {composer} - {title} ({style})", file=sys.stderr)
    else:
        print("Ничего не найдено", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
