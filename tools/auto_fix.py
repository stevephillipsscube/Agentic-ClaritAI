# ======================= tools/auto_fix.py ======================
from __future__ import annotations
import re
from pathlib import Path
from typing import List, Match


def _insert_after_close_label(block: str, snippet: str) -> str:
    """Insert snippet right after the first </label> (or </name> fallback)."""
    i = block.find("</label>")
    if i == -1:
        j = block.find("</name>")
        if j == -1:
            return block + snippet
        return block[: j + len("</name>")] + "\n" + snippet + block[j + len("</name>") :]
    return block[: i + len("</label>")] + "\n" + snippet + block[i + len("</label>") :]


def _ensure_xy_in_block(block: str, x: int, y: int) -> tuple[str, bool]:
    """Ensure a block has <locationX>/<locationY> tags."""
    if "<locationX>" in block and "<locationY>" in block:
        return block, False
    snippet = f"    <locationX>{x}</locationX>\n    <locationY>{y}</locationY>"
    return _insert_after_close_label(block, snippet), True


def _ensure_connector_to_done(block: str) -> tuple[str, bool]:
    """Ensure a block has a <connector><targetReference>done</targetReference></connector>."""
    if "<connector>" in block:
        return block, False
    snippet = (
        "    <connector>\n"
        "      <targetReference>done</targetReference>\n"
        "    </connector>"
    )
    return _insert_after_close_label(block, snippet), True


def _ensure_decision_rules(block: str) -> tuple[str, bool]:
    if "<rules>" in block:
        # also patch any rightValueReference->rightValue boolean
        patched = re.sub(
            r"<rightValueReference>\s*\$GlobalConstant\.False\s*</rightValueReference>",
            "<rightValue><booleanValue>false</booleanValue></rightValue>",
            block,
            flags=re.I,
        )
        return patched, (patched != block)

    snippet = (
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
        "    </rules>"
    )
    return _insert_after_close_label(block, snippet), True



def autofix_locations_and_connectors(xml: str) -> tuple[str, List[str]]:
    """
    Add missing <locationX>/<locationY> to start/decisions/recordCreates/actionCalls,
    add a default <connector> to recordCreates/actionCalls if missing,
    and ensure <decisions> has a <rules> block.
    """
    fixes: List[str] = []

    # --- start ---
    m = re.search(r"<start>.*?</start>", xml, flags=re.DOTALL)
    if m:
        block = m.group(0)
        if "<locationX>" not in block or "<locationY>" not in block:
            fixed = block.replace(
                "<start>",
                "<start>\n    <locationX>100</locationX>\n    <locationY>100</locationY>",
                1,
            )
            xml = xml[: m.start()] + fixed + xml[m.end() :]
            fixes.append("add XY to <start>")

    # --- decisions (may be multiple; fix each) ---
    def _fix_decision(mo: Match[str]) -> str:
        block = mo.group(0)
        fixed, changed_xy = _ensure_xy_in_block(block, 220, 100)
        fixed, changed_rules = _ensure_decision_rules(fixed)
        if changed_xy or changed_rules:
            fixes.append("fix <decisions> (XY/rules)")
        return fixed

    xml = re.sub(r"<decisions>.*?</decisions>", _fix_decision, xml, flags=re.DOTALL)

    # --- recordCreates ---
    def _fix_record_creates(mo: Match[str]) -> str:
        block = mo.group(0)
        fixed = block
        changed_any = False
        fixed, changed = _ensure_xy_in_block(fixed, 360, 100)
        changed_any = changed_any or changed
        fixed, changed = _ensure_connector_to_done(fixed)
        changed_any = changed_any or changed
        if changed_any:
            fixes.append("fix <recordCreates> (XY/connector)")
        return fixed

    xml = re.sub(r"<recordCreates>.*?</recordCreates>", _fix_record_creates, xml, flags=re.DOTALL)

    # --- actionCalls ---
    def _fix_action_calls(mo: Match[str]) -> str:
        block = mo.group(0)
        fixed = block
        changed_any = False
        fixed, changed = _ensure_xy_in_block(fixed, 500, 100)
        changed_any = changed_any or changed
        fixed, changed = _ensure_connector_to_done(fixed)
        changed_any = changed_any or changed
        if changed_any:
            fixes.append("fix <actionCalls> (XY/connector)")
        return fixed

    xml = re.sub(r"<actionCalls>.*?</actionCalls>", _fix_action_calls, xml, flags=re.DOTALL)

    return xml, fixes


def apply_autofix(flow_path: str) -> List[str]:
    p = Path(flow_path)
    src = p.read_text(encoding="utf-8")
    new, fixes = autofix_locations_and_connectors(src)
    if fixes:
        p.write_text(new, encoding="utf-8")
    return fixes
