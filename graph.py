# ============================ graph.py ==========================
from __future__ import annotations
import os, json
from typing import Dict, Any
from langgraph.graph import StateGraph
from tools.spec import FlowSpec, parse_spec
from tools.flow_templates import write_flow_package
from tools.sf_cli import list_object_fields
from llm import chat
from tools.data_ops import create_record_and_get_ticket
from tools.redmine_ops import create_redmine_ticket, list_redmine_tickets

def _detect_node(state: Dict[str, Any]) -> Dict[str, Any]:
    txt = (state.get("spec_text") or "").lower()
    
    # Simple keyword detection for Redmine
    if "redmine" in txt:
        return {"intent": "redmine"}

    cfg = state.get("config") or {}
    for intent in (cfg.get("intents") or []):
        if intent.get("name") == "create_record":
            for pat in intent.get("match_any", []):
                # very simple contains test; replace with real matcher later
                if all(piece.strip("* ") in txt for piece in pat.split("*")):
                    return {
                        "intent": "create_record",
                        "object_api": intent.get("object_api"),
                        "ticket_field": intent.get("ticket_field"),
                    }
    return {"intent": "flow"}  # default

def _redmine_node(state: Dict[str, Any]) -> Dict[str, Any]:
    print("[REDMINE] Enter")
    txt = state.get("spec_text", "")
    
    # Very basic intent parsing for demo purposes
    # "create ticket for project X subject Y"
    # "list tickets"
    
    if "list" in txt.lower():
        result = list_redmine_tickets()
    else:
        # Default to create
        # Heuristic: assume project is first word after "project" or default to 1
        # assume subject is everything else
        project_id = "1" # Default project ID
        subject = "New Ticket from Agent"
        desc = txt
        
        # Try to extract project
        words = txt.split()
        if "project" in words:
            try:
                idx = words.index("project")
                if idx + 1 < len(words):
                    project_id = words[idx+1]
            except:
                pass
        
        # Use LLM to extract details if needed, for now simple pass-through
        result = create_redmine_ticket(project_id, subject=txt, description=f"Created via agent from request: {txt}")
        
    print(f"[REDMINE] Result: {result}")
    return {"redmine_result": result}

def _data_node(state: Dict[str, Any]) -> Dict[str, Any]:
    object_api = state["object_api"]
    ticket_field = state.get("ticket_field") or "Name"
    user_text = state.get("spec_text","")
    print(f"[DATA] Creating {object_api} (ticket_field={ticket_field})")
    rec_id, ticket, used = create_record_and_get_ticket(object_api, ticket_field, user_text)
    print(f"[DATA] Inserted Id={rec_id} | {ticket_field}={ticket}")
    return {"record_id": rec_id, "ticket_value": ticket, "payload_used": used}


def _plan_node(state: Dict[str, Any]) -> Dict[str, Any]:
    print("[PLAN] Enter")
    user = state.get("spec_text", "")
    print("[PLAN] spec_text:", user)

    # Baseline system prompt (tight schema + “admin only” guard)
    sys_prompt = (
        "You are a Salesforce Flow Planner. You design administrative CRM automation only — "
        "no real-world/physical instructions. Interpret all requests as internal business workflow.\n"
        "- If the user asks for automation that runs on record create/update, choose a Record-Triggered After-Save flow.\n"
        "- Prefer simple decision criteria (field equals/contains/value).\n"
        "- Support two actions ONLY: 'create_task' and 'send_email'.\n"
        "- Output ONLY JSON with keys: flow_label, object_api, trigger, conditions, actions.\n"
        "- actions is an array of objects. create_task supports: subject, due_in_days, "
        "  owner ('record_owner'|'creator'|'user_id:<id>'), what_id ('record'|'<lookup field api>'), "
        "  who_id optional, priority, status. send_email supports: template_name OR "
        "  raw fields (to_addresses, email_subject, email_body).\n"
        "- flow_label must be PascalCase, no spaces.\n"
        "- If the request is unrelated to these actions, reinterpret minimally to fit the schema.\n"
    )

    raw = chat(sys_prompt, user)
    print("[PLAN] LLM raw:\n", raw)

    def try_parse(txt: str) -> Dict[str, Any] | None:
        try:
            start = txt.find("{")
            end = txt.rfind("}")
            if 0 <= start < end:
                txt = txt[start : end + 1]
            return json.loads(txt)
        except Exception:
            return None

    data = try_parse(raw)

    # Retry once with an even stricter, JSON-only instruction if parsing failed/refused
    if not data:
        print("[PLAN] First attempt not JSON; retrying with JSON-ONLY framing.")
        sys_prompt_retry = (
            sys_prompt
            + "\nCRITICAL: Respond with a single JSON object only. No prose. No apologies. "
            "If uncertain, make reasonable defaults. Keys: flow_label, object_api, trigger, conditions, actions."
        )
        raw2 = chat(sys_prompt_retry, user)
        print("[PLAN] LLM raw (retry):\n", raw2)
        data = try_parse(raw2)

    if not data:
        msg = raw.strip().splitlines()[0] if raw.strip() else "Planner did not return JSON."
        raise RuntimeError(f"Planner failed to return JSON: {msg}")

    # normalize into FlowSpec
    plan = parse_spec(json.dumps(data))
    print("[PLAN] Normalized plan:", plan.json(indent=2))
    return {"plan": plan.dict()}


def _inspect_node(state: Dict[str, Any]) -> Dict[str, Any]:
    print("\n[INSPECT] Enter")
    if "plan" not in state:
        print("[INSPECT] ERROR: plan missing in state")
        return state  # pass through whatever we have to avoid hard crash

    # Rehydrate for convenience & validation
    plan = FlowSpec(**state["plan"])
    print(f"[INSPECT] Object: {plan.object_api} | Trigger: {plan.trigger}")
    print(f"[INSPECT] Conditions: {plan.conditions}")
    print(f"[INSPECT] Actions: {[a.dict() for a in plan.actions]}")

    if os.getenv("SKIP_INSPECT") == "1":
        print("[INSPECT] SKIP_INSPECT=1 -> skipping schema check")
        return {"plan": state["plan"], "schema": [], "missing_fields": []}

    # Collect referenced fields (rough heuristic)
    referenced: set[str] = set()
    for cond in plan.conditions:
        left = cond.get("left") if isinstance(cond, dict) else None
        if left:
            referenced.add(str(left).split(".")[0])

    for act in plan.actions:
        if getattr(act, "type", None) == "create_task":
            wi = getattr(act, "what_id", "") or ""
            who = getattr(act, "who_id", None)
            if wi not in ("record", "") and "__c" in wi:
                referenced.add(wi)
            if who:
                referenced.add(who)

    print(f"[INSPECT] Referenced tokens: {sorted(referenced)}")

    # Ask CLI for fields (safe no-op if CLI missing, per sf_cli.py)
    schema = list_object_fields(plan.object_api, os.getenv("SF_ORG", ""))
    names = {f.get("QualifiedApiName") or f.get("name") for f in schema}
    missing: list[str] = []
    if schema:
        for r in referenced:
            if r and r not in names and not str(r).startswith("RecordType"):
                missing.append(r)

    print(f"[INSPECT] Fields returned: {len(schema)} | Missing refs: {missing}")

    # Carry plan forward + inspection results
    return {"plan": state["plan"], "schema": schema, "missing_fields": missing}


def _draft_node(state: Dict[str, Any]) -> Dict[str, Any]:
    print("\n[DRAFT] Enter")
    if "plan" not in state:
        print("[DRAFT] ERROR: plan missing in state")
        return state

    plan = FlowSpec(**state["plan"])
    workdir = state.get("workdir")
    print(f"[DRAFT] Writing flow package | workdir={workdir}")

    flow_dir, flow_label = write_flow_package(plan, workdir)
    print(f"[DRAFT] Flow written: {flow_dir} (label={flow_label})")

    return {"plan": state["plan"], "flow_dir": flow_dir, "flow_label": flow_label}


def build_graph(workdir: str, config: dict):
    g = StateGraph(dict)

    def _entry(state):
        return {**state, "workdir": workdir, "config": config}

    g.add_node("entry", _entry)
    g.add_node("detect", _detect_node)
    g.add_node("data", _data_node)
    g.add_node("redmine", _redmine_node)
    g.add_node("plan", _plan_node)
    g.add_node("inspect", _inspect_node)
    g.add_node("draft", _draft_node)

    g.set_entry_point("entry")
    g.add_edge("entry", "detect")

    # branch
    def router(state):
        intent = state.get("intent")
        if intent == "redmine":
            return "redmine"
        elif intent == "create_record":
            return "data"
        else:
            return "plan"

    g.add_conditional_edges(
        "detect",
        router,
        {
            "redmine": "redmine",
            "data": "data",
            "plan": "plan"
        },
    )
    g.add_edge("plan", "inspect")
    g.add_edge("inspect", "draft")

    app = g.compile()
    def invoke(state: Dict[str, Any]):
        state = {**state, "workdir": workdir, "config": config}
        print("[GRAPH] Invoke with keys:", list(state.keys()))
        return app.invoke(state)
    return type("GraphWrapper", (), {"invoke": staticmethod(invoke)})
