"""PC pe test. python local_test.py"""
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent
os.chdir(ROOT)

n = input("kitne views? (Enter = 20): ").strip() or "20"
os.environ["VIEWS"] = n
os.environ["SHARD"] = "0"
os.environ["USE_PROXIES"] = "0"

print("chalu: %s views, proxies off\n" % n)
exec(compile((ROOT / "bot.py").read_text(encoding="utf-8"), "bot.py", "exec"))
