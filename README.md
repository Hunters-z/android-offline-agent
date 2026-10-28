# Loka — Agent AI Offline untuk Android

Agent AI seperti Hermes/Muse/OpenClaw, tapi **100% offline** dan **terkunci dalam container** — tidak bisa mengakses internet sama sekali, bahkan jika diminta (prompt injection pun gagal).

## Prinsip keamanan (3 lapis)
1. **Sandbox Python** (`agent/sandbox.py`) — socket diblokir di level interpreter sebelum kode lain jalan; requests/httpx/net-tools dinetralkan
2. **Container proot** — filesystem terisolasi; agent hanya boleh baca/tulis di `~/loka`
3. **Whitelist tool** — LLM hanya bisa memanggil 9 tool lokal (calc, notes, file, waktu, baterai)

## Install (Sekali — butuh internet)
```bash
pkg install -y git && git clone <repo> && cd android-offline-agent
bash android/setup.sh
```
Unduh model Qwen2.5-1.5B GGUF (±1 GB) — sesudah ini HP bisa airplane mode.

## Jalankan (tanpa internet)
```bash
bash android/net-wall.sh   # opsional: matikan DNS dalam jail
bash android/run.sh
```

## Contoh pemakaian
```
Kamu ▸ hitung 25% dari 1.800.000
Loka ▸ Hasilnya 450.000

Kamu ▸ simpan catatan: survey lokasi B besok pagi
Loka ▸ Tersimpan ✓ (notes/…survey_lokasi_B_besok_pagi.md)

Kamu ▸ buka google.com        → ditolak sandbox ✓
```

## Model
Default: Qwen2.5-1.5B-Instruct (Q4_K_M, ±1 GB) — jalan di HP 4 GB RAM.
Ganti: `LOKA_MODEL=~/loka/models/model lain.gguf bash android/run.sh`
Model lebih kecil (0.5B) untuk HP kentang; model 3B untuk HP 8 GB+.

MIT


## Pilihan Model
Katalog 4 model Qwen2.5 (GGUF Q4_K_M). Di dalam Loka:
- `/model` - daftar model (tiny 0.5B/491MB, small 1.5B/986MB, medium 3B/2GB, smart 7B/4.7GB)
- `/model small` - ganti model aktif (unduh dulu via perintah yang dicetak setup)

## Sistem Skill
Skill = file Markdown di `~/loka/skills/`. Agent memuat otomatis skill yang relevan (berdasar kata kunci) ke konteks - semuanya offline.
- `/skills` - daftar skill terpasang
- `/skill <nama>` - baca isi skill
- Tambah skill sendiri: buat file `.md` dengan baris `Keywords: kata, kunci, ...`
- Bawaan: catatan-cerdas, hitung-laporan
