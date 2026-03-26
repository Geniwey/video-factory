#!/usr/bin/env python3
"""
Generador de subtítulos ASS estilo Alex Hormozi.
- Montserrat Black 900
- Palabra activa: AMARILLO (#FFD700)
- Resto de palabras: BLANCO (#FFFFFF)
- 3 palabras por grupo máximo
- Posición: 72% desde arriba (zona inferior)
"""

import json

# ════════════════════════════════════════
# CONFIGURACIÓN DE ESTILO
# ════════════════════════════════════════
WORDS_PER_GROUP = 3
FONT_NAME = "Montserrat Black"
FONT_SIZE = 85
# Colores en formato ASS: &HAABBGGRR
COLOR_ACTIVE = "&H0000D7FF"    # Amarillo (#FFD700)
COLOR_INACTIVE = "&H00FFFFFF"  # Blanco
COLOR_OUTLINE = "&H00000000"   # Negro
COLOR_SHADOW = "&HBB000000"    # Negro semitransparente
OUTLINE_SIZE = 4
SHADOW_SIZE = 2
# MarginV desde abajo: 1920 * 0.28 ≈ 538px
MARGIN_BOTTOM = 538

# ════════════════════════════════════════
# LEER TRANSCRIPCIÓN DE WHISPER
# ════════════════════════════════════════
with open("audio.json", "r", encoding="utf-8") as f:
    data = json.load(f)

all_words = []
for segment in data.get("segments", []):
    for word_data in segment.get("words", []):
        word = word_data.get("word", "").strip()
        if not word:
            continue
        all_words.append({
            "text": word,
            "start": word_data["start"],
            "end": word_data["end"]
        })

if not all_words:
    print("⚠️ No se encontraron palabras. Generando subtítulo estático.")
    for segment in data.get("segments", []):
        text = segment.get("text", "").strip()
        if text:
            words_in_seg = text.split()
            duration = segment["end"] - segment["start"]
            time_per_word = duration / max(len(words_in_seg), 1)
            for i, w in enumerate(words_in_seg):
                all_words.append({
                    "text": w,
                    "start": segment["start"] + i * time_per_word,
                    "end": segment["start"] + (i + 1) * time_per_word
                })

# ════════════════════════════════════════
# AGRUPAR EN CHUNKS DE 3 PALABRAS
# ════════════════════════════════════════
chunks = []
for i in range(0, len(all_words), WORDS_PER_GROUP):
    chunk = all_words[i:i + WORDS_PER_GROUP]
    chunks.append(chunk)

# ════════════════════════════════════════
# GENERAR ARCHIVO ASS
# ════════════════════════════════════════
def format_time(seconds):
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    cs = int(round((seconds % 1) * 100))
    if cs >= 100: cs = 99
    return f"{h}:{m:02d}:{s:02d}.{cs:02d}"

ass_content = f"""[Script Info]
Title: Hormozi Style Subtitles
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920
WrapStyle: 0

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,{FONT_NAME},{FONT_SIZE},{COLOR_INACTIVE},{COLOR_ACTIVE},{COLOR_OUTLINE},{COLOR_SHADOW},-1,0,0,0,100,100,0,0,1,{OUTLINE_SIZE},{SHADOW_SIZE},2,60,60,{MARGIN_BOTTOM},1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n"""

for chunk in chunks:
    for active_idx, active_word in enumerate(chunk):
        word_start = active_word["start"]
        word_end = active_word["end"]
        
        text_parts = []
        for j, word in enumerate(chunk):
            if j == active_idx:
                text_parts.append(
                    f"{{\\c{COLOR_ACTIVE}\\fscx110\\fscy110}}"
                    f"{word['text'].upper()}"
                    f"{{\\c{COLOR_INACTIVE}\\fscx100\\fscy100}}"
                )
            else:
                text_parts.append(word["text"].upper())

        line = " ".join(text_parts)
        event = f"Dialogue: 0,{format_time(word_start)},{format_time(word_end)},Default,,0,0,0,,{line}\n"
        ass_content += event

# ════════════════════════════════════════
# GUARDAR
# ════════════════════════════════════════
with open("subtitles.ass", "w", encoding="utf-8") as f:
    f.write(ass_content)

print(f"✅ Archivo subtitles.ass generado")
