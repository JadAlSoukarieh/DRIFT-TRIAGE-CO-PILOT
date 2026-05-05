# agent/app/services/manage_checkpoints.py
"""LangGraph checkpoint persistence via Postgres.

Uses langgraph.checkpoint.postgres.AsyncPostgresSaver.
Initialized once at agent startup, attached to compiled graph.
Automatically saves state after each node execution.

Resuming: when the graph is invoked with the same thread_id (investigation_id),
it picks up from the last checkpoint — survives agent crashes and restarts.

TODO: Implement get_checkpointer() -> AsyncPostgresSaver.
"""
