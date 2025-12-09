# ======================= tools/sf_cli.py ========================
from __future__ import annotations
import os
import subprocess
import json
import shutil
from typing import List, Dict, Optional
from tools.auto_fix import apply_autofix

# --- CLI detection -----------------------------------------------------------

def _which_cli() -> Optional[str]:
    """Prefer 'sf', fall back to 'sfdx' if present on PATH."""
    for exe in ("sf", "sfdx"):
        path = shutil.which(exe)
        if path:
            return exe
    return None

def ensure_sf_cli() -> None:
    exe = _which_cli()
    if exe:
        print(f"[SF_CLI] Using {exe} at {shutil.which(exe)}")
    else:
        print("[SF_CLI] WARN: Salesforce CLI not found. Install 'sf' or 'sfdx' and log in.")

def _normalize_org_alias(org_alias: Optional[str]) -> str:
    """Use provided alias if truthy; otherwise read SF_ORG from env; else empty string."""
    return (org_alias or os.getenv("SF_ORG") or "").strip()

# --- Subprocess runner -------------------------------------------------------

def _run(cmd: list[str], cwd: Optional[str] = None, env: Optional[dict] = None) -> tuple[int, str]:
    print("$", " ".join(cmd))

    # Merge env so we keep our current process variables
    merged_env = {**os.environ, **(env or {})}

    kwargs = dict(
        cwd=cwd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,          # universal_newlines=True
        encoding="utf-8",   # avoid cp1252 decode errors on Windows
        errors="replace",   # never crash on weird bytes
        env=merged_env,
    )

    if os.name == "nt":
        # Ensure .cmd/.bat resolve via the shell reliably
        p = subprocess.run(["cmd", "/c"] + cmd, **kwargs)
    else:
        p = subprocess.run(cmd, **kwargs)

    return p.returncode, (p.stdout or "") + (p.stderr or "")

# --- Internal helper for Tooling API queries --------------------------------

def _tooling_query(soql: str, org: str) -> Dict:
    cli = _which_cli()
    if not cli:
        return {}
    # Keep the SOQL a single arg on Windows
    soql_arg = f'"{soql}"' if os.name == "nt" else soql
    if cli == "sf":
        cmd = ["sf", "data", "query", "--json", "--use-tooling-api", "--query", soql_arg]
        if org:
            cmd += ["--target-org", org]
    else:
        cmd = ["sfdx", "data:soql:query", "--json", "--usetoolingapi", "-q", soql_arg]
        if org:
            cmd += ["-u", org]
    _, out = _run(cmd)
    try:
        return json.loads(out or "{}")
    except Exception:
        print("[SF_CLI] WARN: JSON parse failed, raw follows:\n", out)
        return {}

# --- Queries / actions -------------------------------------------------------

def list_object_fields(object_api: str, org_alias: Optional[str] = None) -> List[Dict]:
    """
    Return [{'QualifiedApiName','DataType','IsNillable'}, ...].
    Tries several Tooling strategies, then falls back to REST describe().
    Super chatty so you can see where zeroes come from.
    """
    org = _normalize_org_alias(org_alias)
    print(f"[SF_CLI] Schema inspect for {object_api} (org={org or '<default>'})")

    strategies = []

    # 1) Straight QualifiedApiName (this matched your manual test)
    strategies.append((
        "FieldDefinition WHERE EntityDefinition.QualifiedApiName",
        "SELECT QualifiedApiName, DataType, IsNillable "
        f"FROM FieldDefinition WHERE EntityDefinition.QualifiedApiName = '{object_api}'"
    ))

    # 2) Via EntityDefinitionId subquery (sometimes works when #1 returns 0)
    strategies.append((
        "FieldDefinition WHERE EntityDefinitionId IN (subquery)",
        "SELECT QualifiedApiName, DataType, IsNillable FROM FieldDefinition "
        f"WHERE EntityDefinitionId IN (SELECT Id FROM EntityDefinition WHERE QualifiedApiName = '{object_api}')"
    ))

    # 3) Special case: Event/Task share Activity fields; try Activity
    if object_api in ("Event", "Task"):
        strategies.append((
            "Activity fallback for Event/Task",
            "SELECT QualifiedApiName, DataType, IsNillable "
            "FROM FieldDefinition WHERE EntityDefinition.QualifiedApiName = 'Activity'"
        ))

    # Try each strategy until we get rows
    for label, soql in strategies:
        payload = _tooling_query(soql, org)
        rows = (payload.get("result") or {}).get("records") or []
        print(f"[SF_CLI] {label}: {len(rows)} rows")
        if rows:
            return rows

    # 4) Fallback: REST describe via simple_salesforce
    try:
        from simple_salesforce import Salesforce
        sf = Salesforce(
            username=os.getenv("SF_USERNAME"),
            password=os.getenv("SF_PASSWORD"),
            security_token=os.getenv("SF_SECURITY_TOKEN"),
            domain=os.getenv("SF_DOMAIN", "test"),
        )
        desc = getattr(sf, object_api).describe()
        rows = [
            {"QualifiedApiName": f.get("name"), "DataType": f.get("type"), "IsNillable": f.get("nillable")}
            for f in (desc.get("fields") or [])
        ]
        print(f"[SF_CLI] describe() fallback: {len(rows)} rows")
        return rows
    except Exception as e:
        print(f"[SF_CLI] describe() fallback failed: {e}")

    print("[SF_CLI] No schema returned (continuing without validation).")
    return []

def deploy_source_dir(source_dir: str, org_alias: Optional[str] = None) -> None:
    """Deploy exactly one flow meta file inside source_dir/flows/*.flow-meta.xml."""
    cli = _which_cli()
    if cli is None:
        raise RuntimeError("Salesforce CLI not found in PATH")

    org = _normalize_org_alias(org_alias)

    # Pick one flow file (first match)
    flows_dir_abs = os.path.join(source_dir, "flows")
    if not os.path.isdir(flows_dir_abs):
        raise RuntimeError("No 'flows' folder under " + source_dir)

    flow_meta_rel: Optional[str] = None
    for fn in os.listdir(flows_dir_abs):
        if fn.endswith(".flow-meta.xml"):
            flow_meta_rel = os.path.join("flows", fn)
            break
    if not flow_meta_rel:
        raise RuntimeError("No *.flow-meta.xml found in " + flows_dir_abs)

    def _run_deploy() -> tuple[int, str]:
        if cli == "sf":
            cmd = [
                "sf", "project", "deploy", "start",
                "--source-dir", flow_meta_rel,
                "--target-org", org,
                "--json", "--wait", "10",
            ]
        else:
            cmd = [
                "sfdx", "force:source:deploy",
                "-p", flow_meta_rel,
                "-u", org,
                "--json", "-w", "10",
            ]
        env = os.environ.copy()
        env["TERM"] = "dumb"
        env["NO_COLOR"] = "1"
        env.setdefault("PYTHONUTF8", "1")
        print("[DEPLOY] CWD=", source_dir)
        print("[DEPLOY] Source=", flow_meta_rel)
        return _run(cmd, cwd=source_dir, env=env)

    # First attempt
    code, out = _run_deploy()
    if code == 0:
        print(out)
        return

    # Try to extract file-level errors from JSON (if any)
    print("[DEPLOY] First attempt failed, checking for auto-fixable issues...")
    issues_text = out
    try:
        data = json.loads(out or "{}")
        res = data.get("result", data)
        files = res.get("files") or []
        if isinstance(files, dict):
            files = [files]
        merged = " | ".join(
            str(f.get("error") or f.get("problem") or "") for f in files
        ).strip()
        if merged:
            issues_text = merged
    except Exception:
        pass

    # One-shot auto-fix for missing XY/rules; then retry once
    if any(k in issues_text for k in ("locationX", "locationY", "rules")):
        flow_abs = os.path.join(source_dir, flow_meta_rel)
        fixes = apply_autofix(flow_abs)
        print("[AUTOFIX]", ", ".join(fixes) if fixes else "(no changes)")
        code2, out2 = _run_deploy()
        if code2 == 0:
            print(out2)
            return
        # bubble the second failure with its JSON (shows exact error/line)
        raise RuntimeError(out2)

    # Unhandled error: raise the original JSON/text
    raise RuntimeError(out)

def query_flow_activation(flow_label: str, org_alias: Optional[str] = None) -> Dict:
    cli = _which_cli()
    if cli is None:
        return {"error": "CLI not found"}

    org = _normalize_org_alias(org_alias)
    soql = (
        "SELECT DeveloperName, ActiveVersion.VersionNumber "
        f"FROM FlowDefinition WHERE DeveloperName = '{flow_label}'"
    )
    if cli == "sf":
        cmd = ["sf", "data", "query", "--json", "--query", soql]
        if org:
            cmd += ["--target-org", org]
    else:
        cmd = ["sfdx", "data:soql:query", "--json", "-q", soql]
        if org:
            cmd += ["-u", org]

    code, out = _run(cmd)
    try:
        return json.loads(out)
    except Exception:
        return {"raw": out}
