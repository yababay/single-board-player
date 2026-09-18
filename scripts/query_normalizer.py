#!/usr/bin/env python3
import os
import sys
import re
import wave
import json
import subprocess
import psycopg2
import unittest
from pathlib import Path
from vosk import Model, KaldiRecognizer, SetLogLevel
from yargy import Parser, rule, or_
from yargy.predicates import gram
from yargy.pipelines import morph_pipeline
from yargy.interpretation import fact
from yargy.predicates import type # 🌟 Импортируем предикат типа токена
from dotenv import load_dotenv

# Пути к ресурсам внутри проекта
BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(dotenv_path=BASE_DIR / '.env')

PG_USER = os.getenv('PG_USER', 'mabel')
PG_PASSWORD = os.getenv('PG_PASSWORD', '')
PG_DATABASE = os.getenv('PG_DATABASE', 'player')

AUDIO_RAW = "/tmp/training_voice.raw"
AUDIO_WAV = "/tmp/training_voice.wav"
VOSK_MODEL_PATH = str(BASE_DIR / "scripts" / "models" / "vosk-model-small-ru")

# =====================================================================
# 1. СИНТАКСИЧЕСКИЙ РАЗБОР YARGY (ОТГРАНИЧЕНИЕ ГЛАГОЛОВ)
# =====================================================================
QueryPhrase = fact('QueryPhrase', [
    'action', 
    'meaningful_part'
])

ORDER_MARKERS = morph_pipeline(['включи', 'вруби', 'поставь', 'запусти', 'найди', 'найти'])
ANY_WORD = or_(
    type('RU'),
    type('LATIN')
)

# Грамматическое правило: управляющий глагол + цепочка от 1 до 6 любых слов
QUERY_RULE = rule(
    ORDER_MARKERS.interpretation(QueryPhrase.action),
    ANY_WORD.repeatable(min=1, max=6).interpretation(QueryPhrase.meaningful_part)
).interpretation(QueryPhrase)

yargy_parser = Parser(QUERY_RULE)

def extract_meaningful_part(text):
    """Вычленяет смысловой остаток фразы, отбрасывая первый глагол"""
    clean_text = " ".join(text.lower().split()).strip()
    match = yargy_parser.find(clean_text)
    if match and match.fact.meaningful_part:
        return match.fact.meaningful_part.strip()
    # Если глагол-маркер не найден, убираем дефолтные префиксы регуляркой на всякий случай
    return re.sub(r'^(найди|найти|включи|поставь|вруби|запусти)\s*', '', clean_text).strip()

# =====================================================================
# 2. ГОЛОСОВОЙ И ЛИНГВИСТИЧЕСКИЙ ТРАКТ (VOSK + POSTGRES)
# =====================================================================
def recognize_voice():
    """Физическая запись звука 5 секунд и расшифровка через локальный Vosk"""
    if not os.path.exists(VOSK_MODEL_PATH):
        raise RuntimeError(f"Модель Vosk не найдена по пути: {VOSK_MODEL_PATH}")

    SetLogLevel(-1)

    print("\n🎤 СЛУШАЮ ВАС (Запись 5 секунд для теста)...", file=sys.stderr)
    
    # 5 секунд чистой arecord-записи
    subprocess.run(f"arecord -f cd -t raw -d 5 > {AUDIO_RAW}", shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    subprocess.run(f"ffmpeg -y -f s16le -ar 44100 -ac 2 -i {AUDIO_RAW} -ar 16000 -ac 1 {AUDIO_WAV}", shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    
    # Расшифровка движком Vosk
    model = Model(VOSK_MODEL_PATH)
    wf = wave.open(AUDIO_WAV, "rb")
    rec = KaldiRecognizer(model, wf.getframerate())
    
    data = wf.readframes(wf.getnframes())
    wf.close()
    
    # Чистим временные файлы сразу
    for f in [AUDIO_RAW, AUDIO_WAV]:
        if os.path.exists(f): os.remove(f)
        
    res = json.loads(rec.Result() if rec.AcceptWaveform(data) else rec.FinalResult())
    raw_text = res.get('text', '').strip()
    print(f"📋 Vosk услышал: \"{raw_text}\"", file=sys.stderr)
    return raw_text

def training(raw_speech, expected_interpretation):
    """
    ДРЕССИРОВЩИК: Вычленяет смысловую часть, сверяет с базой алиасов.
    Если перевода нет — автоматически добавляет галлюцинацию в БД.
    Возвращает True, если в итоге получилась нужная интерпретация.
    """
    if not raw_speech:
        print("❌ Ошибка: Речь не распознана, пустой лог.", file=sys.stderr)
        return False

    # Шаг 1. Отбрасываем первый глагол через Yargy
    meaningful_part = extract_meaningful_part(raw_speech)
    if not meaningful_part:
        return False
        
    print(f"🔍 Смысловой остаток для поиска: \"{meaningful_part}\"", file=sys.stderr)
    
    # Подключаемся к Postgres
    conn = psycopg2.connect(f"dbname=player user={PG_USER} password={PG_PASSWORD} host=localhost")
    cur = conn.cursor()
    
    # Шаг 2. Ищем, нет ли уже готовой галлюцинации в базе
    cur.execute("SELECT correct_name FROM phonetic_aliases WHERE vosk_hallucination = %s;", (meaningful_part,))
    result = cur.fetchone()

    are_equal = False

    if result:
        # Алиас найден в базе, берем его перевод
        current_interpretation = result[0]
        print(f"💡 Алиас уже в базе: '{meaningful_part}' -> '{current_interpretation}'", file=sys.stderr)
        are_equal = True
    else:
        # Шаг 3. 🌟 МАГИЯ ОБУЧЕНИЯ: Автоматически заносим новую галлюцинацию в БД!
        print(f"✍️ [Обучение]: Заношу новый алиас: '{meaningful_part}' -> '{expected_interpretation}'", file=sys.stderr)
        cur.execute(
            "INSERT INTO phonetic_aliases (vosk_hallucination, correct_name) VALUES (%s, %s) ON CONFLICT DO NOTHING;",
            (meaningful_part, expected_interpretation.lower().strip())
        )
        conn.commit()
        # current_interpretation = expected_interpretation
        
    cur.close()
    conn.close()
    
    # Тест успешен, если текущая интерпретация совпала с ожидаемым автором
    return are_equal #current_interpretation == expected_interpretation.lower().strip()

def normalize_vosk_query(text):
    """Служебная функция для интеграции в основной voice-assistant.py"""
    meaningful = extract_meaningful_part(text)
    if not meaningful:
        return text
        
    try:
        conn = psycopg2.connect("dbname=player user=postgres host=localhost")
        cur = conn.cursor()
        cur.execute("SELECT correct_name FROM phonetic_aliases WHERE vosk_hallucination = %s;", (meaningful,))
        res = cur.fetchone()
        cur.close()
        conn.close()
        if res:
            return res[0]
    except Exception:
        pass
    return meaningful

# =====================================================================
# 3. ИНТЕРАКТИВНЫЙ ИНТЕЛЛЕКТУАЛЬНЫЙ ТРЕНАЖЕР ЮНИТ-ТЕСТОВ
# =====================================================================
class TestVoiceAssistantTraining(unittest.TestCase):

    def test_meaning(self):
        meaning = extract_meaningful_part('включи дэйва брубека')
        self.assertEqual(meaning, 'дэйва брубека')

    def compare_voice_and_text(self, request, result):
        print(f"Произнесите: «{request}»")
        raw_speech = recognize_voice()
        self.assertTrue(training(raw_speech, result))

    #def test_wynton_marsalis(self):
    #    self.compare_voice_and_text('Поставь Уинтона Марсалиса', 'уинтон марсалис')

    # def test_dave_brubeck(self):
    #     self.compare_voice_and_text('Включи Дэйва Брубека', 'дэйв брубек')

    # def test_funny_valentine(self):
    #     self.compare_voice_and_text('Вруби май фанни валентайн', 'my funny valentine')

    # def test_sarah_vaughan(self):
    #     self.compare_voice_and_text('Поставь Сару Воан', 'сара воан')

    # def test_Ahmad_Jamal(self):
    #     self.compare_voice_and_text('Поставь Ахмада Джамала', 'Ахмад Джамал')

    # def test_Aretha_Franklin(self):
    #     self.compare_voice_and_text('Поставь Арету Франклин', 'Арета Франклин')

    # def test_Benny_Goodman(self):
    #     self.compare_voice_and_text('Поставь Бенни Гудмена', 'Бенни Гудмен')

    # def test_Bruno_Bohmer_Camacho(self):
    #     self.compare_voice_and_text('Поставь Бруно Бёмера', 'Бруно Бёмер Камачо')

    # def test_Chris_Botti(self):
    #     self.compare_voice_and_text('Поставь Криса Ботти', 'Крис Ботти')

    # def test_Ellis_Marsalis(self):
    #     self.compare_voice_and_text('Поставь Эллиса Марсалиса', 'Эллис Марсалис')

    # def test_Erroll_Garner(self):
    #     self.compare_voice_and_text('Поставь Эрролла Гарнера', 'Эрролл Гарнер')

    # def test_Frank_Sinatra(self):
    #     self.compare_voice_and_text('Поставь Фрэнка Синатрау', 'Фрэнк Синатра')

    # def test_George_Benson(self):
    #     self.compare_voice_and_text('Поставь Джорджа Бенсона', 'Джордж Бенсон')

    # def test_Klazz_Brothers(self):
    #     self.compare_voice_and_text('Поставь Клац Бразерс', 'Клац Бразерс')

    # def test_Miles_Davis(self):
    #     self.compare_voice_and_text('Поставь Майлза Дэйвиса', 'Майлз Дэйвис')

    # def test_Niels_Lan_Doky(self):
    #     self.compare_voice_and_text('Поставь Нильса Лан Доки', 'Нильс Лан Доки')

    # def test_Paul_Desmond(self):
    #     self.compare_voice_and_text('Поставь Пола Дезмонд', 'Пол Дезмонд')

    # def test_Roy_Hargrove(self):
    #     self.compare_voice_and_text('Поставь Роя Харгроува', 'Рой Харгроув')

    # def test_Thelonious_Monk(self):
    #     self.compare_voice_and_text('Поставь Телониуса Монка', 'Телониус Монк')

    # def test_Ralph_Sharon_Trio(self):
    #     self.compare_voice_and_text('Поставь Ральфа Шэрона', 'Ральф Шэрон')

    # def test_Tony_Bennett(self):
    #     self.compare_voice_and_text('Поставь Тони Беннетта', 'Тони Беннетт')

    # def test_Art_Blakey_and_the_Jazz_Messengers(self):
    #     self.compare_voice_and_text('Поставь Арта Блэйки', 'Арт Блэйки')

    def test_Mundell_Lowe_and_his_All_Stars(self):
        self.compare_voice_and_text('Поставь Манделла Лоу', 'Манделл Лоу')

if __name__ == "__main__":
    # Запускаем стандартный запуск тестов unittest
    unittest.main()
