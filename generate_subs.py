#!/usr/bin/env python3
"""
Generador de subtítulos ASS estilo Alex Hormozi.
BLINDADO: Maneja todos los edge cases sin crashear.
"""

import json
import os
import sys

# ════════════════════════════════════════
# CONFIGURACIÓN
# ════════════════════════════════════════
WORDS_PER_GROUP = 3
FONT_SIZE = 82

# Detectar fuente disponible
FALLBACK_FONT_FILE = "/tmp/fallback_font.txt"
if os.path.exists(FALLBACK_FONT_FILE):
    with open(FALLBACK_FONT_FILE) as f:
        FONT_NAME = f.read().strip()
    print(f"Usando fuente fallback: {FONT_NAME}")
else:
    FONT_NAME = "Montserrat Black"
    print(f"Usando fuente: {FONT_NAME}")

# Colores ASS: formato &HAABBGGRR
COLOR_ACTIVE   = "&H0000D7FF"     # Amarillo dorado
COLOR_INACTIVE = "&H00FFFFFF"     # Blanco
COLOR_OUTLINE  = "&H00000000"     # Negro
COLOR_SHADOW   = "&HBB000000"     # Negro semitransparente
OUTLINE_SIZE   = 4
SHADOW_SIZE    = 2
MARGIN_BOTTOM  = 538


def format_time(seconds):
    """Convierte segundos a formato ASS: H:MM:SS.CC"""
    if seconds < 0:
        seconds = 0
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    cs = int(round((seconds % 1) * 100))
    if cs >= 100:
        cs = 99
    return f"{h}:{m:02d}:{s:02d}.{cs:02d}"


def clean_word(word):
    """Limpia una palabra para subtítulos."""
    word = word.strip()
    # Eliminar caracteres raros que rompen ASS
    word = word.replace("\\", "")
    word = word.replace("{", "")
    word = word.replace("}", "")
    word = word.replace("\n", " ")
    return word


def extract_words(data):
    """Extrae palabras con timestamps del JSON de Whisper."""
    all_words = []

    segments = data.get("segments", [])

    for segment in segments:
        words_in_segment = segment.get("words", [])

        if words_in_segment:
            # ── Caso ideal: Whisper devolvió word-level timestamps ──
            for w in words_in_segment:
                text = clean_word(w.get("word", ""))
                if not text:
                    continue

                start = w.get("start", 0)
                end   = w.get("end", start + 0.3)

                # Sanity checks
                if not isinstance(start, (int, float)):
                    start = 0
                if not isinstance(end, (int, float)):
                    end = start + 0.3
                if end <= start:
                    end = start + 0.3

                all_words.append({
                    "text": text,
                    "start": float(start),
                    "end": float(end)
                })
        else:
            # ── Fallback: dividir texto del segmento en palabras ──
            text = segment.get("text", "").strip()
            if not text:
                continue

            seg_start = float(segment.get("start", 0))
            seg_end   = float(segment.get("end", seg_start + 1))

            words_list = text.split()
            if not words_list:
                continue

            duration = seg_end - seg_start
            time_per_word = duration / len(words_list)

            for i, word in enumerate(words_list):
                word = clean_word(word)
                if not word:
                    continue
                all_words.append({
                    "text": word,
                    "start": seg_start + i * time_per_word,
                    "end":   seg_start + (i + 1) * time_per_word
                })

    return all_words


def generate_ass(all_words):
    """Genera el contenido del archivo ASS."""

    # ── Header ──
    ass = f"""[Script Info]
Title: Hormozi Style Subtitles
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920
WrapStyle: 0
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,{FONT_NAME},{FONT_SIZE},{COLOR_INACTIVE},{COLOR_ACTIVE},{COLOR_OUTLINE},{COLOR_SHADOW},-1,0,0,0,100,100,0,0,1,{OUTLINE_SIZE},{SHADOW_SIZE},2,60,60,{MARGIN_BOTTOM},1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""

    # ── Agrupar en chunks ──
    chunks = []
    for i in range(0, len(all_words), WORDS_PER_GROUP):
        chunk = all_words[i:i + WORDS_PER_GROUP]
        if chunk:
            chunks.append(chunk)

    if not chunks:
        print("⚠️  No hay palabras para generar subtítulos")
        return ass

    # ── Generar eventos ──
    for chunk in chunks:
        chunk_start = chunk[0]["start"]
        chunk_end   = chunk[-1]["end"]

        for active_idx in range(len(chunk)):
            word_start = chunk[active_idx]["start"]
            word_end   = chunk[active_idx]["end"]

            # Construir texto con highlight
            parts = []
            for j, word in enumerate(chunk):
                w_upper = word["text"].upper()
                if j == active_idx:
                    # Palabra activa: amarillo + más grande
                    parts.append(
                        f"{{\\c{COLOR_ACTIVE}\\fscx115\\fscy115}}"
                        f"{w_upper}"
                        f"{{\\c{COLOR_INACTIVE}\\fscx100\\fscy100}}"
                    )
                else:
                    parts.append(w_upper)

            line = " ".join(parts)

            # Escribir evento
            ass += (
                f"Dialogue: 0,"
                f"{format_time(word_start)},"
                f"{format_time(word_end)},"
                f"Default,,0,0,0,,"
                f"{line}\n"
            )

    return ass


# ════════════════════════════════════════
# MAIN
# ════════════════════════════════════════
def main():
    # ── Leer JSON ──
    json_file = "audio.json"

    if not os.path.exists(json_file):
        print(f"❌ {json_file} no encontrado")
        sys.exit(1)

    try:
        with open(json_file, "r", encoding="utf-8") as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        print(f"❌ JSON inválido en {json_file}: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Error leyendo {json_file}: {e}")
        sys.exit(1)

    # ── Extraer palabras ──
    all_words = extract_words(data)
    print(f"Palabras extraídas: {len(all_words)}")

    if not all_words:
        print("⚠️  No se encontraron palabras en la transcripción")
        sys.exit(1)

    # ── Generar ASS ──
    ass_content = generate_ass(all_words)

    # ── Guardar ──
    with open("subtitles.ass", "w", encoding="utf-8") as f:
        f.write(ass_content)

    dialogue_count = ass_content.count("Dialogue:")
    print(f"✅ subtitles.ass generado: {dialogue_count} líneas de diálogo")
    print(f"   Duración: {format_time(all_words[0]['start'])} → {format_time(all_words[-1]['end'])}")


if __name__ == "__main__":
    main()
