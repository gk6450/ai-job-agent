"""Generate ~/.openclaw/openclaw.json from a template + .env on this machine.

Run once after cloning the repo (and after creating the .venv) to produce a
fully resolved OpenClaw gateway config with absolute paths and your secrets.

Usage:
    python tools/setup_openclaw_config.py
    python tools/setup_openclaw_config.py --dry-run        # print, don't write
    python tools/setup_openclaw_config.py --output PATH    # custom output path
    python tools/setup_openclaw_config.py --env-file PATH  # custom .env path

The script:
  1. Reads `config/openclaw.template.json`
  2. Reads `.env` from the repo root (falls back to existing OS env vars)
  3. Detects the venv Python interpreter for the current OS
  4. Substitutes {{PLACEHOLDERS}} with concrete values
  5. Backs up any existing openclaw.json -> openclaw.json.bak
  6. Writes the result to ~/.openclaw/openclaw.json
"""

from __future__ import annotations

import argparse
import json
import os
import platform
import secrets
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
TEMPLATE_PATH = REPO_ROOT / "config" / "openclaw.template.json"
DEFAULT_ENV_FILE = REPO_ROOT / ".env"
DEFAULT_OUTPUT = Path.home() / ".openclaw" / "openclaw.json"


def parse_env_file(path: Path) -> dict[str, str]:
    """Minimal .env parser (no python-dotenv dependency)."""
    if not path.exists():
        return {}
    env: dict[str, str] = {}
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key:
            env[key] = value
    return env


def detect_venv_python() -> Path:
    """Locate the project's virtual environment Python interpreter."""
    venv = REPO_ROOT / ".venv"
    candidate = (
        venv / "Scripts" / "python.exe"
        if platform.system() == "Windows"
        else venv / "bin" / "python"
    )
    if not candidate.exists():
        raise FileNotFoundError(
            f"Virtual environment Python not found at {candidate}. "
            "Create the venv first:  python -m venv .venv  &&  "
            "(.venv/Scripts/activate or source .venv/bin/activate)  &&  "
            "pip install -r requirements.txt"
        )
    return candidate


def get(env: dict[str, str], key: str, default: str = "", required: bool = False) -> str:
    """Look up a value in the .env dict, then OS env, with an optional default."""
    value = env.get(key) or os.environ.get(key) or default
    if required and not value:
        raise ValueError(
            f"Required value '{key}' is missing. Set it in .env or as an environment variable."
        )
    return value


def to_posix(p: Path) -> str:
    """Forward-slash absolute path; OpenClaw + Node handle this on every OS."""
    return p.resolve().as_posix()


def build_substitutions(env: dict[str, str]) -> dict[str, str]:
    venv_python = detect_venv_python()
    service_account = get(env, "GOOGLE_SERVICE_ACCOUNT_FILE", "data/service-account.json")
    if service_account and not Path(service_account).is_absolute():
        service_account = to_posix(REPO_ROOT / service_account)

    return {
        "{{REPO_ROOT}}": to_posix(REPO_ROOT),
        "{{VENV_PYTHON}}": to_posix(venv_python),
        "{{GATEWAY_TOKEN}}": get(env, "OPENCLAW_GATEWAY_TOKEN", secrets.token_hex(24)),
        "{{GOOGLE_API_KEY}}": get(env, "GOOGLE_API_KEY", required=True),
        "{{GROQ_API_KEY}}": get(env, "GROQ_API_KEY", ""),
        "{{TELEGRAM_BOT_TOKEN}}": get(env, "TELEGRAM_BOT_TOKEN", ""),
        "{{GOOGLE_SERVICE_ACCOUNT_FILE}}": service_account,
        "{{ALLOWED_TELEGRAM_ID}}": get(env, "ALLOWED_TELEGRAM_ID", ""),
        "{{ALLOWED_WHATSAPP_NUMBER}}": get(env, "ALLOWED_WHATSAPP_NUMBER", ""),
    }


def render(template: str, subs: dict[str, str]) -> str:
    out = template
    for placeholder, value in subs.items():
        out = out.replace(placeholder, value)
    return out


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--dry-run", action="store_true", help="Print the rendered config and exit")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT, help=f"Output path (default: {DEFAULT_OUTPUT})")
    parser.add_argument("--env-file", type=Path, default=DEFAULT_ENV_FILE, help=f"Path to .env (default: {DEFAULT_ENV_FILE})")
    args = parser.parse_args()

    if not TEMPLATE_PATH.exists():
        print(f"ERROR: template not found at {TEMPLATE_PATH}", file=sys.stderr)
        return 1

    env = parse_env_file(args.env_file)
    if env:
        print(f"Loaded {len(env)} value(s) from {args.env_file}")
    else:
        print(f"No .env file at {args.env_file} (falling back to OS environment)")

    try:
        subs = build_substitutions(env)
    except (FileNotFoundError, ValueError) as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 1

    rendered = render(TEMPLATE_PATH.read_text(encoding="utf-8"), subs)

    try:
        parsed = json.loads(rendered)
    except json.JSONDecodeError as e:
        print(f"ERROR: rendered config is invalid JSON: {e}", file=sys.stderr)
        print(rendered, file=sys.stderr)
        return 1

    parsed["meta"] = {"lastTouchedAt": datetime.now(timezone.utc).isoformat()}
    pretty = json.dumps(parsed, indent=2)

    if args.dry_run:
        print("\n--- Rendered openclaw.json (dry run) ---\n")
        print(pretty)
        return 0

    args.output.parent.mkdir(parents=True, exist_ok=True)
    if args.output.exists():
        backup = args.output.with_suffix(args.output.suffix + ".bak")
        shutil.copy2(args.output, backup)
        print(f"Backed up existing config -> {backup}")

    args.output.write_text(pretty, encoding="utf-8")
    print(f"Wrote {args.output}")
    print(f"  Repo root:    {subs['{{REPO_ROOT}}']}")
    print(f"  Venv Python:  {subs['{{VENV_PYTHON}}']}")
    print("Next: openclaw gateway start")
    return 0


if __name__ == "__main__":
    sys.exit(main())
