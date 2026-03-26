#!/usr/bin/env python3
"""
Generador de subtítulos de EMERGENCIA.
Se usa cuando generate_subs.py falla.
Genera subtítulos simples por segmento (sin word-level highlight).
"""

import json
import os

FONT_NAME = "Montserrat Black"
if os.path.exists("/tmp/fallback_font.txt"):
    with open("/tmp/fallback_font.txt") as f:
        FONT_NAME = f.read().strip()


def format_time(seconds):
    seconds = max(0, float(seconds))
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    cs = min(99, int(round((seconds % 1) * 100)))
    return f"{h}:{m:02d}:{s:02d}.{cs:02d}"


# Leer lo que haya disponible
data = {"segments": []}

if os.path.exists("audio.json"):
    try:
        with open("audio.json") as f:
            data = json.load(f)
    except:
        pass

segments = data.get("segments", [])

# Si no hay segmentos, crear uno desde el texto del guion
if not segments:
    duration = 50.0
    if os.path.exists("/tmp/audio_duration.txt"):
        try:
            duration = float(open("/tmp/audio_duration.txt").read().strip())
        except:
            pass

    script = os.environ.get("SCRIPT_TEXT", "")
    if script:
        words = script.split()
        chunk_size = 5
        dt = duration / max(len(words) / chunk_size, 1)
        for i in range(0, len(words), chunk_size):
            chunk = words[i:i + chunk_size]
            segments.append({
                "start": (i / chunk_size) * dt,
                "end": ((i / chunk_size) + 1) * dt,
                "text": " ".join(chunk)
            })

ass = f"""[Script Info]
Title: Fallback Subtitles
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,{FONT_NAME},78,&H00FFFFFF,&H0000D7FF,&H00000000,&HBB000000,-1,0,0,0,100,100,0,0,1,4,2,2,60,60,538,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""

for seg in segments:
    text = seg.get("text", "").strip().upper()
    if not text:
        continue

    # Limpiar caracteres problemáticos
    text = text.replace("\\", "").replace("{", "").replace("}", "")

    start = format_time(seg.get("start", 0))
    end = format_time(seg.get("end", 0))
    ass += f"Dialogue: 0,{start},{end},Default,,0,0,0,,{text}\n"

with open("subtitles.ass", "w", encoding="utf-8") as f:
    f.write(ass)

count = ass.count("Dialogue:")
print(f"✅ Subtítulos de emergencia generados: {count} líneas")
