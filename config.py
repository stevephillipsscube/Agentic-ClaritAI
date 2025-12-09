# config.py
import os, json
from typing import Any, Dict
try:
    import yaml  # pip install pyyaml
except Exception:
    yaml = None

def load_agent_config(path: str = "config/agent.yml") -> Dict[str, Any]:
    if yaml and os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f) or {}
    # fallback default
    return {
        "defaults": {
            "org_alias_env": "SF_ORG",
            "emit_decision_router": False,
            "add_canvas_coordinates": True,
        },
        "intents": [],
    }
