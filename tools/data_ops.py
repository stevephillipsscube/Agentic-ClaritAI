# tools/data_ops.py
from __future__ import annotations
import os, re, random, string
from typing import Dict, Any, Tuple, List
from simple_salesforce import Salesforce, SalesforceMalformedRequest

def _connect() -> Salesforce:
    return Salesforce(
        username=os.getenv("SF_USERNAME"),
        password=os.getenv("SF_PASSWORD"),
        security_token=os.getenv("SF_SECURITY_TOKEN"),
        domain=os.getenv("SF_DOMAIN", "test"),
    )

def _describe(sf: Salesforce, sobject: str) -> Dict[str, Any]:
    # Access dynamic attr: sf.TreeClearingApplication__c.describe()
    return getattr(sf, sobject).describe()

def _placeholder(field: Dict[str, Any]) -> Any:
    t = (field.get("type") or "").lower()
    if t in ("string", "textarea", "phone", "email", "url"):
        base = "Auto"
        return base + "-" + "".join(random.choices(string.ascii_uppercase + string.digits, k=6))
    if t in ("double","currency","percent","int","long"):
        return 1
    if t in ("boolean",):
        return True
    if t in ("date",):
        from datetime import date
        return date.today().isoformat()
    if t in ("datetime",):
        from datetime import datetime, timezone
        return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000+0000")
    if t in ("picklist",):
        vals = [v.get("value") for v in (field.get("picklistValues") or []) if v.get("active")]
        return vals[0] if vals else None
    # lookups / reference: best effort OwnerId -> me
    if t in ("reference",):
        # try current user for OwnerId; otherwise leave None (server may default)
        if field.get("name") == "OwnerId":
            return None  # SF will often default
        return None
    return None

def _required_fields(desc: Dict[str, Any]) -> List[Dict[str, Any]]:
    fields = desc.get("fields") or []
    req = []
    for f in fields:
        if f.get("createable") and not f.get("nillable") and not f.get("defaultedOnCreate"):
            name = f.get("name")
            # Skip system ids created by platform
            if name in ("Id",):
                continue
            req.append(f)
    return req

def create_record_and_get_ticket(
    object_api: str,
    ticket_field: str,
    user_text: str
) -> Tuple[str, Any, Dict[str, Any]]:
    """
    Tries to create `object_api` with placeholders for required fields.
    If SF returns REQUIRED_FIELD_MISSING, fills them and retries up to 3 times.
    Returns (record_id, ticket_value, payload_used).
    """
    sf = _connect()
    desc = _describe(sf, object_api)
    req_fields = _required_fields(desc)

    payload: Dict[str, Any] = {}
    # naive mapping from user_text like "applicant email is x" could be added later
    # for now, prefill placeholders for all required fields we can
    for f in req_fields:
        val = _placeholder(f)
        if val is not None:
            payload[f["name"]] = val

    def _insert(p: Dict[str, Any]) -> str:
        res = getattr(sf, object_api).create(p)
        # simple_salesforce returns {'id': ..., 'success': True, 'errors': []}
        if not res.get("success"):
            raise SalesforceMalformedRequest(res.get("errors"))
        return res["id"]

    # up to 3 attempts, auto-filling missing fields if server tells us
    last_err = None
    for _ in range(3):
        try:
            rec_id = _insert(payload)
            # fetch ticket field if present
            q = f"SELECT {ticket_field} FROM {object_api} WHERE Id = '{rec_id}'"
            qr = sf.query(q)
            val = None
            if qr.get("records"):
                val = qr["records"][0].get(ticket_field)
            return rec_id, val, payload
        except SalesforceMalformedRequest as e:
            last_err = e
            # parse which fields are missing and fill sensible defaults
            msgs = []
            for err in (getattr(e, "content", None) or []):
                msg = err.get("message","")
                if "REQUIRED_FIELD_MISSING" in (err.get("errorCode","")) or "Required fields are missing" in msg:
                    flds = err.get("fields") or []
                    msgs.extend(flds)
            changed = False
            for f in req_fields:
                name = f["name"]
                if name not in payload and name in msgs:
                    val = _placeholder(f)
                    if val is not None:
                        payload[name] = val
                        changed = True
            if not changed:
                break
    # if here, failed
    raise last_err or RuntimeError("Insert failed")
