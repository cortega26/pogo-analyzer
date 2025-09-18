from __future__ import annotations

import os
import sys


def main() -> None:  # pragma: no cover - thin launcher
    try:
        from streamlit.web import cli as stcli  # type: ignore
    except Exception:  # noqa: BLE001
        sys.stderr.write(
            "Streamlit is required. Install with `pip install pogo-analyzer[gui]`\n"
        )
        raise SystemExit(1)

    script_path = os.path.join(os.path.dirname(__file__), "gui_app.py")
    sys.argv = ["streamlit", "run", script_path]
    sys.exit(stcli.main())


if __name__ == "__main__":
    main()

