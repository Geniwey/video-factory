#!/bin/bash
set -euo pipefail

echo "═══════════════════════════════════════"
echo "  RENDER ESTILO HORMOZI — FFmpeg"
echo "═══════════════════════════════════════"

# ── Obtener duración del audio ──
DURATION=$(ffprobe -v quiet -show_entries format=duration \
  -of default=noprint_wrappers=1:nokey=1 audio.wav)

echo "⏱  Duración audio: ${DURATION}s"

# ── Verificar que todos los assets existen y son válidos ──
for file in audio.wav background.mp4 overlay.png subtitles.ass; do
  if [ ! -f "$file" ] || [ ! -s "$file" ]; then
    echo "❌ Archivo faltante o vacío: $file"
    exit 1
  fi
  echo "✅ $file ($(du -h "$file" | cut -f1))"
done

# ══════════════════════════════════════════════════
# RENDER EN 2 PASADAS (más estable en GitHub Actions)
# Pasada 1: Combinar fondo + overlay + subtítulos
# Pasada 2: Añadir audio + barra de progreso
# ══════════════════════════════════════════════════

echo ""
echo "── PASADA 1: Composición visual ──"

ffmpeg -y \
  -stream_loop -1 -i background.mp4 \
  -i overlay.png \
  -filter_complex "
    [0:v]
      scale=1080:1920:
        force_original_aspect_ratio=increase,
      crop=1080:1920,
      setsar=1,
      eq=brightness=-0.12:saturation=0.85
    [bg];

    [1:v]
      scale=1080:1920:
        force_original_aspect_ratio=increase,
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

echo "✅ Pasada 1 completada ($(du -h temp_visual.mp4 | cut -f1))"

echo ""
echo "── PASADA 2: Audio + Barra de progreso ──"

ffmpeg -y \
  -i temp_visual.mp4 \
  -i audio.wav \
  -filter_complex "
    [0:v]drawbox=
      x=0:
      y=0:
      w='min(iw\,iw*t/${DURATION})':
      h=8:
      color=0xFFD700@0.9:
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

# ── Limpieza ──
rm -f temp_visual.mp4

# ── Verificar resultado ──
OUTPUT_SIZE=$(stat --printf="%s" output.mp4 2>/dev/null || stat -f%z output.mp4)
OUTPUT_MB=$(echo "scale=1; $OUTPUT_SIZE / 1048576" | bc)
OUTPUT_DUR=$(ffprobe -v quiet -show_entries format=duration \
  -of default=noprint_wrappers=1:nokey=1 output.mp4)

echo ""
echo "═══════════════════════════════════════"
echo "  ✅ RENDER COMPLETADO"
echo "  📦 Tamaño: ${OUTPUT_MB} MB"
echo "  ⏱  Duración: ${OUTPUT_DUR}s"
echo "═══════════════════════════════════════"

# ── Validación final ──
if [ "$OUTPUT_SIZE" -lt 500000 ]; then
  echo "❌ El archivo es sospechosamente pequeño (<500KB). Posible error."
  exit 1
fi
