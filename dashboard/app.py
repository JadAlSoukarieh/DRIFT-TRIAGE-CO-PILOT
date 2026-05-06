"""Streamlit dashboard for Drift Triage Co-Pilot."""

from __future__ import annotations

from html import escape
import os
from typing import Any

import requests
import streamlit as st


st.set_page_config(
    page_title="Drift Triage Co-Pilot",
    page_icon="T",
    layout="wide",
)


AGENT_BASE_URL = os.getenv("AGENT_BASE_URL", "http://localhost:8001").rstrip("/")
PLATFORM_BASE_URL = os.getenv("PLATFORM_BASE_URL", "http://localhost:8000").rstrip("/")


def get_json(url: str, timeout: int = 5) -> dict[str, Any]:
    """GET JSON from a service and return a UI-safe result object."""

    try:
        response = requests.get(url, timeout=timeout)
    except requests.Timeout:
        return {"ok": False, "status_code": None, "data": None, "error": "Request timed out."}
    except requests.ConnectionError:
        return {"ok": False, "status_code": None, "data": None, "error": "Service is unreachable."}
    except requests.RequestException as exc:
        return {"ok": False, "status_code": None, "data": None, "error": str(exc)}

    try:
        data = response.json()
    except ValueError:
        data = None
        json_error = "Response was not valid JSON."
    else:
        json_error = None

    if not response.ok:
        return {
            "ok": False,
            "status_code": response.status_code,
            "data": data,
            "error": f"HTTP {response.status_code}",
        }
    if json_error:
        return {"ok": False, "status_code": response.status_code, "data": None, "error": json_error}
    return {"ok": True, "status_code": response.status_code, "data": data, "error": None}


def post_json(url: str, payload: dict[str, Any], timeout: int = 5) -> dict[str, Any]:
    """POST JSON to a service and return a UI-safe result object."""

    try:
        response = requests.post(url, json=payload, timeout=timeout)
    except requests.Timeout:
        return {"ok": False, "status_code": None, "data": None, "error": "Request timed out."}
    except requests.ConnectionError:
        return {"ok": False, "status_code": None, "data": None, "error": "Service is unreachable."}
    except requests.RequestException as exc:
        return {"ok": False, "status_code": None, "data": None, "error": str(exc)}

    try:
        data = response.json()
    except ValueError:
        data = None
        json_error = "Response was not valid JSON."
    else:
        json_error = None

    if not response.ok:
        detail = data.get("detail") if isinstance(data, dict) else None
        if isinstance(detail, dict):
            error = detail.get("message") or f"HTTP {response.status_code}"
        elif isinstance(detail, str):
            error = detail
        else:
            error = f"HTTP {response.status_code}"
        return {"ok": False, "status_code": response.status_code, "data": data, "error": error}
    if json_error:
        return {"ok": False, "status_code": response.status_code, "data": None, "error": json_error}
    return {"ok": True, "status_code": response.status_code, "data": data, "error": None}


def check_service_health(base_url: str) -> dict[str, Any]:
    """Check a service /health endpoint."""

    result = get_json(f"{base_url}/health", timeout=3)
    data = result.get("data")
    status = data.get("status") if isinstance(data, dict) else None
    result["healthy"] = bool(result["ok"] and status == "ok")
    return result


def install_css() -> None:
    """Install custom dashboard styling."""

    st.markdown(
        """
        <style>
        :root {
            --surface: #ffffff;
            --surface-soft: #f6f8fb;
            --surface-blue: #eef5ff;
            --line: #d9e1ec;
            --text: #172033;
            --muted: #68758a;
            --green-bg: #e7f7ee;
            --green: #167647;
            --amber-bg: #fff4d6;
            --amber: #9a6700;
            --red-bg: #fde8e8;
            --red: #b42318;
            --blue-bg: #e7f0ff;
            --blue: #175cd3;
        }
        .block-container {
            padding-top: 2rem;
            padding-bottom: 3rem;
            max-width: 1380px;
        }
        .hero {
            padding: 1.4rem 1.6rem;
            border: 1px solid var(--line);
            border-radius: 14px;
            background: linear-gradient(135deg, #ffffff 0%, #f4f8ff 54%, #eef7f2 100%);
            margin-bottom: 1.25rem;
        }
        .hero h1 {
            color: var(--text);
            font-size: 2.2rem;
            line-height: 1.12;
            margin: 0;
            letter-spacing: 0;
        }
        .hero p {
            color: var(--muted);
            font-size: 1.02rem;
            margin: 0.45rem 0 0;
        }
        .kpi-card, .panel-card, .approval-card, .empty-card, .error-card {
            border: 1px solid var(--line);
            border-radius: 14px;
            background: var(--surface);
            box-shadow: 0 10px 30px rgba(21, 31, 48, 0.06);
        }
        .kpi-card {
            min-height: 132px;
            padding: 1rem 1.05rem;
        }
        .kpi-title {
            color: var(--muted);
            font-size: 0.78rem;
            font-weight: 700;
            letter-spacing: 0.04em;
            text-transform: uppercase;
            margin-bottom: 0.55rem;
        }
        .kpi-value {
            color: var(--text);
            font-size: 1.5rem;
            font-weight: 780;
            line-height: 1.2;
            margin-bottom: 0.55rem;
        }
        .kpi-detail {
            color: var(--muted);
            font-size: 0.86rem;
            line-height: 1.35;
            margin-top: 0.55rem;
        }
        .section-title {
            color: var(--text);
            font-size: 1.25rem;
            font-weight: 780;
            margin: 0.35rem 0 0.75rem;
        }
        .panel-card, .empty-card, .error-card {
            padding: 1rem 1.05rem;
            margin-bottom: 0.9rem;
        }
        .approval-card {
            padding: 1rem 1.05rem;
            margin-bottom: 0.75rem;
        }
        .approval-head {
            display: flex;
            align-items: flex-start;
            justify-content: space-between;
            gap: 1rem;
            margin-bottom: 0.85rem;
        }
        .approval-action {
            color: var(--text);
            font-size: 1.1rem;
            font-weight: 780;
            text-transform: capitalize;
        }
        .kv-grid {
            display: grid;
            grid-template-columns: repeat(2, minmax(0, 1fr));
            gap: 0.65rem 1rem;
            margin: 0.8rem 0 0.1rem;
        }
        .kv-label {
            color: var(--muted);
            font-size: 0.74rem;
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 0.04em;
        }
        .kv-value {
            color: var(--text);
            font-size: 0.92rem;
            overflow-wrap: anywhere;
        }
        .chip {
            display: inline-flex;
            align-items: center;
            border-radius: 999px;
            padding: 0.26rem 0.62rem;
            font-size: 0.76rem;
            font-weight: 760;
            line-height: 1;
            white-space: nowrap;
        }
        .chip-green { color: var(--green); background: var(--green-bg); }
        .chip-amber { color: var(--amber); background: var(--amber-bg); }
        .chip-red { color: var(--red); background: var(--red-bg); }
        .chip-blue { color: var(--blue); background: var(--blue-bg); }
        .chip-gray { color: #4b5563; background: #eef1f5; }
        .note {
            color: #344054;
            border-left: 4px solid #175cd3;
            background: var(--surface-blue);
            border-radius: 10px;
            padding: 0.75rem 0.9rem;
            margin: 0.5rem 0 1rem;
            font-size: 0.92rem;
        }
        .muted {
            color: var(--muted);
            font-size: 0.92rem;
        }
        .stButton > button {
            border-radius: 10px;
            font-weight: 760;
            min-height: 2.55rem;
            border: 1px solid var(--line);
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def chip(label: str, tone: str = "gray") -> str:
    """Render a status chip."""

    return f'<span class="chip chip-{tone}">{escape(label)}</span>'


def status_text(result: dict[str, Any]) -> tuple[str, str, str, str]:
    """Map a health result to display values."""

    if result.get("healthy"):
        return "Healthy", "healthy", "green", "Responding normally"
    if result.get("status_code"):
        return "Warning", f"HTTP {result['status_code']}", "amber", "Service returned a non-healthy response"
    return "Offline", "offline", "red", result.get("error") or "No response"


def kpi_card(title: str, value: str, chip_label: str, tone: str, detail: str) -> None:
    """Render a custom KPI card."""

    st.markdown(
        f"""
        <div class="kpi-card">
            <div class="kpi-title">{escape(title)}</div>
            <div class="kpi-value">{escape(value)}</div>
            {chip(chip_label, tone)}
            <div class="kpi-detail">{escape(detail)}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def session_defaults() -> None:
    """Initialize state keys used to persist action feedback across reruns."""

    st.session_state.setdefault("last_drift_result", None)
    st.session_state.setdefault("last_action_message", None)


def show_action_message() -> None:
    """Display the latest approval or refresh result."""

    message = st.session_state.get("last_action_message")
    if not message:
        return
    if message.get("tone") == "success":
        st.success(message["text"])
    else:
        st.error(message["text"])


def approval_value(approval: dict[str, Any], key: str, fallback: str = "-") -> str:
    """Return a display-safe approval value."""

    value = approval.get(key)
    if value is None or value == "":
        return fallback
    return str(value)


def render_approval_card(approval: dict[str, Any]) -> None:
    """Render a pending approval card and its decision controls."""

    approval_id = approval_value(approval, "approval_id", "unknown")
    action = approval_value(approval, "requested_action", "unknown")
    status = approval_value(approval, "status", "pending")
    tone = "amber" if status == "pending" else "gray"

    st.markdown(
        f"""
        <div class="approval-card">
            <div class="approval-head">
                <div>
                    <div class="approval-action">{escape(action.replace("_", " "))}</div>
                    <div class="muted">Approval ID: {escape(approval_id)}</div>
                </div>
                <div>{chip(status, tone)}</div>
            </div>
            <div class="kv-grid">
                <div><div class="kv-label">Investigation</div><div class="kv-value">{escape(approval_value(approval, "investigation_id"))}</div></div>
                <div><div class="kv-label">Drift Event</div><div class="kv-value">{escape(approval_value(approval, "drift_event_id"))}</div></div>
                <div><div class="kv-label">Target Version</div><div class="kv-value">{escape(approval_value(approval, "target_model_version"))}</div></div>
                <div><div class="kv-label">Requested By</div><div class="kv-value">{escape(approval_value(approval, "requested_by"))}</div></div>
                <div><div class="kv-label">Created</div><div class="kv-value">{escape(approval_value(approval, "created_at"))}</div></div>
                <div><div class="kv-label">Action</div><div class="kv-value">{escape(action)}</div></div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    approved_by = st.text_input(
        "Approved by",
        value="jad",
        key=f"approved_by_{approval_id}",
    )
    reason = st.text_area(
        "Reason",
        value="",
        placeholder="Optional note for the audit trail",
        key=f"reason_{approval_id}",
        height=84,
    )
    approve_col, reject_col, spacer = st.columns([1, 1, 4])
    with approve_col:
        if st.button("Approve", key=f"approve_{approval_id}", use_container_width=True):
            result = post_json(
                f"{AGENT_BASE_URL}/hil/{approval_id}/approve",
                {"approved_by": approved_by, "reason": reason or None},
            )
            if result["ok"]:
                st.session_state["last_action_message"] = {
                    "tone": "success",
                    "text": f"Approval {approval_id} approved.",
                }
            else:
                st.session_state["last_action_message"] = {
                    "tone": "error",
                    "text": f"Could not approve {approval_id}: {result['error']}",
                }
            st.rerun()
    with reject_col:
        if st.button("Reject", key=f"reject_{approval_id}", use_container_width=True):
            result = post_json(
                f"{AGENT_BASE_URL}/hil/{approval_id}/reject",
                {"approved_by": approved_by, "reason": reason or None},
            )
            if result["ok"]:
                st.session_state["last_action_message"] = {
                    "tone": "success",
                    "text": f"Approval {approval_id} rejected.",
                }
            else:
                st.session_state["last_action_message"] = {
                    "tone": "error",
                    "text": f"Could not reject {approval_id}: {result['error']}",
                }
            st.rerun()
    with spacer:
        st.empty()


def drift_kpi(result: dict[str, Any] | None) -> tuple[str, str, str, str]:
    """Return KPI values for the latest drift report."""

    if result is None:
        return "Not Run", "pending", "blue", "Run a drift report from the operations panel."
    if not result.get("ok"):
        return "Failed", "failed", "red", result.get("error") or "Drift report failed."
    data = result.get("data")
    if not isinstance(data, dict):
        return "Unknown", "warning", "amber", "Response did not match the expected shape."
    report = data.get("report") if isinstance(data.get("report"), dict) else {}
    severity = str(report.get("severity", "unknown"))
    webhook_sent = data.get("webhook_sent")
    label = "success" if webhook_sent else "warning"
    tone = "green" if webhook_sent else "amber"
    detail = f"Severity: {severity}. Webhook sent: {webhook_sent}."
    return severity.title(), label, tone, detail


def render_dashboard() -> None:
    """Render the full Streamlit dashboard."""

    install_css()
    session_defaults()

    st.markdown(
        """
        <div class="hero">
            <h1>Drift Triage Co-Pilot</h1>
            <p>Monitor drift, review approvals, and coordinate response actions.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.markdown(
        """
        <div class="note">
            Replay/retrain jobs are queued for the worker. Production-changing actions require HIL approval.
        </div>
        """,
        unsafe_allow_html=True,
    )
    show_action_message()

    platform_health = check_service_health(PLATFORM_BASE_URL)
    agent_health = check_service_health(AGENT_BASE_URL)
    approvals_result = get_json(f"{AGENT_BASE_URL}/hil/pending", timeout=5)
    approvals_payload = approvals_result.get("data") if approvals_result.get("ok") else None
    approvals = approvals_payload.get("approvals", []) if isinstance(approvals_payload, dict) else []

    platform_value, platform_label, platform_tone, platform_detail = status_text(platform_health)
    agent_value, agent_label, agent_tone, agent_detail = status_text(agent_health)
    pending_value = str(len(approvals)) if approvals_result["ok"] else "Unknown"
    pending_label = "pending" if approvals else "clear"
    pending_tone = "amber" if approvals else ("green" if approvals_result["ok"] else "red")
    pending_detail = (
        "Approvals waiting for review"
        if approvals
        else "No pending approvals returned"
        if approvals_result["ok"]
        else approvals_result.get("error") or "Approval service unavailable"
    )
    drift_value, drift_label, drift_tone, drift_detail = drift_kpi(
        st.session_state["last_drift_result"]
    )

    kpi_cols = st.columns(4)
    with kpi_cols[0]:
        kpi_card("Platform Status", platform_value, platform_label, platform_tone, platform_detail)
    with kpi_cols[1]:
        kpi_card("Agent Status", agent_value, agent_label, agent_tone, agent_detail)
    with kpi_cols[2]:
        kpi_card("Pending Approvals", pending_value, pending_label, pending_tone, pending_detail)
    with kpi_cols[3]:
        kpi_card("Last Drift Report", drift_value, drift_label, drift_tone, drift_detail)

    left, right = st.columns([2.1, 1], gap="large")

    with left:
        st.markdown('<div class="section-title">HIL Approval Inbox</div>', unsafe_allow_html=True)
        if not approvals_result["ok"]:
            st.markdown(
                f"""
                <div class="error-card">
                    <strong>Approval inbox unavailable.</strong>
                    <div class="muted">{escape(approvals_result.get("error") or "Unable to load approvals.")}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )
        elif not approvals:
            st.markdown(
                """
                <div class="empty-card">
                    <strong>No pending approvals right now.</strong>
                    <div class="muted">When the agent requests human review, approvals will appear here.</div>
                </div>
                """,
                unsafe_allow_html=True,
            )
        else:
            for approval in approvals:
                if isinstance(approval, dict):
                    render_approval_card(approval)

    with right:
        st.markdown('<div class="section-title">Operations</div>', unsafe_allow_html=True)
        st.markdown(
            """
            <div class="panel-card">
                <strong>Drift smoke check</strong>
                <div class="muted">Run the platform drift report and verify webhook delivery to the agent.</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        if st.button("Run Drift Report", key="run_drift_report", use_container_width=True):
            st.session_state["last_drift_result"] = get_json(
                f"{PLATFORM_BASE_URL}/drift/report",
                timeout=10,
            )
            st.rerun()

        last_drift_result = st.session_state["last_drift_result"]
        if last_drift_result:
            if last_drift_result.get("ok"):
                data = last_drift_result.get("data")
                report = data.get("report", {}) if isinstance(data, dict) else {}
                webhook_sent = data.get("webhook_sent") if isinstance(data, dict) else None
                st.success(f"Drift report completed. Webhook sent: {webhook_sent}.")
                st.caption(f"Severity: {report.get('severity', 'unknown')}")
            else:
                st.error(f"Drift report failed: {last_drift_result.get('error')}")

        if st.button("Refresh approvals", key="refresh_approvals", use_container_width=True):
            st.session_state["last_action_message"] = {
                "tone": "success",
                "text": "Approval inbox refreshed.",
            }
            st.rerun()

        st.markdown(
            """
            <div class="panel-card">
                <strong>Queue visibility</strong>
                <div class="muted">Queue visibility will be connected after worker status endpoint is available.</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with st.expander("Raw pending approvals response"):
        st.json(approvals_result)
    with st.expander("Raw drift report response"):
        st.json(st.session_state["last_drift_result"] or {"ok": False, "data": None, "error": "No drift report run yet."})
    with st.expander("Health check details"):
        st.json({"platform": platform_health, "agent": agent_health})


render_dashboard()
