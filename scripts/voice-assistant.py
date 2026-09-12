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
    # Шаг 1. Записываем звук и аппаратно конвертируем в моно через ffmpeg
    record_audio()
    
    # Шаг 2. Распознаем речь на локальном процессоре
    raw_text = recognize_speech_local()
    print(f"Распознано локально (Vosk): \"{raw_text}\"", file=sys.stderr)
    
    # Шаг 3. Очищаем текст от мусорных глаголов
    clean_text = clean_text_query(raw_text)
    if not clean_text:
        print("Ошибка: Запрос пуст.", file=sys.stderr)
        sys.exit(1)
        
    # Шаг 4. Отправляем чистый текст на наш ЛОКАЛЬНЫЙ ИИ-сервер FastAPI
    print(f"Запрос к локальному ИИ-серверу для: \"{clean_text}\"...", file=sys.stderr)
    try:
        # ... в функции main() измените строку запроса:
        response = requests.get(LOCAL_SEARCH_URL, params={"query": clean_text}, timeout=30)
        # response = requests.get(LOCAL_SEARCH_URL, params={"query": clean_text}, timeout=10)
        response.raise_for_status()
        srv_data = response.json()
        
        if srv_data.get("status") == "success":
            debug_msg = srv_data.get("debug_info")
            print(debug_msg, file=sys.stderr)
            
            ai_command = srv_data.get("command")
            pl_num, tr_num = ai_command.split(';')
            
            # Сначала физически переключаем плеер mpc
            control_mpc(pl_num, tr_num)
            
            # 🌟 ПЕРЕХВАТ ТЕГОВ ИЗ MPC:
            # Вызываем mpc без параметров — он возвращает три строки:
            # 1. Текущий трек (Автор - Название)
            # 2. Статус ([playing] #3/3 ...)
            # 3. Настройки (volume: ...)
            try:
                mpc_output = subprocess.check_output("mpc", shell=True, text=True).splitlines()
                if mpc_output:
                    # Берем самую первую строчку — это и есть играющий сейчас трек
                    current_track = mpc_output[0].strip()
                else:
                    current_track = "Воспроизведение запущено"
            except Exception:
                current_track = "Воспроизведение запущено"
            
            # 🌟 ИТОГОВАЯ ВИЗУАЛИЗАЦИЯ:
            # Выводим на экран красивое окно:
            # Заголовок: Что услышал Vosk (например: "Вы сказали: второй концерт рахманинова")
            # Текст: Что сейчас заиграло в колонках (из тегов mpc)
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
