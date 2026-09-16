SELECT '# КАТАЛОГ МЕДИАТЕКИ' AS markdown_output
UNION ALL
SELECT 
    E'## 💿 Плейлист №' || playlist_number || E' — ' || playlist_title || E'\n' ||
    E'* **Жанр/Стиль:** ' || COALESCE(string_agg(DISTINCT style, ', '), 'Классика') || E'\n' ||
    E'* **Основные авторы:** ' || COALESCE(string_agg(DISTINCT composer, ', '), 'Не указан') || E'\n'
FROM tracks
GROUP BY playlist_number, playlist_title
ORDER BY playlist_number;

