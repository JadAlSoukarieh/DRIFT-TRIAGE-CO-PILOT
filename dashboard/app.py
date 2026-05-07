"""Streamlit command-center dashboard for Drift Triage Co-Pilot."""

from __future__ import annotations

import os
from datetime import UTC, datetime
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
PREDICTION_WINDOW_SIZE = 50
SAMPLE_PREDICTION_COUNT = 60


SAMPLE_PREDICT_PAYLOAD = {
    "age": 40,
    "job": "admin.",
    "marital": "married",
    "education": "university.degree",
    "default": "no",
    "housing": "yes",
    "loan": "no",
    "contact": "cellular",
    "month": "may",
    "day_of_week": "mon",
    "campaign": 1,
    "pdays": 999,
    "previous": 0,
    "poutcome": "nonexistent",
    "emp_var_rate": 1.1,
    "cons_price_idx": 93.994,
    "cons_conf_idx": -36.4,
    "euribor3m": 4.857,
    "nr_employed": 5191,
}


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


def classify_webhook_status(drift_response: dict[str, Any] | None) -> tuple[str, str]:
    if not drift_response:
        return "not_run", "neutral"
    if not drift_response.get("ok"):
        return "failed", "error"
    data = drift_response.get("data") if isinstance(drift_response.get("data"), dict) else {}
    webhook_sent = data.get("webhook_sent")
    webhook_error = str(data.get("webhook_error") or "").lower()
    if webhook_sent is True:
        return "sent", "success"
    if "suppressed" in webhook_error or "severity unchanged" in webhook_error:
        return "suppressed", "warning"
    if "insufficient data" in webhook_error:
        return "waiting_for_data", "warning"
    if webhook_sent is False and webhook_error:
        return "failed", "error"
    return "not_sent", "neutral"


def drift_summary(result: dict[str, Any] | None) -> tuple[str, str]:
    return classify_webhook_status(result)


def build_demo_alert(severity: str, event_id: str) -> dict[str, Any]:
    numeric_drift = []
    output_drift = {
        "psi": 0.01,
        "positive_rate_reference": 0.11,
        "positive_rate_current": 0.11,
        "severity": "stable",
    }
    if severity == "moderate":
        numeric_drift = [{"feature": "euribor3m", "psi": 0.18, "severity": "moderate"}]
        output_drift = {
            "psi": 0.16,
            "positive_rate_reference": 0.11,
            "positive_rate_current": 0.18,
            "severity": "moderate",
        }
    elif severity == "critical":
        numeric_drift = [{"feature": "euribor3m", "psi": 0.35, "severity": "critical"}]
        output_drift = {
            "psi": 0.22,
            "positive_rate_reference": 0.11,
            "positive_rate_current": 0.27,
            "severity": "critical",
        }
    return {
        "schema_version": "v1",
        "event_id": event_id,
        "created_at": "2026-05-07T12:00:00Z",
        "model_name": "bank_marketing_pipeline",
        "model_version": "1",
        "model_alias": "candidate",
        "severity": severity,
        "window": {
            "size": 200,
            "start": "2026-05-07T11:00:00Z",
            "end": "2026-05-07T12:00:00Z",
        },
        "numeric_drift": numeric_drift,
        "categorical_drift": [],
        "output_drift": output_drift,
    }


def send_demo_alert(severity: str) -> None:
    suffix = datetime.now(UTC).strftime("%Y%m%d%H%M%S")
    payload = build_demo_alert(severity, f"dashboard-demo-{severity}-{suffix}")
    result = post_json(f"{AGENT_BASE_URL}/webhook/drift", payload, timeout=15)
    st.session_state.last_demo_alert_result = result
    if result["ok"]:
        st.session_state.last_action_message = ("success", f"Sent {severity} demo alert.")
    else:
        st.session_state.last_action_message = ("error", f"Demo alert failed: {result['error']}")
    st.rerun()


def generate_sample_predictions(count: int = SAMPLE_PREDICTION_COUNT) -> dict[str, Any]:
    successes = 0
    failures: list[dict[str, Any]] = []
    last_response: dict[str, Any] | None = None
    progress = st.progress(0, text="Generating sample predictions...")

    for index in range(count):
        payload = dict(SAMPLE_PREDICT_PAYLOAD)
        payload["campaign"] = 1 + (index % 3)
        payload["age"] = 35 + (index % 16)
        payload["euribor3m"] = 4.5 + ((index % 8) * 0.05)
        result = post_json(f"{PLATFORM_BASE_URL}/predict/", payload, timeout=10)
        last_response = result
        if result["ok"]:
            successes += 1
        else:
            failures.append(
                {
                    "index": index + 1,
                    "error": result.get("error"),
                    "status_code": result.get("status_code"),
                }
            )
            break
        progress.progress((index + 1) / count, text=f"Generated {index + 1}/{count} sample predictions")

    progress.empty()
    return {
        "ok": not failures,
        "requested": count,
        "successful": successes,
        "failed": len(failures),
        "ready": successes >= PREDICTION_WINDOW_SIZE,
        "window_size": PREDICTION_WINDOW_SIZE,
        "last_response": last_response,
        "errors": failures,
    }


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
    .chip-neutral { color: #334155; background: #e2e8f0; }
    .chip-error { color: #991b1b; background: #fee2e2; }
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
if "last_demo_alert_result" not in st.session_state:
    st.session_state.last_demo_alert_result = None
if "sample_predictions_result" not in st.session_state:
    st.session_state.sample_predictions_result = None


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
    "Only Production-changing actions like rollback or promotion require HIL approval.</div>",
    unsafe_allow_html=True,
)

st.info(
    "Why can Real Drift say Waiting for data while Demo Alert queued a job? "
    "Real Drift Report uses accumulated predictions and may suppress webhooks. "
    "Demo Alert sends a synthetic drift event directly to the agent to demonstrate the workflow. "
    "Critical drift queues retraining as a candidate model; it does not ask for approval because Production is unchanged."
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
    render_card("Real Drift Report", drift_label, drift_label, drift_kind, "Platform history monitor")


left, right = st.columns([1.65, 1], gap="large")

with left:
    st.subheader("HIL Approval Inbox")
    st.caption(
        "Approvals appear only for Production-changing actions: rollback or promote_candidate. "
        "Stable, replay_test, and retrain-candidate actions do not require approval."
    )
    if not pending_result["ok"]:
        render_error_card("Pending approvals unavailable", pending_result)
    elif not approvals:
        st.info("No pending approvals right now. Critical demo alerts queue retraining only; they do not touch Production.")
    else:
        for item in approvals:
            approval_card(item)

    with st.expander("Raw pending approvals response"):
        st.json(pending_result)

with right:
    st.subheader("Operations")

    st.markdown("**Real Drift Monitoring**")
    st.markdown('<div class="ops-card">', unsafe_allow_html=True)
    st.caption(
        "Uses /predict history. A webhook is sent only when there is enough data and severity changes."
    )
    if st.button("Generate 60 Sample Predictions", use_container_width=True):
        result = generate_sample_predictions()
        st.session_state.sample_predictions_result = result
        if result["ok"]:
            st.session_state.last_action_message = (
                "success",
                f"Generated {result['successful']} sample predictions for the real drift window.",
            )
        else:
            st.session_state.last_action_message = (
                "error",
                f"Prediction generation stopped after {result['successful']} successes.",
            )
        st.rerun()
    if st.button("Run Real Drift Report", use_container_width=True):
        st.session_state.last_drift_result = get_json(f"{PLATFORM_BASE_URL}/drift/report", timeout=20)
        st.rerun()
    if st.button("Refresh System State", use_container_width=True):
        st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("**Demo Agent Alerts**")
    st.markdown('<div class="ops-card">', unsafe_allow_html=True)
    st.caption(
        "Bypasses platform and sends synthetic drift directly to the agent. "
        "Stable resolves, moderate queues replay_test, critical queues retrain candidate. None of these change Production."
    )
    demo_col_1, demo_col_2, demo_col_3 = st.columns(3)
    with demo_col_1:
        if st.button("Send Stable Demo Alert", use_container_width=True):
            send_demo_alert("stable")
    with demo_col_2:
        if st.button("Send Moderate Demo Alert", use_container_width=True):
            send_demo_alert("moderate")
    with demo_col_3:
        if st.button("Send Critical Demo Alert (queues retrain)", use_container_width=True):
            send_demo_alert("critical")
    st.markdown("</div>", unsafe_allow_html=True)

    prediction_result = st.session_state.sample_predictions_result
    if prediction_result:
        render_state_panel(
            "Prediction Window Readiness",
            "ready" if prediction_result.get("ready") else "building",
            "ready" if prediction_result.get("ready") else "building",
            "success" if prediction_result.get("ready") else "warning",
            [
                ("Generated predictions", prediction_result.get("successful")),
                ("Required window", prediction_result.get("window_size")),
                ("Failed requests", prediction_result.get("failed")),
                ("Ready for /drift/report", prediction_result.get("ready")),
            ],
            note=(
                "The real drift monitor now has enough /predict history."
                if prediction_result.get("ready")
                else "Generate at least 50 successful predictions before expecting a real drift webhook."
            ),
        )

    drift_result = st.session_state.last_drift_result
    if drift_result:
        if drift_result["ok"]:
            data = drift_result.get("data") if isinstance(drift_result.get("data"), dict) else {}
            webhook_label, webhook_kind = classify_webhook_status(drift_result)
            report = data.get("report") if isinstance(data.get("report"), dict) else {}
            render_state_panel(
                "Real Drift Report Status",
                webhook_label,
                webhook_label,
                webhook_kind,
                [
                    (
                        "Prediction history",
                        "building"
                        if webhook_label == "waiting_for_data"
                        else ("ready" if st.session_state.sample_predictions_result else "unknown"),
                    ),
                    ("Severity", data.get("severity", report.get("severity", "unknown"))),
                    ("Webhook status", webhook_label),
                    ("Reason", data.get("webhook_error")),
                    ("Event", data.get("webhook_response", {}).get("drift_event_id") if isinstance(data.get("webhook_response"), dict) else None),
                ],
                note=str(data.get("summary") or data.get("message") or data.get("webhook_error") or ""),
            )
        else:
            render_error_card("Drift report failed", drift_result)

    demo_result = st.session_state.last_demo_alert_result
    if demo_result:
        if demo_result["ok"]:
            data = demo_result.get("data") if isinstance(demo_result.get("data"), dict) else {}
            render_state_panel(
                "Agent Demo Alert Result",
                str(data.get("severity", "unknown")).title(),
                str(data.get("recommended_action", "unknown")),
                "success" if data.get("status") in {"resolved", "queued"} else "warning",
                [
                    ("Severity", data.get("severity")),
                    ("Recommended action", data.get("recommended_action")),
                    ("Status", data.get("status")),
                    ("Queued", data.get("queued")),
                    ("Approval required", data.get("requires_approval")),
                    ("Job ID", data.get("job_id")),
                    ("Queue", data.get("queue_name")),
                    ("Dispatch error", data.get("dispatch_error")),
                ],
                note=(
                    str(data.get("summary") or "")
                    + " Critical retrain creates a candidate only; rollback/promotion would require HIL approval."
                    if data.get("recommended_action") == "retrain"
                    else str(data.get("summary") or "")
                ),
            )
        else:
            render_error_card("Demo alert failed", demo_result)

    if queue_result["ok"]:
        queue_data = queue_result.get("data") if isinstance(queue_result.get("data"), dict) else {}
        dlq_length = queue_data.get("dlq_length")
        queue_length = queue_data.get("queue_length")
        if isinstance(dlq_length, int) and dlq_length > 0:
            queue_note = (
                "DLQ contains failed/safety jobs. In this demo, rollback safety tests can intentionally go to DLQ."
            )
        elif queue_length == 0:
            queue_note = "Queue is empty. This can mean the worker consumed jobs successfully."
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
        candidate_version = registry_data.get("candidate_version")
        production_version = registry_data.get("production_version")
        registry_note_lines = []
        if candidate_version:
            registry_note_lines.append(f"Latest candidate model version: v{candidate_version}")
        if production_version is None:
            registry_note_lines.append("No Production model promoted yet. This is safe: retrain creates candidates only.")
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
            note=" ".join(registry_note_lines) or registry_note,
        )
    else:
        render_error_card("Registry / Model Status unavailable", registry_result)

    with st.expander("Health check details"):
        st.json({"platform": platform_health, "agent": agent_health})
    with st.expander("Raw drift report response"):
        st.json(st.session_state.last_drift_result or {})
    with st.expander("Raw demo alert response"):
        st.json(st.session_state.last_demo_alert_result or {})
    with st.expander("Raw queue status response"):
        st.json(queue_result)
    with st.expander("Raw registry status response"):
        st.json(registry_result)
