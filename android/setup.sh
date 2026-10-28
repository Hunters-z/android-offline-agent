#!/data/data/com.termux/files/usr/bin/bash
# Setup SEKALI (butuh internet). Model: Qwen2.5-0.5B-Instruct Q4_K_M (491 MB)
set -e
pkg update -y && pkg install -y python proot-distribution wget curl
pip install llama-cpp-python huggingface_hub || pip install --break-system-packages llama-cpp-python huggingface_hub
proot-distribution install ubuntu -d loka-jail
mkdir -p ~/loka/models
# Sumber utama ModelScope (stabil), cadangan HuggingFace
curl -L -H 'User-Agent: Mozilla/5.0' -C - -o ~/loka/models/model-q4.gguf \
  'https://modelscope.cn/models/Qwen/Qwen2.5-0.5B-Instruct-GGUF/resolve/master/qwen2.5-0.5b-instruct-q4_k_m.gguf' \
  || wget -O ~/loka/models/model-q4.gguf \
  'https://huggingface.co/Qwen/Qwen2.5-0.5B-Instruct-GGUF/resolve/main/qwen2.5-0.5b-instruct-q4_k_m.gguf'
cp -r . /root/loka-app 2>/dev/null || true
proot-distribution login loka-jail -- mkdir -p /root/loka/app
cp -r agent tools tests /root/loka/app/ 2>/dev/null || proot-distribution login loka-jail -- bind -r $(pwd) /root/loka/app
echo "SELESAI - mulai sekarang HP bisa airplane mode. Jalankan: bash android/run.sh"
