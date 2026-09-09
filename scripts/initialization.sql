-- Таблица плейлистов (соответствует верхнему уровню вашего YAML)
CREATE TABLE playlists (
    playlist_number INT PRIMARY KEY,    -- Номер плейлиста (например, 1057)
    playlist_title TEXT NOT NULL         -- Очищенное название (1057-orama-prokofiev-visions)
);

-- Таблица треков со всеми семантическими полями и вектором
CREATE TABLE tracks (
    id SERIAL PRIMARY KEY,
    playlist_number INT REFERENCES playlists(playlist_number) ON DELETE CASCADE,
    track_number INT NOT NULL,          -- Номер трека внутри плейлиста (для mpc play)
    file_path TEXT NOT NULL,            -- Путь к файлу на диске
    
    -- Семантические текстовые метаданные
    title TEXT NOT NULL,
    artist TEXT,
    album TEXT,
    composer TEXT,
    genre TEXT,
    style TEXT,
    form TEXT,
    instrument TEXT,
    period TEXT,
    mood TEXT,                          -- Будущее поле для текстовых настроений
    recording_date INT,                 -- Год записи (как число)
    release_year INT,                   -- Год релиза (как число)
    comment TEXT,
    
    -- Векторное поле для ИИ-поиска по смыслам и настроениям.
    -- Размерность 1024 подходит для современных бесплатных векторных моделей (например, семейства e5 или мультиязычных моделей от Яндекс/Сбер).
    embedding vector(1024),
    
    -- Ограничение, чтобы не было дублей треков в рамках одного плейлиста
    UNIQUE(playlist_number, track_number)
);

-- Индекс для классического текстового поиска (B-Tree)
CREATE INDEX idx_tracks_search ON tracks(artist, composer, album);

-- Индекс для мгновенного векторного поиска (HNSW - Hierarchical Navigable Small World)
-- Использует косинусное расстояние (cosine), идеальное для текстовых смыслов
CREATE INDEX idx_tracks_embedding ON tracks USING hnsw (embedding vector_cosine_ops);
