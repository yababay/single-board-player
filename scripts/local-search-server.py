#!/usr/bin/env python3
import os
import re
import sys
from pathlib import Path
import psycopg2
from fastapi import FastAPI, HTTPException
import uvicorn
from sentence_transformers import SentenceTransformer
from dotenv import load_dotenv

# Загружаем настройки базы данных из .env в корне проекта
BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(dotenv_path=BASE_DIR / '.env')

PG_USER = os.getenv('PG_USER', 'mabel')
PG_PASSWORD = os.getenv('PG_PASSWORD', '')
PG_DATABASE = os.getenv('PG_DATABASE', 'player')

app = FastAPI(title="Local Music AI Search Server")

# Глобальные переменные для модели и подключения к БД
model = None
db_conn = None

@app.on_event("startup")
def startup_event():
    global model, db_conn
    print("Инициализация локального микросервиса...", file=sys.stderr)
    print("Загрузка ИИ-модели из ЛОКАЛЬНОЙ папки (офлайн-режим)...", file=sys.stderr)
    
    # 🌟 МАГИЯ ОФЛАЙНА: Запрещаем библиотекам обращаться к интернету (Hugging Face)
    os.environ["HF_HUB_DISABLE_SYMLINKS_WARNING"] = "1"
    os.environ["TRANSFORMERS_OFFLINE"] = "1"
    os.environ["HF_HUB_OFFLINE"] = "1"
    
    # Вычисляем точный путь к сохраненной модели внутри нашего проекта
    current_dir = Path(__file__).resolve().parent
    local_model_path = str(current_dir / "models" / "multilingual-e5-large")
    
    # Загружаем модель строго по локальному пути
    model = SentenceTransformer(local_model_path)
    
    print("Подключение к локальной PostgreSQL 17...", file=sys.stderr)
    try:
        # Подключаемся к вашей локальной базе данных player
        db_conn = psycopg2.connect(f"dbname={PG_DATABASE} user={PG_USER} password={PG_PASSWORD} host=localhost")
        print("💡 Локальный ИИ-сервис успешно запущен и готов к работе!", file=sys.stderr)
    except Exception as e:
        print(f"Критическая ошибка подключения к БД: {e}", file=sys.stderr)
        sys.exit(1)

@app.on_event("shutdown")
def shutdown_event():
    """Выполняется при закрытии сервера (Ctrl+C)"""
    global db_conn
    if db_conn:
        db_conn.close()
    print("Локальный сервис остановлен, память очищена.", file=sys.stderr)

@app.get("/search")
def search(query: str):
    """Эндпоинт для мгновенного семантического поиска"""
    global model, db_conn
    if not query.strip():
        raise HTTPException(status_code=400, detail="Пустой запрос")
        
    # Очищаем текст от мусорных команд управления
    clean_query = query.lower().strip()
    clean_query = re.sub(r'^(найди|включи|поставь|вруби|запусти|хочу_послушать|хочу[[:space:]]+послушать)[[:space:]]*', '', clean_query)
    
    # 1. Мгновенная генерация вектора (занимает сотые доли секунды, так как модель в памяти)
    # Используем обязательный префикс 'query: ' для моделей семейства e5
    query_embedding = model.encode(f"query: {clean_query}").tolist()
    
    # 2. Мгновенный векторный поиск в локальной PostgreSQL 17
    try:
        cur = db_conn.cursor()
        cur.execute("""
            SELECT playlist_number, track_number, title, composer, style
            FROM tracks 
            ORDER BY embedding <=> %s::vector 
            LIMIT 1;
        """, (query_embedding,))
        
        result = cur.fetchone()
        cur.close()
        
        if result:
            pl_num, tr_num, title, composer, style = result
            # Возвращаем JSON с результатом поиска
            return {
                "status": "success",
                "command": f"{pl_num};{tr_num}",
                "debug_info": f"[Найдено]: {composer} - {title} ({style})"
            }
        else:
            return {"status": "not_found", "command": "", "debug_info": "Ничего не найдено"}
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка базы данных: {e}")

@app.get("/embed")
def get_embedding(text: str):
    """Новый эндпоинт для моментального расчета вектора без перезагрузки модели"""
    global model
    if not text.strip():
        raise HTTPException(status_code=400, detail="Пустой текст")
    # Генерируем вектор из модели, которая УЖЕ сидит в оперативной памяти
    embedding = model.encode(f"query: {text}").tolist()
    return {"embedding": embedding}

if __name__ == "__main__":
    # Запускаем локальный веб-сервер на порту 8080
    uvicorn.run(app, host="127.0.0.1", port=8080, log_level="warning")
