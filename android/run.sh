#!/data/data/com.termux/files/usr/bin/bash
# Jalankan Loka - AMAN dengan internet mati (airplane mode)
proot-distribution login loka-jail -- /bin/bash -c "
  cd /root/loka/app 2>/dev/null || cd /root/app
  export LOKA_HOME=/root/loka
  export LOKA_MODEL=/root/loka/models/model-q4.gguf
  python3 agent/core.py
"
