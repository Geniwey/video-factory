#!/bin/bash
set -euo pipefail

echo "══════════════════════════════════════"
echo "  RENDER FFMPEG — ESTILO HORMOZI"
echo "══════════════════════════════════════"

# ═══════════════════════════════════════
# VALIDACIÓN DE ARCHIVOS
# ═══════════════════════════════════════
ABORT=false
for file in audio.wav background.mp4 overlay.png subtitles.ass; do
  if [ ! -f "$file" ]; then
    echo "❌ FALTA: $file"
    ABORT=true
  elif [ ! -s "$file" ]; then
    echo "❌ VACÍO: $file"
    ABORT=true
  else
    echo "✅ $file ($(du -h "$file" | cut -f1))"
  fi
done

if [ "$ABORT" = true ]; then
  echo "❌ Faltan archivos críticos. Abortando render."
  exit 1
fi

# ═══════════════════════════════════════
# OBTENER DURACIÓN
# ═══════════════════════════════════════
if [ -f "/tmp/audio_duration.txt" ]; then
  DURATION=$(cat /tmp/audio_duration.txt)
else
  DURATION=$(ffprobe -v quiet \
    -show_entries format=duration \
    -of default=noprint_wrappers=1:nokey=1 \
    audio.wav)
fi

# Validar que DURATION es un número
if ! echo "$DURATION" | grep -qE '^[0-9]+\.?[0-9]*$'; then
  echo "❌ Duración inválida: '$DURATION'"
  exit 1
fi

echo "⏱  Duración: ${DURATION}s"

# ═══════════════════════════════════════
# PASADA 1: Composición visual
# (fondo + overlay + subtítulos)
# ═══════════════════════════════════════
echo ""
echo "── PASADA 1: Composición visual ──"

ffmpeg -y \
  -stream_loop -1 -i background.mp4 \
  -i overlay.png \
  -filter_complex "
    [0:v]
      scale=1080:1920:force_original_aspect_ratio=increase,
      crop=1080:1920,
      setsar=1,
      eq=brightness=-0.12:saturation=0.85
    [bg];
    [1:v]
      scale=1080:1920:force_original_aspect_ratio=increase,
      crop=1080:1920,
      format=rgba,
      colorchannelmixer=aa=0.18
    [ov];
    [bg][ov]overlay=0:0[merged];
    [merged]ass=subtitles.ass[final]
  " \
  -map "[final]" \
  -t "$DURATION" \
  -c:v libx264 \
  -preset medium \
  -crf 23 \
  -pix_fmt yuv420p \
  -an \
  temp_visual.mp4

# Verificar pasada 1
if [ ! -f "temp_visual.mp4" ] || [ "$(stat --printf='%s' temp_visual.mp4)" -lt 50000 ]; then
  echo "❌ Pasada 1 falló. Intentando render simplificado..."

  # Render de emergencia sin overlay ni subtítulos
  ffmpeg -y \
    -stream_loop -1 -i background.mp4 \
    -t "$DURATION" \
    -vf "scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,eq=brightness=-0.1" \
    -c:v libx264 -preset fast -crf 25 -pix_fmt yuv420p -an \
    temp_visual.mp4

  if [ ! -f "temp_visual.mp4" ]; then
    echo "❌ Render de emergencia también falló. Abortando."
    exit 1
  fi
  echo "⚠️  Render simplificado (sin overlay/subs)"
fi

echo "✅ Pasada 1 completada ($(du -h temp_visual.mp4 | cut -f1))"

# ═══════════════════════════════════════
# PASADA 2: Audio + Barra de progreso
# ═══════════════════════════════════════
echo ""
echo "── PASADA 2: Audio + Barra de progreso ──"

# Escapar la duración para el filtro drawbox
SAFE_DURATION=$(printf '%s' "$DURATION")

ffmpeg -y \
  -i temp_visual.mp4 \
  -i audio.wav \
  -filter_complex "
    [0:v]drawbox=
      x=0:
      y=0:
      w='min(iw,iw*t/${SAFE_DURATION})':
      h=8:
      color=0xFFD700@0.90:
      t=fill
    [final]
  " \
  -map "[final]" \
  -map 1:a \
  -c:v libx264 \
  -preset medium \
  -crf 23 \
  -pix_fmt yuv420p \
  -c:a aac \
  -b:a 192k \
  -ar 44100 \
  -movflags +faststart \
  -t "$DURATION" \
  output.mp4

# ═══════════════════════════════════════
# LIMPIEZA Y VALIDACIÓN
# ═══════════════════════════════════════
rm -f temp_visual.mp4

if [ ! -f "output.mp4" ]; then
  echo "❌ output.mp4 no se generó"
  exit 1
fi

OUTPUT_SIZE=$(stat --printf="%s" output.mp4)

if [ "$OUTPUT_SIZE" -lt 100000 ]; then
  echo "❌ output.mp4 demasiado pequeño (${OUTPUT_SIZE} bytes)"
  exit 1
fi

OUTPUT_MB=$(echo "scale=1; $OUTPUT_SIZE / 1048576" | bc)
OUTPUT_DUR=$(ffprobe -v quiet \
  -show_entries format=duration \
  -of default=noprint_wrappers=1:nokey=1 \
  output.mp4)

echo ""
echo "══════════════════════════════════════"
echo "  ✅ RENDER COMPLETADO"
echo "  📦 Tamaño:   ${OUTPUT_MB} MB"
echo "  ⏱  Duración: ${OUTPUT_DUR}s"
echo "══════════════════════════════════════"
