# =================== tools/flow_templates.py ====================
from typing import Tuple, Dict, Any, Optional
from pathlib import Path
import json
from .spec import FlowSpec

API_VERSION = "60.0"

def _xy(x: int, y: int) -> str:
    return f"    <locationX>{x}</locationX>\n    <locationY>{y}</locationY>"

def _xml_header() -> str:
    return """<?xml version="1.0" encoding="UTF-8"?>
<Flow xmlns="http://soap.sforce.com/2006/04/metadata">"""

def _xml_footer() -> str:
    return "</Flow>\n"

def _start_block(spec: FlowSpec, add_xy: bool) -> str:
    rt = {"Create": "Create", "Update": "Update", "CreateOrUpdate": "CreateOrUpdate"}[spec.trigger]

    # filters
    filters_xml = []
    op_map = {"equals": "EqualTo", "notEquals": "NotEqualTo", "contains": "Contains"}
    for c in spec.conditions:
        left = c.get("left"); op = c.get("op", "equals"); val = c.get("right")
        if left and left.startswith("RecordType."):
            filters_xml.append(
                "    <formula>\n"
                "      <dataType>Boolean</dataType>\n"
                f"      <expression>$Record.RecordType.DeveloperName = '{val}'</expression>\n"
                "    </formula>"
            )
        else:
            field_path = f"{spec.object_api}.{left}" if left else ""
            filters_xml.append(
                "    <filters>\n"
                f"      <field>{field_path}</field>\n"
                f"      <operator>{op_map.get(op, 'EqualTo')}</operator>\n"
                f"      <value>{val}</value>\n"
                "    </filters>"
            )

    xy_start = (_xy(100, 100) + "\n") if add_xy else ""
    filters_join = ("\n".join(filters_xml) + "\n") if filters_xml else ""

    return (
        f"  <startElementReference>start</startElementReference>\n"
        f"  <start>\n"
        f"{xy_start}"
        f"    <connector>\n"
        f"      <targetReference>post_start</targetReference>\n"
        f"    </connector>\n"
        f"    <object>{spec.object_api}</object>\n"
        f"    <recordTriggerType>{rt}</recordTriggerType>\n"
        f"    <triggerType>RecordAfterSave</triggerType>\n"
        f"{filters_join}"
        f"  </start>"
    )


def _create_task_call_xml(step_name: str, spec: FlowSpec, act: Dict[str, Any], add_xy: bool) -> Tuple[str, str]:
    def esc(s: Optional[str]) -> str:
        return (s or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;") \
                        .replace('"', "&quot;").replace("'", "&apos;")

    subject = esc(act.get("subject") or "New Task")
    due_days = int(act.get("due_in_days") or 0)

    owner = act.get("owner") or "record_owner"
    if owner == "record_owner":
        owner_ref = "{!$Record.OwnerId}"
    elif owner == "creator":
        owner_ref = "{!$Record.CreatedById}"
    elif owner.startswith("user_id:"):
        owner_ref = owner.split(":", 1)[1]
    else:
        owner_ref = "{!$Record.OwnerId}"

    what_id = (act.get("what_id") or "record").strip()
    if what_id == "record":
        what_ref = "{!$Record.Id}"
    elif what_id.endswith("__c"):
        what_ref = "{!$Record." + what_id + "}"
    else:
        what_ref = what_id

    who_id = (act.get("who_id") or "").strip()
    who_ref = "{!$Record." + who_id + "}" if who_id else ""

    status = esc(act.get("status") or "Not Started")
    priority = esc(act.get("priority") or "Normal")

    # NB: Keep assignments minimal to avoid schema errors – no valueDataType/isLiteral tags.
    ia = []
    ia.append(
        "    <inputAssignments>\n"
        "      <field>Subject</field>\n"
        f"      <value>{subject}</value>\n"
        "    </inputAssignments>"
    )
    if due_days:
        ia.append(
        "    <inputAssignments>\n"
        "      <field>ActivityDate</field>\n"
        f"      <value>{{!TODAY()+{due_days}}}</value>\n"
        "    </inputAssignments>"
        )
    ia.append(
        "    <inputAssignments>\n"
        "      <field>OwnerId</field>\n"
        f"      <value>{esc(owner_ref)}</value>\n"
        "    </inputAssignments>"
    )
    if what_ref:
        ia.append(
        "    <inputAssignments>\n"
        "      <field>WhatId</field>\n"
        f"      <value>{esc(what_ref)}</value>\n"
        "    </inputAssignments>"
        )
    if who_ref:
        ia.append(
        "    <inputAssignments>\n"
        "      <field>WhoId</field>\n"
        f"      <value>{esc(who_ref)}</value>\n"
        "    </inputAssignments>"
        )
    ia.append(
        "    <inputAssignments>\n"
        "      <field>Status</field>\n"
        f"      <value>{status}</value>\n"
        "    </inputAssignments>"
    )
    ia.append(
        "    <inputAssignments>\n"
        "      <field>Priority</field>\n"
        f"      <value>{priority}</value>\n"
        "    </inputAssignments>"
    )

    element = (
        "  <recordCreates>\n"
        f"    <name>{step_name}</name>\n"
        f"    <label>{subject or 'Create Task'}</label>\n"
        + (_xy(360, 100) + "\n" if add_xy else "")
        + "\n".join(ia) + "\n"
        "    <object>Task</object>\n"
        "    <connector>\n"
        "      <targetReference>done</targetReference>\n"
        "    </connector>\n"
        "  </recordCreates>"
    )
    return element, "done"

def _send_email_action_xml(step_name: str, action: Dict[str, Any], add_xy: bool) -> Tuple[str, str]:
    assigns = []
    if action.get("template_name"):
        assigns.append(
            "    <inputParameters>\n"
            "      <name>emailTemplateNameOrId</name>\n"
            f"      <stringValue>{action['template_name']}</stringValue>\n"
            "    </inputParameters>"
        )
    else:
        if action.get("to_addresses"):
            assigns.append(
                "    <inputParameters>\n"
                "      <name>recipientAddresses</name>\n"
                f"      <stringValue>{action['to_addresses']}</stringValue>\n"
                "    </inputParameters>"
            )
        if action.get("email_subject"):
            assigns.append(
                "    <inputParameters>\n"
                "      <name>emailSubject</name>\n"
                f"      <stringValue>{action['email_subject']}</stringValue>\n"
                "    </inputParameters>"
            )
        if action.get("email_body"):
            assigns.append(
                "    <inputParameters>\n"
                "      <name>emailBody</name>\n"
                f"      <stringValue>{action['email_body']}</stringValue>\n"
                "    </inputParameters>"
            )

    xy_ac = (_xy(500, 100) + "\n") if add_xy else ""
    assigns_xml = "\n".join(assigns) + ("\n" if assigns else "")

    elements = (
        f"  <actionCalls>\n"
        f"    <name>{step_name}</name>\n"
        f"    <label>{step_name}</label>\n"
        f"{xy_ac}"
        f"    <actionName>SendEmail</actionName>\n"
        f"    <actionType>coreAction</actionType>\n"
        f"    <connector>\n"
        f"      <targetReference>done</targetReference>\n"
        f"    </connector>\n"
        f"{assigns_xml}"
        f"    <storeOutputAutomatically>true</storeOutputAutomatically>\n"
        f"  </actionCalls>"
    )
    return elements, "done"


def build_flow_xml(spec: FlowSpec, cfg: Optional[Dict[str, Any]] = None) -> str:
    d = (cfg or {}).get("defaults", {})
    add_xy = bool(d.get("add_canvas_coordinates", True))
    emit_router = bool(d.get("emit_decision_router", True))

    parts = [
        _xml_header(),
        f"  <apiVersion>{API_VERSION}</apiVersion>",
        f"  <label>{spec.flow_label}</label>",
        "  <processMetadataValues>\n"
        "    <name>BuilderType</name>\n"
        "    <value>\n"
        "      <stringValue>LightningFlowBuilder</stringValue>\n"
        "    </value>\n"
        "  </processMetadataValues>",
        "  <processType>AutoLaunchedFlow</processType>",
        _start_block(spec, add_xy),
        "  <stages/>\n  <status>Active</status>",
    ]

# inside build_flow_xml(), where we build the post_start decisions block:

    if emit_router:
        xy = (_xy(220, 100) + "\n") if add_xy else ""
        parts.append(
            (
                "  <decisions>\n"
                "    <name>post_start</name>\n"
                "    <label>post_start</label>\n"
                f"{xy}"
                "    <defaultConnector>\n"
                "      <targetReference>step1</targetReference>\n"
                "    </defaultConnector>\n"
                "    <rules>\n"
                "      <name>Rule_Never</name>\n"
                "      <label>Rule_Never</label>\n"
                "      <conditionLogic>and</conditionLogic>\n"
                "      <conditions>\n"
                "        <leftValueReference>$GlobalConstant.True</leftValueReference>\n"
                "        <operator>EqualTo</operator>\n"
                "        <rightValue>\n"
                "          <booleanValue>false</booleanValue>\n"
                "        </rightValue>\n"
                "      </conditions>\n"
                "      <connector>\n"
                "        <targetReference>done</targetReference>\n"
                "      </connector>\n"
                "    </rules>\n"
                "  </decisions>"
            )
        )



    step_index = 1
    for act in spec.actions:
        step_name = f"step{step_index}"
        if act.type == "create_task":
            el, _ = _create_task_call_xml(step_name, spec, act.dict(), add_xy)
        elif act.type == "send_email":
            el, _ = _send_email_action_xml(step_name, act.dict(), add_xy)
        else:
            step_index += 1
            continue
        parts.append(el)
        step_index += 1

    parts.append(_xml_footer())
    return "\n".join(parts)

def write_flow_package(spec: FlowSpec, workdir: Optional[str], cfg: Optional[Dict[str, Any]] = None) -> Tuple[str, str]:
    if workdir is None:
        workdir = "out_flows"
    w = Path(workdir) / spec.flow_label
    (w / "flows").mkdir(parents=True, exist_ok=True)

    xml = build_flow_xml(spec, cfg)
    flow_path = w / "flows" / f"{spec.flow_label}.flow-meta.xml"
    flow_path.write_text(xml, encoding="utf-8")

    sfdx_json = {
        "packageDirectories": [{"path": ".", "default": True}],
        "namespace": "",
        "sfdcLoginUrl": "https://login.salesforce.com",
        "sourceApiVersion": API_VERSION.split(".")[0],
    }
    (w / "sfdx-project.json").write_text(json.dumps(sfdx_json, indent=2))
    return str(w), spec.flow_label
