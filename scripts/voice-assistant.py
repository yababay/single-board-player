#!/usr/bin/env python3
import os
import sys
import re
import wave
import json
import subprocess
import requests
from pathlib import Path
from dotenv import load_dotenv
from vosk import Model, KaldiRecognizer
from yargy.pipelines import morph_pipeline
from playlist_checker import check_playlist_phrase

# 1. Загрузка инфраструктуры и окружения
BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(dotenv_path=BASE_DIR / '.env')

FOLDER_ID = os.getenv("YC_FOLDER_ID")
API_KEY = os.getenv("YC_API_KEY")
VECTOR_STORE_ID = os.getenv("YC_VECTOR_STORE_ID")
MODEL_NAME = os.getenv("YC_MODEL_NAME")
ASSISTANT_ENDPOINT = os.getenv("YC_ASSISTANT_ENDPOINT")

# Локальные сетевые параметры ИИ-сервера
LOCAL_HOST = "127.0.0.1"
PORT_PATH = ":8080/search"
LOCAL_SEARCH_URL = f"http://{LOCAL_HOST}{PORT_PATH}"

# Файлы для записи звука. Vosk требует строго чистый RAW/WAV 16кГц Моно 16бит
AUDIO_RAW = "/tmp/voice_request.raw"
AUDIO_WAV = "/tmp/voice_request.wav"

def replace_words_with_digits(text):
    positive_word_list = ['плейлист', 'две', 'тысячи', 'двадцать']
    positive_rule = or_(rule(in_(positive_word_list)))
    positive_parser = Parser(positive_rule)
    positive_words = list(positive_parser.findall(text))
    return positive_words

def replace_words_with_digits_copilot(text):
    """Заменяет числительные после слова «плейлист» на число."""
    number_words = {
        "ноль": 0,
        "один": 1, "одна": 1, "одно": 1,
        "два": 2, "две": 2,
        "три": 3, "четыре": 4, "пять": 5,
        "шесть": 6, "семь": 7, "восемь": 8, "девять": 9,
        "десять": 10, "одиннадцать": 11, "двенадцать": 12,
        "тринадцать": 13, "четырнадцать": 14, "пятнадцать": 15,
        "шестнадцать": 16, "семнадцать": 17,
        "восемнадцать": 18, "девятнадцать": 19,
        "двадцать": 20, "тридцать": 30, "сорок": 40,
        "пятьдесят": 50, "шестьдесят": 60,
        "семьдесят": 70, "восемьдесят": 80, "девяносто": 90,
        "сто": 100, "двести": 200, "триста": 300,
        "четыреста": 400, "пятьсот": 500, "шестьсот": 600,
        "семьсот": 700, "восемьсот": 800, "девятьсот": 900,
    }

    number_pattern = "|".join(number_words)
    pattern = re.compile(
        rf"\bплейлист((?:\s+(?:{number_pattern}|тысяча|тысячи|тысяч))+)",
        re.IGNORECASE,
    )

    match = pattern.search(text)
    if not match:
        return ""

    total = 0
    current = 0

    for word in match.group(1).lower().split():
        if word in number_words:
            current += number_words[word]
        elif word in ("тысяча", "тысячи", "тысяч"):
            total += (current or 1) * 1000
            current = 0

    number = total + current

    start, end = match.span(1)
    return text[:start] + f" {number}" + text[end:]

def replace_words_with_digits_gemini(text):
    """
    Нормализует текст: находит русские слова-числа в любом падеже 
    и заменяет их на цифровые строки.
    'плейлист две тысячи двадцать' -> 'плейлист 2000 20'
    """
    NUM_MAP = {
        'ноль': '0', 'один': '1', 'два': '2', 'три': '3', 'четыре': '4', 'пять': '5', 'шесть': '6', 'семь': '7', 'восемь': '8', 'девять': '9',
        'первый': '1', 'второй': '2', 'третий': '3', 'четвертый': '4', 'пятый': '5', 'шестой': '6', 'седьмой': '7', 'восьмой': '8', 'девятый': '9',
        'десять': '10', 'одиннадцать': '11', 'двенадцать': '12', 'тринадцать': '13', 'четырнадцать': '14', 'пятнадцать': '15',
        'двадцать': '20', 'тридцать': '30', 'сорок': '40', 'пятьдесят': '50', 'шестьдесят': '60', 'семьдесят': '70', 'восемьдесят': '80', 'девяносто': '90',
        'сто': '100', 'двести': '200', 'триста': '300', 'четыреста': '400', 'пятьсот': '500', 'шестьсот': '600', 'семьсот': '700', 'восемьсот': '800', 'девятьсот': '900',
        'тысяча': '1000', 'тысячи': '1000', 'тысяч': '1000', 'две тысячи': '2000', 'три тысячи': '3000', 'четыре тысячи': '4000'
    }
    
    from yargy import Parser
    # Создаем парсер ОДИН РАЗ вне цикла
    pipeline = morph_pipeline(NUM_MAP)
    parser = Parser(pipeline)
    
    # Сканируем весь текст целиком. yargy найдет все числительные
    matches = list(parser.findall(text))
    if not matches:
        return text
        
    # Делаем замену слов на цифры с конца строки, чтобы не плыли индексы символов (классика старой школы)
    text_chars = list(text)
    for match in reversed(matches):
        # Вытаскиваем нормализованное словарное слово, которое сопоставилось
        # В yargy значение вытаскивается через сопоставление токена со словарем
        matched_word = match.tokens[0].value
        # Морфологический анализатор yargy приводит слово к нормальной форме
        normal_form = parser.analyzer(matched_word).normal
        
        if normal_form in NUM_MAP:
            digit_str = NUM_MAP[normal_form]
            # Заменяем кусок текста со словами на готовую цифру
            text_chars[match.span.start : match.span.end] = list(digit_str)
            
    return "".join(text_chars)

def record_audio():
    """Запись звука с отправкой нативного уведомления на рабочий стол"""
    # 🌟 ВИЗУАЛИЗАЦИЯ: Отправляем всплывающее окошко на экран десктопа
    # Параметры: заголовок, текст, иконка микрофона и время удержания 5000 мс (5 секунд)
    notify_start = (
        'notify-send -t 5000 -i audio-input-microphone '
        '"Голосовой ассистент" '
        '"Слушаю вас! У вас есть 5 секунд, чтобы озвучить свой запрос в микрофон."'
    )
    subprocess.run(notify_start, shell=True)

    print("=== Слушаю вашу команду (запись 5 секунд) ===", file=sys.stderr)
    
    # Записываем сырой поток (5 секунд)
    cmd_record = f"arecord -f cd -t raw -d 5 > {AUDIO_RAW}"
    subprocess.run(cmd_record, shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    
    if not os.path.exists(AUDIO_RAW) or os.path.getsize(AUDIO_RAW) == 0:
        print("Ошибка: Аудиофайл не записался.", file=sys.stderr)
        # Сообщаем об ошибке на экран, если микрофон отключен
        subprocess.run('notify-send -i dialog-error "Ошибка" "Микрофон не записал звук"', shell=True)
        sys.exit(1)
        
    # Конвертация в WAV моно для Vosk
    cmd_convert = f"ffmpeg -y -f s16le -ar 44100 -ac 2 -i {AUDIO_RAW} -ar 16000 -ac 1 {AUDIO_WAV}"
    subprocess.run(cmd_convert, shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    # 🌟 ВИЗУАЛИЗАЦИЯ ПОСЛЕ ЗАПИСИ: Меняем уведомление, чтобы пользователь понял, что запись кончилась
    # notify_processing = 'notify-send -t 2000 -i Очередь "Голосовой ассистент" "Запись окончена. Распознаю смысл..."'
    # subprocess.run(notify_processing, shell=True)

def recognize_speech_local():
    """Локальное распознавание речи на процессоре через Vosk"""
    print("Локальное распознавание речи через Vosk...", file=sys.stderr)
    
    current_dir = Path(__file__).resolve().parent
    model_path = str(current_dir / "models" / "vosk-model-small-ru")
    
    if not os.path.exists(model_path):
        print(f"Ошибка: Модель Vosk не найдена по пути {model_path}", file=sys.stderr)
        sys.exit(1)
        
    # Загружаем модель и настраиваем распознаватель под частоту 16000 Гц
    model = Model(model_path)
    wf = wave.open(AUDIO_WAV, "rb")
    rec = KaldiRecognizer(model, wf.getframerate())
    
    # Читаем и сканируем WAV-файл
    data = wf.readframes(wf.getnframes())
    wf.close()
    
    if rec.AcceptWaveform(data):
        res = json.loads(rec.Result())
    else:
        res = json.loads(rec.FinalResult())
        
    # Vosk возвращает текст в поле 'text'
    return res.get('text', '')

def clean_text_query(text):
    """Отсечение управляющих глаголов активации микрофона из кириллицы"""
    if not text:
        return ""
    text = text.lower().strip()
    # Используем чистый \s+ вместо [[:space:]]*, чтобы убрать предупреждения Python
    text = re.sub(r'^(найди|найти|включи|поставь|вруби|запусти|слушаю|хочу_послушать|хочу\s+послушать)\s*', '', text)
    return text.strip(', ')

def control_mpc(playlist_num, track_num):
    """Физическое выполнение команд переключения трека в mpc"""
    formatted_num = f"{int(playlist_num):04d}"
    try:
        playlists_list = subprocess.check_output("mpc lsplaylists", shell=True, text=True).splitlines()
        target_playlist = None
        for pl in playlists_list:
            if re.match(rf'^{formatted_num}-', pl):
                target_playlist = pl
                break
                
        if not target_playlist:
            print(f"Ошибка: Плейлист {formatted_num} не найден в базе MPD.", file=sys.stderr)
            sys.exit(1)
            
        print(f"Запуск плеера: {target_playlist} ➡️ Трек №{track_num}", file=sys.stderr)
        subprocess.run("mpc clear", shell=True, stdout=subprocess.DEVNULL)
        subprocess.run(f'mpc load "{target_playlist}"', shell=True, stdout=subprocess.DEVNULL)
        subprocess.run(f"mpc play {track_num}", shell=True, stdout=subprocess.DEVNULL)
    except Exception as e:
        print(f"Ошибка управления mpc: {e}", file=sys.stderr)
        sys.exit(1)

def main():
    # 🌟 АВТОМАТИЧЕСКИЙ ПРОГРЕВ ИИ-СЕРВЕРА СТАРТ
    print("Проверка готовности ИИ-сервера...", file=sys.stderr)
    
    # Отправляем легкий холостой запрос. Выставляем timeout=40 секунд, 
    # чтобы сервер успел не спеша прочитать все 1.3 ГБ весов с жесткого диска.
    try:
        ping_res = requests.get(LOCAL_SEARCH_URL, params={"query": "прогрев"}, timeout=140)
        ping_res.raise_for_status()
        print("ИИ-сервер успешно проснулся и готов к работе!", file=sys.stderr)
    except Exception as e:
        print(f"Ошибка прогрева сервера: {e}", file=sys.stderr)
        # Если сервер лежит намертво, выводим ошибку на экран и выходим
        subprocess.run('notify-send -i dialog-error "Сбой системы" "ИИ-сервер не отвечает на пинг"', shell=True)
        sys.exit(1)
    # 🌟 АВТОМАТИЧЕСКИЙ ПРОГРЕВ ИИ-СЕРВЕРА КОНЕЦ

    # Шаг 1. Теперь, когда сервер точно в ОЗУ, спокойно включаем микрофон и визуализацию
    record_audio()
    
    # Шаг 2. Распознаем речь на локальном процессоре (Vosk)
    raw_text = recognize_speech_local()
    print(f"Распознано локально (Vosk): \"{raw_text}\"", file=sys.stderr)
    
    # 🌟 БЫСТРЫЙ ПЕРЕХВАТ КОМАНД УПРАВЛЕНИЯ ПЛЕЕРОМ
    text_lower = raw_text.lower().strip()
    
    if any(word in text_lower for word in ['пауза', 'стоп', 'останови']):
        subprocess.run("mpc pause", shell=True)
        subprocess.run('notify-send -i media-playback-pause "Плеер" "Пауза"', shell=True)
        return
        
    if any(word in text_lower for word in ['играй', 'продолжи', 'сними с паузы']):
        subprocess.run("mpc play", shell=True)
        subprocess.run('notify-send -i media-playback-start "Плеер" "Воспроизведение"', shell=True)
        return
        
    if any(word in text_lower for word in ['следующий', 'вперед', 'дальше']):
        subprocess.run("mpc next", shell=True)
        subprocess.run('notify-send -i media-skip-forward "Плеер" "Следующий трек"', shell=True)
        return

    if any(word in text_lower for word in ['предыдущий', 'назад']):
        subprocess.run("mpc prev", shell=True)
        subprocess.run('notify-send -i media-skip-backward "Плеер" "Предыдущий трек"', shell=True)
        return
        
    if 'громче' in text_lower:
        subprocess.run("mpc volume +10", shell=True)
        return
        
    if 'тише' in text_lower:
        subprocess.run("mpc volume -10", shell=True)
        return

    # 🌟 ЛАКОНИЧНЫЙ АНАЛИЗ ЧИСЕЛ ЧЕРЕЗ РЕГУЛЯРКУ
    # Шаг 1. Переводим слова в цифры: "плейлист две тысячи двадцать" -> "плейлист 2000 20"
    #digitized_text = replace_words_with_digits(text_lower)
    #print(f"Текст после цифровой нормализации: \"{digitized_text}\"", file=sys.stderr)
    
    # Шаг 2. Ищем любые идущие подряд цифры регулярным выражением \d+
    numbers_found = check_playlist_phrase(text_lower)   #re.findall(r'\d+', digitized_text)
    
    if numbers_found:
        # Если найдено несколько чисел (например, '2000' и '20')
        #if len(numbers_found) == 2 and numbers_found[0].endswith('00'):
            # Специфика тысяч: 2000 + 20 = 2020
        #    detected_number = int(numbers_found[0]) + int(numbers_found[1])
        #else:
            # Для обычных чисел (например, '35') или если число одно
        #    detected_number = int("".join(numbers_found))
            
        print(f"Выделено число: {numbers_found}", file=sys.stderr)
        control_mpc(numbers_found, 1)
        return
        
        # Шаг 3. Защита от сонат: проверяем жесткие маркеры плейлиста
        #playlist_markers = ['плейлист', 'диск', 'альбом', 'номер', 'папка', 'загрузи', 'добавь']
        #if any(marker in digitized_text for marker in playlist_markers):
        #    print(f"🎯 Прямой вызов! Включаю плейлист №{detected_number}", file=sys.stderr)
        #else:
        #    print(f"Маркеры плейлиста не найдены (вероятно, это соната №{detected_number}). Ухожу в ИИ...", file=sys.stderr)

    # Если прямых команд на плейлист нет — шлем исходный текст на ИИ-сервер
    clean_text = clean_text_query(raw_text)
    # ... (дальше ваш стандартный код отправки на LOCAL_SEARCH_URL)
    # 🌟 КОНЕЦ БЛОКА БЫСТРЫХ КОМАНД

    # Шаг 3. Очищаем текст от мусорных глаголов
    clean_text = clean_text_query(raw_text)
    if not clean_text:
        print("Ошибка: Запрос пуст.", file=sys.stderr)
        sys.exit(1)
        
    # Шаг 4. Отправляем чистый текст на наш ЛОКАЛЬНЫЙ ИИ-сервер FastAPI
    # Здесь timeout можно вернуть к быстрым 10 секундам, ведь сервер уже прогрет!
    print(f"Запрос к локальному ИИ-серверу для: \"{clean_text}\"...", file=sys.stderr)
    try:
        response = requests.get(LOCAL_SEARCH_URL, params={"query": clean_text}, timeout=10)
        response.raise_for_status()
        srv_data = response.json()
        
        if srv_data.get("status") == "success":
            debug_msg = srv_data.get("debug_info")
            print(debug_msg, file=sys.stderr)
            
            ai_command = srv_data.get("command")
            pl_num, tr_num = ai_command.split(';')
            
            # Физически переключаем плеер mpc
            control_mpc(pl_num, tr_num)
            
            # Перехватываем теги из mpc
            try:
                mpc_output = subprocess.check_output("mpc", shell=True, text=True).splitlines()
                current_track = mpc_output[0].strip() if mpc_output else "Воспроизведение запущено"
            except Exception:
                current_track = "Воспроизведение запущено"
            
            # Итоговая визуализация на экране
            notify_final = (
                f'notify-send -t 6000 -i media-playlist-music '
                f'"Вы сказали: «{raw_text}»" '
                f'"{current_track}"'
            )
            subprocess.run(notify_final, shell=True)
            
        else:
            print("Локальный ИИ ничего не нашёл.", file=sys.stderr)
            subprocess.run(f'notify-send -i dialog-warning "Локальный ИИ" "Не удалось подобрать трек для: «{raw_text}»"', shell=True)
    except Exception as e:
        print(f"Ошибка связи с локальным ИИ-сервером: {e}", file=sys.stderr)
        sys.exit(1)
        
    # Чистим временные файлы в /tmp
    for f in [AUDIO_RAW, AUDIO_WAV]:
        if os.path.exists(f):
            os.remove(f)

if __name__ == "__main__":
    main()
