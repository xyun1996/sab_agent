import sys


def pytest_sessionstart(session):
    # Windows 控制台默认 GBK，打印 emoji/特殊字符会 UnicodeEncodeError
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
