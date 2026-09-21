from __future__ import annotations

import sys
from http.client import HTTPConnection


def main() -> int:
    connection = HTTPConnection("127.0.0.1", 8000, timeout=2)
    try:
        connection.request("GET", "/health/live")
        return 0 if connection.getresponse().status == 200 else 1
    finally:
        connection.close()


if __name__ == "__main__":
    sys.exit(main())
