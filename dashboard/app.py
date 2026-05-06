"""Streamlit command-center dashboard for Drift Triage Co-Pilot."""

from __future__ import annotations

import os
from typing import Any

import requests
import streamlit as st


st.set_page_config(
    page_title="Drift Triage Co-Pilot",
    page_icon="🛰️",
    layout="wide",
)


AGENT_BASE_URL = os.getenv("AGENT_BASE_URL", "http://localhost:8001").rstrip("/")
PLATFORM_BASE_URL = os.getenv("PLATFORM_BASE_URL", "http://localhost:8000").rstrip("/")


def get_json(url: str, timeout: int = 5) -> dict[str, Any]:
    try:
        response = requests.get(url, timeout=timeout)
    except requests.Timeout:
        return {"ok": False, "status_code": None, "data": None, "error": "Request timed out."}
    except requests.RequestException as exc:
        return {"ok": False, "status_code": None, "data": None, "error": str(exc)}

    try:
        data = response.json()
    except ValueError:
        data = None
        error = "Service returned a non-JSON response."
    else:
        error = None

    if not response.ok:
        return {
            "ok": False,
            "status_code": response.status_code,
            "data": data,
            "error": error or f"HTTP {response.status_code}",
        }
    return {"ok": True, "status_code": response.status_code, "data": data, "error": error}


def post_json(url: str, payload: dict[str, Any], timeout: int = 5) -> dict[str, Any]:
    try:
        response = requests.post(url, json=payload, timeout=timeout)
    except requests.Timeout:
        return {"ok": False, "status_code": None, "data": None, "error": "Request timed out."}
    except requests.RequestException as exc:
        return {"ok": False, "status_code": None, "data": None, "error": str(exc)}

    try:
        data = response.json()
    except ValueError:
        data = None
        error = "Service returned a non-JSON response."
    else:
        error = None

    if not response.ok:
        return {
            "ok": False,
            "status_code": response.status_code,
            "data": data,
            "error": error or f"HTTP {response.status_code}",
        }
    return {"ok": True, "status_code": response.status_code, "data": data, "error": error}


def check_service_health(base_url: str) -> dict[str, Any]:
    return get_json(f"{base_url}/health", timeout=3)


def status_chip(label: str, kind: str) -> str:
    return f'<span class="chip chip-{kind}">{label}</span>'


def as_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def extract_pending_approvals(result: dict[str, Any]) -> list[dict[str, Any]]:
    data = result.get("data")
    if isinstance(data, dict):
        return [item for item in as_list(data.get("approvals")) if isinstance(item, dict)]
    return []


def drift_summary(result: dict[str, Any] | None) -> tuple[str, str]:
    if not result:
        return "Not run", "warning"
    if not result.get("ok"):
        return "Failed", "failed"
    data = result.get("data") if isinstance(result.get("data"), dict) else {}
    webhook_sent = data.get("webhook_sent")
    if webhook_sent is True:
        return "Webhook sent", "success"
    if webhook_sent is False:
        return "Webhook failed", "failed"
    return "Completed", "success"


def queue_summary(result: dict[str, Any]) -> tuple[str, str, str]:
    if not result.get("ok"):
        return "Unavailable", "offline", result.get("error") or "Queue status unavailable."
    data = result.get("data") if isinstance(result.get("data"), dict) else {}
    if not data.get("redis_connected"):
        return "Redis offline", "offline", str(data.get("worker_note", "Worker cannot consume jobs."))
    dlq_length = data.get("dlq_length")
    if isinstance(dlq_length, int) and dlq_length > 0:
        return f"DLQ {dlq_length}", "warning", str(data.get("worker_note", "Worker is running with DLQ backlog."))
    queue_length = data.get("queue_length")
    return f"Queue {queue_length}", "healthy", str(data.get("worker_note", "Worker is polling normally."))


def registry_summary(result: dict[str, Any]) -> tuple[str, str, str]:
    if not result.get("ok"):
        return "Unavailable", "offline", result.get("error") or "Registry status unavailable."
    data = result.get("data") if isinstance(result.get("data"), dict) else {}
    production = data.get("production_version")
    candidate = data.get("candidate_version")
    if production:
        return f"Prod v{production}", "healthy", f"Candidate v{candidate}" if candidate else "No candidate version."
    if candidate:
        return f"Candidate v{candidate}", "warning", "No Production version yet."
    return "No versions", "warning", "Registry reachable but no aliases are set."


def render_card(title: str, value: str, chip_label: str, chip_kind: str, note: str = "") -> None:
    st.markdown(
        f"""
        <div class="kpi-card">
          <div class="kpi-title">{title}</div>
          <div class="kpi-value">{value}</div>
          <div>{status_chip(chip_label, chip_kind)}</div>
          <div class="kpi-note">{note}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_error_card(title: str, result: dict[str, Any]) -> None:
    st.markdown(
        f"""
        <div class="error-card">
          <div class="card-title">{title}</div>
          <div class="muted">The service did not respond cleanly.</div>
          <div class="error-text">{result.get("error") or "Unknown error"}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_state_panel(
    title: str,
    value: str,
    chip_label: str,
    chip_kind: str,
    details: list[tuple[str, Any]],
    note: str = "",
) -> None:
    rows = "".join(
        f'<div class="state-row"><span>{label}</span><b>{value if value not in (None, "") else "-"}</b></div>'
        for label, value in details
    )
    note_html = f'<div class="kpi-note">{note}</div>' if note else ""
    st.markdown(
        f"""
        <div class="ops-card">
          <div class="panel-topline">
            <div>
              <div class="eyebrow">{title}</div>
              <div class="panel-value">{value}</div>
            </div>
            <div>{status_chip(chip_label, chip_kind)}</div>
          </div>
          <div class="state-grid">{rows}</div>
          {note_html}
        </div>
        """,
        unsafe_allow_html=True,
    )


def approval_card(approval: dict[str, Any]) -> None:
    approval_id = str(approval.get("approval_id", "unknown"))
    action = str(approval.get("requested_action", "unknown"))
    status = str(approval.get("status", "pending"))
    target_model = approval.get("target_model_version") or "not specified"

    st.markdown(
        f"""
        <div class="approval-card">
          <div class="approval-topline">
            <div>
              <div class="eyebrow">Requested Action</div>
              <div class="approval-action">{action}</div>
            </div>
            <div>{status_chip(status, "pending" if status == "pending" else "warning")}</div>
          </div>
          <div class="approval-grid">
            <div><span>Approval</span><b>{approval_id}</b></div>
            <div><span>Investigation</span><b>{approval.get("investigation_id", "-")}</b></div>
            <div><span>Drift Event</span><b>{approval.get("drift_event_id", "-")}</b></div>
            <div><span>Target Model</span><b>{target_model}</b></div>
            <div><span>Requested By</span><b>{approval.get("requested_by", "-")}</b></div>
            <div><span>Created</span><b>{approval.get("created_at", "-")}</b></div>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    approved_by = st.text_input("Approved by", value="jad", key=f"approved_by_{approval_id}")
    reason = st.text_area(
        "Reason",
        placeholder="Optional reviewer note",
        key=f"reason_{approval_id}",
    )
    approve_col, reject_col = st.columns(2)
    with approve_col:
        if st.button("Approve", key=f"approve_{approval_id}", use_container_width=True):
            result = post_json(
                f"{AGENT_BASE_URL}/hil/{approval_id}/approve",
                {"approved_by": approved_by, "reason": reason or None},
            )
            st.session_state.last_action_message = (
                "success",
                f"Approved {approval_id}" if result["ok"] else f"Approve failed: {result['error']}",
            )
            st.rerun()
    with reject_col:
        if st.button("Reject", key=f"reject_{approval_id}", use_container_width=True):
            result = post_json(
                f"{AGENT_BASE_URL}/hil/{approval_id}/reject",
                {"approved_by": approved_by, "reason": reason or None},
            )
            st.session_state.last_action_message = (
                "success",
                f"Rejected {approval_id}" if result["ok"] else f"Reject failed: {result['error']}",
            )
            st.rerun()


st.markdown(
    """
    <style>
    .block-container { padding-top: 2rem; padding-bottom: 3rem; }
    .hero { padding: 1.4rem 1.6rem; border-radius: 24px; background:
      radial-gradient(circle at top left, rgba(39, 116, 255, .20), transparent 32%),
      linear-gradient(135deg, #0d1b2a 0%, #14213d 48%, #1d3557 100%);
      color: white; margin-bottom: 1.4rem; box-shadow: 0 22px 55px rgba(13, 27, 42, .20); }
    .hero h1 { margin: 0; font-size: 2.7rem; letter-spacing: -0.04em; }
    .hero p { margin: .4rem 0 0; color: #d8e2f0; font-size: 1.05rem; }
    .kpi-card, .approval-card, .ops-card, .error-card {
      border: 1px solid rgba(15, 23, 42, .08); border-radius: 20px; padding: 1.05rem;
      background: rgba(255,255,255,.92); box-shadow: 0 12px 30px rgba(15,23,42,.07);
      margin-bottom: .9rem; }
    .kpi-title, .eyebrow { color: #64748b; font-size: .75rem; text-transform: uppercase; letter-spacing: .10em; font-weight: 800; }
    .kpi-value { color: #0f172a; font-size: 1.65rem; font-weight: 850; letter-spacing: -.03em; margin: .35rem 0; }
    .kpi-note, .muted { color: #64748b; font-size: .86rem; margin-top: .45rem; }
    .chip { display: inline-block; padding: .28rem .65rem; border-radius: 999px; font-size: .78rem; font-weight: 800; }
    .chip-success, .chip-healthy { color: #065f46; background: #d1fae5; }
    .chip-warning, .chip-pending { color: #92400e; background: #fef3c7; }
    .chip-failed, .chip-offline { color: #991b1b; background: #fee2e2; }
    .approval-topline { display: flex; justify-content: space-between; gap: 1rem; align-items: start; }
    .approval-action { color: #0f172a; font-size: 1.35rem; font-weight: 850; margin-top: .2rem; }
    .approval-grid { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: .75rem; margin-top: 1rem; }
    .approval-grid span { display: block; color: #64748b; font-size: .78rem; }
    .approval-grid b { display: block; color: #0f172a; font-size: .9rem; overflow-wrap: anywhere; }
    .panel-topline { display: flex; justify-content: space-between; gap: 1rem; align-items: start; }
    .panel-value { color: #0f172a; font-size: 1.25rem; font-weight: 850; margin-top: .25rem; }
    .state-grid { display: grid; grid-template-columns: 1fr; gap: .55rem; margin-top: .85rem; }
    .state-row { display: flex; justify-content: space-between; gap: 1rem; padding: .55rem 0; border-top: 1px solid rgba(15,23,42,.08); }
    .state-row span { color: #64748b; font-size: .85rem; }
    .state-row b { color: #0f172a; font-size: .88rem; overflow-wrap: anywhere; text-align: right; }
    .error-card { border-color: rgba(220,38,38,.20); background: #fff7f7; }
    .error-text { color: #991b1b; margin-top: .45rem; overflow-wrap: anywhere; }
    .help-note { padding: .9rem 1rem; background: #eef6ff; color: #1e3a8a; border-radius: 16px; border: 1px solid #bfdbfe; margin-bottom: 1rem; }
    </style>
    """,
    unsafe_allow_html=True,
)


if "last_drift_result" not in st.session_state:
    st.session_state.last_drift_result = None
if "last_action_message" not in st.session_state:
    st.session_state.last_action_message = None


platform_health = check_service_health(PLATFORM_BASE_URL)
agent_health = check_service_health(AGENT_BASE_URL)
pending_result = get_json(f"{AGENT_BASE_URL}/hil/pending", timeout=5)
queue_result = get_json(f"{PLATFORM_BASE_URL}/queue/status", timeout=5)
registry_result = get_json(f"{PLATFORM_BASE_URL}/registry/status", timeout=5)
approvals = extract_pending_approvals(pending_result)
drift_label, drift_kind = drift_summary(st.session_state.last_drift_result)
queue_label, queue_kind, queue_note = queue_summary(queue_result)
registry_label, registry_kind, registry_note = registry_summary(registry_result)


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
    '<div class="help-note">Replay/retrain jobs are queued for the worker. '
    "Production-changing actions require HIL approval.</div>",
    unsafe_allow_html=True,
)

if st.session_state.last_action_message:
    level, message = st.session_state.last_action_message
    if level == "success":
        st.success(message)
    else:
        st.error(message)

kpi_cols = st.columns(4)
with kpi_cols[0]:
    render_card(
        "Platform Status",
        "Online" if platform_health["ok"] else "Offline",
        "healthy" if platform_health["ok"] else "offline",
        "healthy" if platform_health["ok"] else "offline",
        PLATFORM_BASE_URL,
    )
with kpi_cols[1]:
    render_card(
        "Agent Status",
        "Online" if agent_health["ok"] else "Offline",
        "healthy" if agent_health["ok"] else "offline",
        "healthy" if agent_health["ok"] else "offline",
        AGENT_BASE_URL,
    )
with kpi_cols[2]:
    render_card(
        "Pending Approvals",
        str(len(approvals)) if pending_result["ok"] else "Unknown",
        "pending" if approvals else ("healthy" if pending_result["ok"] else "offline"),
        "pending" if approvals else ("healthy" if pending_result["ok"] else "offline"),
        "HIL inbox",
    )
with kpi_cols[3]:
    render_card("Last Drift Report", drift_label, drift_label.lower(), drift_kind, "Platform webhook")


left, right = st.columns([1.65, 1], gap="large")

with left:
    st.subheader("HIL Approval Inbox")
    if not pending_result["ok"]:
        render_error_card("Pending approvals unavailable", pending_result)
    elif not approvals:
        st.info("No pending approvals right now.")
    else:
        for item in approvals:
            approval_card(item)

    with st.expander("Raw pending approvals response"):
        st.json(pending_result)

with right:
    st.subheader("Operations")
    st.markdown('<div class="ops-card">', unsafe_allow_html=True)
    if st.button("Run Drift Report", use_container_width=True):
        st.session_state.last_drift_result = get_json(f"{PLATFORM_BASE_URL}/drift/report", timeout=20)
        st.rerun()
    if st.button("Refresh approvals", use_container_width=True):
        st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)

    drift_result = st.session_state.last_drift_result
    if drift_result:
        if drift_result["ok"]:
            data = drift_result.get("data") if isinstance(drift_result.get("data"), dict) else {}
            render_state_panel(
                "Last Drift Report",
                "Webhook sent" if data.get("webhook_sent") is True else "Completed",
                "success" if data.get("webhook_sent") is True else ("failed" if data.get("webhook_sent") is False else "warning"),
                "success" if data.get("webhook_sent") is True else ("failed" if data.get("webhook_sent") is False else "warning"),
                [
                    ("Webhook sent", data.get("webhook_sent", "unknown")),
                    ("Severity", data.get("severity", data.get("report", {}).get("severity", "unknown"))),
                    ("Event", data.get("webhook_response", {}).get("drift_event_id") if isinstance(data.get("webhook_response"), dict) else None),
                ],
                note=str(data.get("summary") or data.get("message") or data.get("webhook_error") or ""),
            )
            summary = data.get("summary") or data.get("message") or data.get("webhook_error")
        else:
            render_error_card("Drift report failed", drift_result)

    if queue_result["ok"]:
        queue_data = queue_result.get("data") if isinstance(queue_result.get("data"), dict) else {}
        render_state_panel(
            "Queue / Worker Status",
            queue_label,
            queue_label if queue_kind == "healthy" else ("warning" if queue_kind == "warning" else "offline"),
            queue_kind,
            [
                ("Queue", queue_data.get("queue_name")),
                ("Queued jobs", queue_data.get("queue_length")),
                ("DLQ", queue_data.get("dlq_name")),
                ("DLQ size", queue_data.get("dlq_length")),
                ("Redis connected", queue_data.get("redis_connected")),
            ],
            note=queue_note,
        )
    else:
        render_error_card("Queue / Worker Status unavailable", queue_result)

    if registry_result["ok"]:
        registry_data = registry_result.get("data") if isinstance(registry_result.get("data"), dict) else {}
        render_state_panel(
            "Registry / Model Status",
            registry_label,
            "healthy" if registry_kind == "healthy" else ("warning" if registry_kind == "warning" else "offline"),
            registry_kind,
            [
                ("Registered model", registry_data.get("registered_model_name")),
                ("Candidate", registry_data.get("candidate_version")),
                ("Production", registry_data.get("production_version") or "No Production version yet"),
                ("Last promotion", registry_data.get("last_promotion")),
                ("Status", registry_data.get("status")),
            ],
            note=registry_note,
        )
    else:
        render_error_card("Registry / Model Status unavailable", registry_result)

    with st.expander("Health check details"):
        st.json({"platform": platform_health, "agent": agent_health})
    with st.expander("Raw drift report response"):
        st.json(st.session_state.last_drift_result or {})
    with st.expander("Raw queue status response"):
        st.json(queue_result)
    with st.expander("Raw registry status response"):
        st.json(registry_result)
