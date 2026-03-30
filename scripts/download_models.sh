#!/bin/bash
# Download Piper TTS voice models
set -e

MODELS_DIR="$(dirname "$0")/../models"
mkdir -p "$MODELS_DIR"
cd "$MODELS_DIR"

BASE="https://huggingface.co/rhasspy/piper-voices/resolve/main"

download() {
    local path="$1"
    local name="$2"
    if [ -f "${name}.onnx" ]; then
        echo "  SKIP: ${name} (already exists)"
        return
    fi
    echo "  Downloading: ${name}..."
    curl -sL -o "${name}.onnx" "${BASE}/${path}.onnx?download=true"
    curl -sL -o "${name}.onnx.json" "${BASE}/${path}.onnx.json?download=true"
    local size=$(wc -c < "${name}.onnx" | tr -d ' ')
    if [ "$size" -lt 1000 ]; then
        echo "  WARNING: ${name} download failed (${size} bytes), removing"
        rm -f "${name}.onnx" "${name}.onnx.json"
    else
        echo "  OK: ${name} ($(du -h "${name}.onnx" | cut -f1))"
    fi
}

echo "=== Downloading Piper TTS voice models ==="
echo ""

download "tr/tr_TR/dfki/medium/tr_TR-dfki-medium" "tr_TR-dfki-medium"
download "en/en_US/amy/medium/en_US-amy-medium" "en_US-amy-medium"
download "de/de_DE/thorsten/medium/de_DE-thorsten-medium" "de_DE-thorsten-medium"
download "fr/fr_FR/siwis/medium/fr_FR-siwis-medium" "fr_FR-siwis-medium"
download "es/es_ES/sharvard/medium/es_ES-sharvard-medium" "es_ES-sharvard-medium"
download "it/it_IT/riccardo/x_low/it_IT-riccardo-x_low" "it_IT-riccardo-x_low"
download "zh/zh_CN/huayan/medium/zh_CN-huayan-medium" "zh_CN-huayan-medium"
download "ru/ru_RU/denis/medium/ru_RU-denis-medium" "ru_RU-denis-medium"
download "ar/ar_JO/kareem/medium/ar_JO-kareem-medium" "ar_JO-kareem-medium"
download "pt/pt_BR/faber/medium/pt_BR-faber-medium" "pt_BR-faber-medium"

echo ""
echo "=== Done! $(ls -1 *.onnx 2>/dev/null | wc -l | tr -d ' ') models downloaded ==="
