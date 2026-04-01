"""Write FastAPI OpenAPI schema to openapi.json (run from repo root with env configured)."""

from __future__ import annotations

import json
import sys
from pathlib import Path


def main() -> None:
    backend_root = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(backend_root))
    from app.main import app

    out = backend_root / "openapi.json"
    out.write_text(json.dumps(app.openapi(), indent=2), encoding="utf-8")
    print(f"Wrote {out}")


if __name__ == "__main__":
    main()
