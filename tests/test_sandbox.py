"""Self-test sandbox: semua akses network HARUS gagal (diblokir)."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import agent.sandbox

fails = []
def expect_block(desc, fn):
    try:
        fn()
        fails.append(f"TIDAK terblokir: {desc}")
    except OSError:
        print(f"  ok diblokir: {desc}")
    except ImportError:
        print(f"  ok diblokir (module off): {desc}")
    except Exception as e:
        fails.append(f"error lain {desc}: {e}")

expect_block("socket.socket", lambda: __import__("socket").socket())
expect_block("getaddrinfo", lambda: __import__("socket").getaddrinfo("example.com", 443))
expect_block("os.popen curl", lambda: os.popen("curl https://example.com"))
expect_block("subprocess wget", lambda: __import__("subprocess").run(["wget","http://x"]))
expect_block("import requests", lambda: __import__("requests"))

if fails:
    print("GAGAL:", fails); sys.exit(1)
print("SANDBOX LOLOS SEMUA TES - agent benar-benar offline.")
