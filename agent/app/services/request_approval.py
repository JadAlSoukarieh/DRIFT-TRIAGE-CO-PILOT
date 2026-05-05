# agent/app/services/request_approval.py
"""Human-in-the-Loop (HIL) approval service.

1. request_approval(investigation_id, action):
   - Write a pending approval row to Postgres (hil_approvals table)
   - Interrupt the LangGraph graph to pause execution

2. check_approval(investigation_id) -> bool:
   - Read approval status from Postgres
   - Used by dashboard to display pending approvals

The dashboard's Approve/Reject buttons call routers/hil.py which
updates the row and resumes the graph.

TODO: Implement request_approval() and check_approval().
"""
