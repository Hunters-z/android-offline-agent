#!/data/data/com.termux/files/usr/bin/bash
# Setup SEKALI (butuh internet): Termux + proot sandbox + model lokal
set -e
echo "=== 1. Paket dasar ==="
pkg update -y && pkg install -y python proot-distribution wget
pip install llama-cpp-python --extra-index-url https://abetlen.github.io/llama-cpp-python/whl/cpu || pip install llama-cpp-python

echo "=== 2. Container proot (filesystem terisolasi) ==="
proot-distribution install ubuntu -d loka-jail

echo "=== 3. Unduh model GGUF kecil (±500 MB, sekali saja) ==="
mkdir -p ~/loka/models
# Qwen2.5-1.5B-Instruct Q4_K_M — muat di HP 4 GB RAM
URL="https://huggingface.co/Qwen/Qwen2.5-1.5B-Instruct-GGUF/resolve/main/qwen2.5-1.5b-instruct-q4_k_m.gguf"
wget -O ~/loka/models/model-q4.gguf "$URL"

echo "=== 4. Salin agent ke dalam container ==="
proot-distribution login loka-jail -- mkdir -p /root/loka
proot-distribution login loka-jail -- bind -r $(pwd) /root/app 2>/dev/null || cp -r . /root/loka/app

echo "=== 5. Verifikasi sandbox ==="
proot-distribution login loka-jail -- /bin/bash -c "python3 -c \"import sys; sys.path.insert(0,'/root/loka/app'); import agent.sandbox as s; print('SANDBOX:', s.SANDBOX_ACTIVE)\""

echo "SELESAI — dari sini HP bisa airplane-mode penuh."
echo "Jalankan agent: bash android/run.sh"
