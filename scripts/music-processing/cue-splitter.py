#!/usr/bin/env python3
import subprocess
import re
import os
import sys

def parse_cue(cue_file):
    """Парсит CUE-файл"""
    # Пробуем разные кодировки
    for encoding in ['utf-8', 'cp1251', 'cp1252', 'latin-1']:
        try:
            with open(cue_file, 'r', encoding=encoding) as f:
                content = f.read()
            break
        except UnicodeDecodeError:
            continue
    else:
        raise ValueError("Не удалось определить кодировку CUE-файла")
    
    # Ищем аудиофайл
    audio_match = re.search(r'FILE\s+"([^"]+)"', content)
    if not audio_match:
        raise ValueError("Не найден аудиофайл в CUE")
    audio_file = audio_match.group(1)
    
    # Ищем треки
    tracks = []
    track_pattern = re.compile(
        r'TRACK\s+(\d+)\s+AUDIO.*?TITLE\s+"([^"]+)".*?INDEX\s+01\s+(\d+):(\d+):(\d+)',
        re.DOTALL
    )
    
    for match in track_pattern.finditer(content):
        track_num = int(match.group(1))
        title = match.group(2)
        minutes = int(match.group(3))
        seconds = int(match.group(4))
        frames = int(match.group(5))
        
        start_time = minutes * 60 + seconds + frames / 75.0
        tracks.append({
            'number': track_num,
            'title': title,
            'start': start_time
        })
    
    return audio_file, tracks

def split_album(cue_file):
    """Разбивает альбом на треки"""
    cue_dir = os.path.dirname(os.path.abspath(cue_file))
    os.chdir(cue_dir)
    
    audio_file, tracks = parse_cue(cue_file)
    
    if not tracks:
        print("Не найдены треки в CUE-файле")
        return
    
    if not os.path.exists(audio_file):
        print(f"Ошибка: аудиофайл '{audio_file}' не найден")
        return
    
    # Получаем информацию об аудиофайле
    probe_cmd = [
        'ffprobe', '-v', 'error',
        '-show_entries', 'stream=sample_rate,channels,duration',
        '-of', 'default=noprint_wrappers=1',
        audio_file
    ]
    probe_output = subprocess.check_output(probe_cmd, text=True)
    
    sample_rate = int(re.search(r'sample_rate=(\d+)', probe_output).group(1))
    channels = int(re.search(r'channels=(\d+)', probe_output).group(1))
    duration = float(re.search(r'duration=([\d.]+)', probe_output).group(1))
    
    print(f"Аудиофайл: {audio_file}")
    print(f"Sample rate: {sample_rate} Hz, Channels: {channels}, Duration: {duration:.1f}s")
    print(f"Найдено треков: {len(tracks)}\n")
    
    # Разбиваем на треки
    for i, track in enumerate(tracks):
        start_time = track['start']
        
        if i + 1 < len(tracks):
            track_duration = tracks[i + 1]['start'] - start_time
        else:
            track_duration = None
        
        # Очищаем название от недопустимых символов
        title = re.sub(r'[<>:"/\\|?*]', '_', track['title'])
        output_file = f"{track['number']:02d} - {title}.flac"
        
        # Формируем команду правильно
        cmd = ['ffmpeg', '-y']
        
        # Указываем начало и длительность ПЕРЕД входным файлом
        cmd.extend(['-ss', str(start_time)])
        if track_duration:
            cmd.extend(['-t', str(track_duration)])
        
        cmd.extend([
            '-i', audio_file,
            '-c:a', 'flac',
            '-sample_fmt', 's32',
            '-ar', str(sample_rate),
            '-ac', str(channels),
            '-metadata', f'TRACKNUMBER={track["number"]}',
            '-metadata', f'TITLE={track["title"]}',
            output_file
        ])
        
        print(f"[{i+1}/{len(tracks)}] Создаю: {output_file}")
        result = subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True)
        
        if result.returncode != 0:
            print(f"  Ошибка: {result.stderr}")
    
    print("\nГотово!")

if __name__ == '__main__':
    if len(sys.argv) != 2:
        print("Использование: python3 split_cue.py <файл.cue>")
        sys.exit(1)
    
    split_album(sys.argv[1])

