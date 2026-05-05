# dashboard/app.py
"""Streamlit dashboard — 4 sections.

Section 1 — Registry State:
- Current active model version
- Model metrics (accuracy, precision, recall, F1)
- Model history / version list

Section 2 — Open Investigations:
- Table of active/recent investigations
- Investigation status, severity, recommended action
- Click to view full investigation details

Section 3 — Queue Depth / DLQ:
- Redis queue length
- Dead-letter queue entries
- Job status (pending, processing, failed)

Section 4 — HIL Inbox:
- Pending approval actions
- Approve / Reject buttons
- Action type, investigation link, timestamp

TODO: Implement 4 st.header sections with st.empty() placeholders.
"""
