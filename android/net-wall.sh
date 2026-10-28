#!/data/data/com.termux/files/usr/bin/bash
# Lapisan ke-2: blokir network di level proot (selain python tetap tak bisa keluar folder)
# Catatan: proot tidak punya netns; lapisan utama = sandbox.py. Skrip ini hanya belt-and-suspenders:
# men-disable DNS resolver di dalam jail.
JAIL=loka-jail
proot-distribution login $JAIL -- /bin/bash -c "
  echo 'nameserver 127.0.0.1' > /etc/resolv.conf
  echo '# loka: DNS diblokir oleh net-wall' >> /etc/resolv.conf
  echo '[net-wall] resolver dimatikan di dalam container.'
"
