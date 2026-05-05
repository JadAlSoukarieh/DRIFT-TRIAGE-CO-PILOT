# agent/app/tools/dispatch_replay.py
"""Enqueue a replay job.

Replays the held-out test set through the current (or specified) model
to compute up-to-date metrics without retraining.

TODO: Implement enqueue_replay(payload: dict) -> str.
"""
