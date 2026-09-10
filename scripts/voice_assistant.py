#!/usr/bin/env python3
import os
import sys
import re
import subprocess
import requests
from pathlib import Path
from dotenv import load_dotenv

# 1. Загрузка инфраструктуры и окружения
# Ищем .env на один уровень выше директории скрипта (в корне проекта)
BASE_DIR = Path(__file__).resolve().parent.parent
ENV_PATH = BASE_DIR / '.env'
load_dotenv(dotenv_path=ENV_PATH)

debug_mode = os.getenv("DEBUG_MODE", "false").lower() == "true"

# Константы из окружения
FOLDER_ID = os.getenv("YC_FOLDER_ID")
IAM_TOKEN = os.getenv("YC_IAM_TOKEN")
API_KEY = os.getenv("YC_API_KEY")
VECTOR_STORE_ID = os.getenv("YC_VECTOR_STORE_ID")
MODEL_NAME = os.getenv("YC_MODEL_NAME")
STT_ENDPOINT = os.getenv("YC_STT_ENDPOINT")
ASSISTANT_ENDPOINT = os.getenv("YC_ASSISTANT_ENDPOINT")

AUDIO_FILE = "/tmp/voice_request.ogg"

# Жестко вшитый системный промпт — больше никаких внешних txt-файлов
SYSTEM_INSTRUCTIONS = """Ты — строгий музыкальный ассистент-контроллер. Пользователь ищет конкретное музыкальное произведение по его описанию. Твоя задача — найти точную строку в подключенном поисковом индексе.

СТРОГИЕ ПРАВИЛА ПРИОРИТЕТА:
1. Если пользователь называет имя автора, модель должна определить его роль:
   - Если это композитор (Бах, Куртаг, Прокофьев, Чайковский), приоритет поиска ВСЕГДА отдается полю "Композитор: [Имя]".
   - Если это исполнитель или дирижер (Ван Клиберн, Владимир Софроницкий, Сакари Орамо), приоритет поиска ВСЕГДА отдается полю "Исполнитель: [Имя]".
   - Поиск по названию альбома и другим полям выполняется только в том случае, если по главным полям (Композитор/Исполнитель) совпадений не найдено.
2. Не выдавай трек другого автора только потому, что искомое слово упоминается в названии поля "Альбом:". Выдавать трек другого композитора разрешено ТОЛЬКО в случае, если произведений искомого автора вообще нет в базе данных.
3. Если пользователь указал музыкальную форму (например, "ноктюрн", "вальс", "этюд", "соната"), ты ОБЯЗАН найти строку, где в поле "Форма:" или "Название:" указан именно этот жанр. Запрещено выдавать вальс, если пользователь просил ноктюрн.
4. Каждый запрос изолирован. Полностью забудь все свои предыдущие ответы в этом диалоге и не пытайся их повторять.

### ФОРМАТ ОТВЕТА: 
В ответ выдай СТРОГО два числа, разделенные точкой с запятой из поля "Команда: [код]". Запрещено писать любые вводные слова, пояснения, комментарии, знаки препинания или кавычки. Только две цифры и точка с запятой между ними (например: 1052;8)."""

def record_audio():
    """Запись звука стабильным stereo-методом и сжатие в OGG через oggenc"""
    print("=== Слушаю вашу команду (запись 5 секунд) ===", file=sys.stderr)
    cmd = f"arecord -f cd -t raw -d 5 | oggenc - -r -o {AUDIO_FILE}"
    subprocess.run(cmd, shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    
    if not os.path.exists(AUDIO_FILE) or os.path.getsize(AUDIO_FILE) == 0:
        print("Ошибка: Аудиофайл не записался.", file=sys.stderr)
        sys.exit(1)
    # if debug_mode:
    #    print(f"DEBUG: Аудиофайл записан в {AUDIO_FILE} (размер {os.path.getsize(AUDIO_FILE)} байт)", file=sys.stderr)
    #    sys.exit(0)  # В режиме отладки останавливаемся после записи аудио

def recognize_speech():
    """Отправка ogg-файла в Yandex SpeechKit STT"""
    print("Распознавание речи через Yandex SpeechKit...", file=sys.stderr)
    
    url = f"{STT_ENDPOINT}?topic=general&lang=ru-RU&folderId={FOLDER_ID}"
    headers = {
        "Authorization": f"Bearer {IAM_TOKEN}",
        "Content-Type": "audio/ogg"
    }
    
    try:
        with open(AUDIO_FILE, 'rb') as f:
            response = requests.post(url, headers=headers, data=f, timeout=15)
        
        response.raise_for_status()
        result = response.json()
        return result.get('result', '')
    except Exception as e:
        print(f"Ошибка SpeechKit API: {e}", file=sys.stderr)
        if 'response' in locals():
            print(response.text, file=sys.stderr)
        sys.exit(1)

def clean_and_deduplicate_text(text):
    """Исправление дублирования аппаратуры, перевод в нижний регистр и отсечение глаголов"""
    if not text:
        return ""
        
    text = text.lower().strip()
    
    # 1. Лечим склейку Stereo-дубликата ("найди ноктюрн шопена найди ноктюрн шопена")
    # Ищем повторяющуюся последовательность слов
    words = text.split()
    n = len(words)
    if n % 2 == 0:
        half = n // 2
        if words[:half] == words[half:]:
            text = " ".join(words[:half])
            
    # 2. Вырезаем управляющие глаголы активации микрофона
    text = re.sub(r'^(найди|включи|поставь|вруби|запусти|слушаю|хочу_послушать|хочу[[:space:]]+послушать)[[:space:]]*', '', text)
    return text.strip(', ')

def search_in_ai_studio(query_text):
    """Поиск по RAG-индексу в Yandex AI Studio через Responses API"""
    print(f"Поиск музыкального смысла в облаке для: \"{query_text}\"...", file=sys.stderr)
    
    headers = {
        "Authorization": f"Api-Key {API_KEY}",
        "Content-Type": "application/json",
        "x-project": FOLDER_ID
    }
    
    payload = {
        "model": f"gpt://{FOLDER_ID}/{MODEL_NAME}",
        "instructions": SYSTEM_INSTRUCTIONS,
        "tools": [{"type": "file_search", "vector_store_ids": [VECTOR_STORE_ID]}],
        "input": query_text
    }
    
    try:
        response = requests.post(ASSISTANT_ENDPOINT, headers=headers, json=payload, timeout=15)
        response.raise_for_status()
        raw_response = response.text
        
        # Сканируем регулярным выражением абсолютно весь прилетевший JSON (включая блок summary)
        match = re.search(r'(\d+)\;(\d+)', raw_response)
        if match:
            return f"{match.group(1)};{match.group(2)}"
        else:
            print("Ошибка ИИ: В ответе Яндекса не обнаружен технический формат команды.", file=sys.stderr)
            print(f"Сырой ответ сервера: {raw_response}", file=sys.stderr)
            sys.exit(1)
            
    except Exception as e:
        print(f"Ошибка AI Studio API: {e}", file=sys.stderr)
        sys.exit(1)

def control_mpc(playlist_num, track_num):
    """Физическое выполнение команд переключения трека в mpc"""
    # Форматируем номер с лидирующими нулями до 4 знаков (например, "58" -> "0058")
    formatted_num = f"{int(playlist_num):04d}"
    
    # Ищем точное имя плейлиста в mpd (якорь ^ гарантирует защиту от коллизий вроде 57 и 1057)
    try:
        playlists_list = subprocess.check_output("mpc lsplaylists", shell=True, text=True).splitlines()
        target_playlist = None
        
        for pl in playlists_list:
            if re.match(rf'^{formatted_num}-', pl):
                target_playlist = pl
                break
                
        if not target_playlist:
            print(f"Ошибка: Плейлист под номером {formatted_num} не обнаружен в MPD.", file=sys.stderr)
            sys.exit(1)
            
        print(f"Запуск плеера: {target_playlist} ➡️ Трек №{track_num}", file=sys.stderr)
        
        # Выполняем цепочку mpc-команд
        subprocess.run("mpc clear", shell=True, stdout=subprocess.DEVNULL)
        subprocess.run(f'mpc load "{target_playlist}"', shell=True, stdout=subprocess.DEVNULL)
        subprocess.run(f"mpc play {track_num}", shell=True, stdout=subprocess.DEVNULL)
        
    except Exception as e:
        print(f"Ошибка управления mpc: {e}", file=sys.stderr)
        sys.exit(1)

def main():
    # Шаг 1. Записываем голос
    record_audio()
    
    # Шаг 2. Переводим голос в сырой текст
    raw_text = recognize_speech()
    print(f"Распознано SpeechKit: \"{raw_text}\"", file=sys.stderr)
    
    #if debug_mode:
    #    print("DEBUG: Режим отладки включен. Останавливаемся после распознавания речи.", file=sys.stderr)
    #    sys.exit(0)

    # Шаг 3. Дедуплицируем стерео-сбои и чистим кириллицу от глаголов
    clean_text = clean_and_deduplicate_text(raw_text)
    if not clean_text:
        print("Ошибка: После очистки запроса не осталось значимых слов.", file=sys.stderr)
        sys.exit(1)

    #if debug_mode:
    #    print(f"DEBUG: Чистый текст после дедупликации и очистки: \"{clean_text}\"", file=sys.stderr)
    #    sys.exit(0)  # В режиме отладки останавливаемся после очистки текста

    # Шаг 4. Шлем чистый смысл в RAG-индекс Яндекса
    ai_command = search_in_ai_studio(clean_text)
    
    # Шаг 5. Расщепляем полученную команду и переключаем mpc
    pl_num, tr_num = ai_command.split(';')
    control_mpc(pl_num, tr_num)
    
    # Чистим за собой временный аудиофайл
    if os.path.exists(AUDIO_FILE):
        os.remove(AUDIO_FILE)

if __name__ == "__main__":
    main()
