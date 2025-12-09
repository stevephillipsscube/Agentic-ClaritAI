# ======================== tools/spec.py =========================
from pydantic import BaseModel, Field, validator
from typing import List, Dict, Any
import json, re

class FlowAction(BaseModel):
    type: str  # "create_task" | "send_email"
    # create_task fields
    subject: str | None = None
    due_in_days: int | None = None
    owner: str | None = None  # record_owner | creator | user_id:<id>
    what_id: str | None = None  # record | <lookup field api>
    who_id: str | None = None  # optional lookup
    priority: str | None = None
    status: str | None = None
    # send_email fields
    template_name: str | None = None
    to_addresses: str | None = None
    email_subject: str | None = None
    email_body: str | None = None

class FlowSpec(BaseModel):
    flow_label: str = Field(..., description="PascalCase flow label")
    object_api: str = Field(..., description="Trigger object API name")
    trigger: str = Field(..., description="Create|Update|CreateOrUpdate")
    conditions: List[Dict[str, Any]] = Field(default_factory=list)
    actions: List[FlowAction] = Field(default_factory=list)

    @validator("flow_label")
    def no_spaces(cls, v):
        if not re.match(r"^[A-Za-z0-9_]+$", v):
            raise ValueError("flow_label must be alnum/underscore (no spaces)")
        return v

# --- Normalizers ------------------------------------------------

def _normalize_condition(c: Any) -> Dict[str, Any] | None:
    """Coerce various condition shapes into {'left','op','right'}."""
    if isinstance(c, dict):
        left = c.get("left") or c.get("field") or c.get("name")
        op = (c.get("op") or c.get("operator") or "equals").lower()
        right = c.get("right") or c.get("value") or c.get("val")
        if left is not None and right is not None:
            op_map = {"=": "equals", "==": "equals", "equals": "equals",
                      "contains": "contains", "!=": "notEquals", "<>": "notEquals", "notequals": "notEquals"}
            op = op_map.get(op, op)
            return {"left": left, "op": op, "right": right}
        return None
    if isinstance(c, str):
        m = re.match(r"\s*([A-Za-z0-9_.]+)\s*(==|=|!=|<>|contains)\s*['\"]?(.+?)['\"]?\s*$", c, re.I)
        if m:
            left, op_raw, right = m.group(1), m.group(2).lower(), m.group(3)
            op_map = {"=": "equals", "==": "equals", "contains": "contains", "!=": "notEquals", "<>": "notEquals"}
            return {"left": left, "op": op_map.get(op_raw, "equals"), "right": right}
        return None
    return None

def _normalize_action(a: Any) -> Dict[str, Any] | None:
    """
    Ensure an action dict always has a 'type'.
    Infer type when missing based on keys or simple string hints.
    """
    if a is None:
        return None

    if isinstance(a, str):
        s = a.strip().lower()
        if "email" in s:
            return {"type": "send_email"}
        # default to task if it mentions task/create
        if "task" in s or "create" in s:
            return {"type": "create_task"}
        return None

    if isinstance(a, dict):
        t = (a.get("type") or a.get("action") or a.get("name") or "").strip().lower()
        # map common synonyms
        alias = {
            "createtask": "create_task",
            "create_task": "create_task",
            "task": "create_task",
            "sendemail": "send_email",
            "send_email": "send_email",
            "email": "send_email",
        }
        t = alias.get(t, t)

        if not t:
            # infer from keys
            if any(k in a for k in ("template_name", "to_addresses", "email_subject", "email_body")):
                t = "send_email"
            elif any(k in a for k in ("subject", "due_in_days", "owner", "what_id", "who_id", "priority", "status")):
                t = "create_task"

        if not t:
            return None  # still unknown; drop it

        out: Dict[str, Any] = {"type": t}

        # copy only known fields for that type
        if t == "create_task":
            for k in ("subject", "due_in_days", "owner", "what_id", "who_id", "priority", "status"):
                if k in a and a[k] is not None:
                    out[k] = a[k]
            # helpful defaults
            out.setdefault("subject", "Automated Task")
            out.setdefault("due_in_days", 1)
            out.setdefault("owner", "record_owner")
            out.setdefault("what_id", "record")
            out.setdefault("status", "Not Started")
            out.setdefault("priority", "Normal")
        else:  # send_email
            for k in ("template_name", "to_addresses", "email_subject", "email_body"):
                if k in a and a[k] is not None:
                    out[k] = a[k]
        return out

    return None

# --- Public API -------------------------------------------------

def parse_spec(txt: str) -> FlowSpec:
    data = json.loads(txt)

    # normalize trigger
    trig = data.get("trigger", "Create")
    if trig not in ("Create", "Update", "CreateOrUpdate"):
        trig = "Create"
    data["trigger"] = trig

    # normalize conditions
    conds = data.get("conditions", []) or []
    if isinstance(conds, dict):
        conds = [conds]
    data["conditions"] = [nc for c in conds if (nc := _normalize_condition(c))]

    # normalize actions
    acts = data.get("actions", []) or []
    if isinstance(acts, dict):
        acts = [acts]
    norm_actions = [na for a in acts if (na := _normalize_action(a))]
    if not norm_actions:
        # As a last resort, default to a create_task so FlowSpec validates
        norm_actions = [{"type": "create_task", "subject": "Automated Task", "due_in_days": 1,
                         "owner": "record_owner", "what_id": "record", "status": "Not Started", "priority": "Normal"}]
    data["actions"] = norm_actions

    return FlowSpec(**data)
