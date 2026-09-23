DO $$
DECLARE
    r_playlist RECORD;
    r_track RECORD;
    current_cat INT := 0;
    playlist_cat INT;
BEGIN
    -- На всякий случай выводим в stdout уведомление
    RAISE NOTICE 'Генерация каталога фонотеки в формате Markdown...';
    
    -- Цикл 1: Идем по уникальным номерам плейлистов, отсортированным по возрастанию (пропускаем < 1000)
    FOR r_playlist IN 
        SELECT DISTINCT playlist_number, 
               -- Пытаемся найти текстовое имя из mpc/файлов, если его нет — выводим красивую заглушку
               COALESCE(album, 'Плейлист ' || playlist_number) as playlist_name
        FROM tracks 
        WHERE playlist_number >= 1000
        ORDER BY playlist_number ASC
    LOOP
        -- Вычисляем базу раздела (1000, 2000, 3000, 4000)
        playlist_cat := (r_playlist.playlist_number / 1000) * 1000;
        
        -- Если перешли в новый раздел — печатаем главный заголовок
        IF playlist_cat <> current_cat THEN
            current_cat := playlist_cat;
            RAISE INFO '';
            IF current_cat = 1000 THEN RAISE INFO '# Классическая музыка';
            ELSIF current_cat = 2000 THEN RAISE INFO '# Рок-музыка';
            ELSIF current_cat = 3000 THEN RAISE INFO '# Джаз';
            ELSIF current_cat = 4000 THEN RAISE INFO '# Блюз';
            ELSE RAISE INFO '# Раздел %000', (current_cat / 1000);
            END IF;
            RAISE INFO '';
        END IF;
        
        -- Печатаем заголовок плейлиста (номер и имя)
        -- Пока e5 выключена и имена файлов не подтянуты, префикс сгенерируем по вашему стандарту
        RAISE INFO '## %-%', r_playlist.playlist_number, lower(regexp_replace(r_playlist.playlist_name, '[^a-zA-Z0-9а-яА-Я]+', '-', 'g'));
        RAISE INFO '';
        
        -- Цикл 2: Вложенный обход всех треков внутри текущего плейлиста
        FOR r_track IN 
            SELECT track_number, title, artist 
            FROM tracks 
            WHERE playlist_number = r_playlist.playlist_number
            ORDER BY track_number ASC
        LOOP
            -- Выводим трек в формате маркированного списка Markdown
            RAISE INFO '* % - %', r_track.artist, r_track.title;
        END LOOP;
        
        RAISE INFO '';
    END LOOP;
END $$;

