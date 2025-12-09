# agent.py
import os, sys, json, platform
from pathlib import Path
from dotenv import load_dotenv, find_dotenv
from simple_salesforce import Salesforce
from graph import build_graph
from tools.sf_cli import ensure_sf_cli, deploy_source_dir, query_flow_activation
from config import load_agent_config

# env boot
DOTENV_PATH = find_dotenv(usecwd=True)
if not load_dotenv(DOTENV_PATH, override=True):
    print("⚠️  .env not found (using OS env only)", file=sys.stderr)

print("[BOOT] Python:", sys.executable)
print("[BOOT] Platform:", platform.platform())
print("[BOOT] SF_ORG:", os.getenv("SF_ORG", ""))
print("[BOOT] LLM endpoint:", os.getenv("OLLAMA_URL", ""))
print("[BOOT] LLM model:", os.getenv("LLM_MODEL", ""))

try:
    sf = Salesforce(
        username=os.getenv("SF_USERNAME"),
        password=os.getenv("SF_PASSWORD"),
        security_token=os.getenv("SF_SECURITY_TOKEN"),
        domain=os.getenv("SF_DOMAIN", "test"),
    )
    print("[BOOT] simple_salesforce session established")
except Exception as e:
    print(f"[BOOT] simple_salesforce not initialized: {e}")

if len(sys.argv) < 2:
    print('Usage: python agent.py "<natural language flow spec>"')
    sys.exit(1)

CFG = load_agent_config()

nl_spec = sys.argv[1]
print("\n[RUN] Spec:", nl_spec)

OUT = Path("out_flows")
OUT.mkdir(parents=True, exist_ok=True)

# build ONCE
graph = build_graph(workdir=str(OUT), config=CFG)
state = {"spec_text": nl_spec, "config": CFG}

print("[RUN] Invoking graph...")
result = graph.invoke(state)
print("[RUN] Graph returned keys:", list(result.keys()))

print("\n=== PLAN ===")
print(json.dumps(result.get("plan", {}), indent=2))

if "flow_dir" in result:
    print(f"\n[RESULT] Generated flow at: {result['flow_dir']}")
else:
    print("\n[RESULT] No flow_dir produced — check PLAN and earlier logs.")
    sys.exit(2)

org_alias = os.getenv("SF_ORG", "")
if os.getenv("SKIP_DEPLOY") == "1":
    print("\n(SKIP_DEPLOY=1) Not deploying.")
    print(f"  cd {result['flow_dir']}")
    print(f"  sf project deploy start --source-dir . --target-org {org_alias or '<yourAlias>'}")
else:
    ensure_sf_cli()
    print("\n[DEPLOY] Starting deploy...")
    deploy_source_dir(result["flow_dir"], org_alias)
    print("[DEPLOY] Done.")

    flow_label = result.get("flow_label")
    if flow_label:
        print("\n[VERIFY] Querying FlowDefinition/ActiveVersion ...")
        active = query_flow_activation(flow_label, org_alias)
        print(json.dumps(active, indent=2))
    else:
        print("\n[VERIFY] (flow_label missing; skipping)")


# --- UTF-8 console safety on Windows ---
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

print("[BOOT] Python:", sys.executable)
print("[BOOT] Platform:", platform.platform())
print("[BOOT] SF_ORG:", os.getenv("SF_ORG", ""))
print("[BOOT] LLM endpoint:", os.getenv("OLLAMA_URL", ""))
print("[BOOT] LLM model:", os.getenv("LLM_MODEL", ""))

# Connect to Salesforce (optional; safe to fail)
try:
    sf = Salesforce(
        username=os.getenv("SF_USERNAME"),
        password=os.getenv("SF_PASSWORD"),
        security_token=os.getenv("SF_SECURITY_TOKEN"),
        domain=os.getenv("SF_DOMAIN", "test"),
    )
    print("[BOOT] simple_salesforce session established")
except Exception as e:
    print(f"[BOOT] simple_salesforce not initialized: {e}")

if len(sys.argv) < 2:
    print('Usage: python agent.py "<natural language flow spec>"')
    sys.exit(1)

nl_spec = sys.argv[1]
print("\n[RUN] Spec:", nl_spec)

# Working dir for generated metadata
OUT = Path("out_flows")
OUT.mkdir(parents=True, exist_ok=True)

# Load config (with safe fallback if config.py is missing)
try:
    from config import load_agent_config  # optional module
    CFG = load_agent_config()
except Exception:
    CFG = {
        # tweak as you like; passed into graph via state["config"]
        "planner": {"max_retries": 1},
        "deploy": {"autofix": True},
        "inspect": {"skip": os.getenv("SKIP_INSPECT") == "1"},
    }
    print("[BOOT] Using default CFG:", json.dumps(CFG))

# Build the graph (new signature expects config)
graph = build_graph(workdir=str(OUT), config=CFG)

# Initial state passed to the graph
state = {"spec_text": nl_spec, "config": CFG}

print("[RUN] Invoking graph...")
result = graph.invoke(state)
print("[RUN] Graph returned keys:", list(result.keys()))

print("\n=== PLAN ===")
print(json.dumps(result.get("plan", {}), indent=2))

if "flow_dir" not in result:
    print("\n[RESULT] No flow_dir produced — check PLAN and earlier logs.")
    sys.exit(2)

print(f"\n[RESULT] Generated flow at: {result['flow_dir']}")

# Deployment
org_alias = os.getenv("SF_ORG", "")

if os.getenv("SKIP_DEPLOY") == "1":
    print(f"\n(SKIP_DEPLOY=1) Not deploying. To deploy later:")
    print(f"  cd {result['flow_dir']}")
    print(f"  sf project deploy start --source-dir . --target-org {org_alias or '<yourAlias>'}")
    sys.exit(0)

ensure_sf_cli()
print("\n[DEPLOY] Starting deploy...")
deploy_source_dir(result["flow_dir"], org_alias)
print("[DEPLOY] Done.")

flow_label = result.get("flow_label")
if flow_label:
    print("\n[VERIFY] Querying FlowDefinition/ActiveVersion ...")
    active = query_flow_activation(flow_label, org_alias)
    print(json.dumps(active, indent=2))
else:
    print("\n[VERIFY] (flow_label missing; skipping)")
