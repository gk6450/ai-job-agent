"""Configuration for the web backend."""

from pathlib import Path
import os

PROJECT_ROOT = Path(__file__).parent.parent.parent
DATA_DIR = PROJECT_ROOT / "data"
GENERATED_DIR = PROJECT_ROOT / "generated"
MCP_SERVERS_DIR = PROJECT_ROOT / "mcp-servers"

OPENCLAW_GATEWAY_URL = os.environ.get("OPENCLAW_GATEWAY_URL", "http://localhost:18789")
WEB_AUTH_TOKEN = os.environ.get("JOBPILOT_WEB_TOKEN", "jobpilot-local-dev")
CORS_ORIGINS = os.environ.get("CORS_ORIGINS", "http://localhost:5173,http://localhost:3000").split(",")
