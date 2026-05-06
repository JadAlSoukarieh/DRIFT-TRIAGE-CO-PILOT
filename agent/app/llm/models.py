"""Pydantic models for LLM structured output.

GUIDELINES-compliant: all LLM responses parsed as typed models.
No regex parsing of raw text.
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class TriageOutput(BaseModel):
    """Structured triage summary from the LLM."""

    triage_summary: str = Field(
        description="One-paragraph ML operations triage summary of the drift alert."
    )


class CommsOutput(BaseModel):
    """Structured dashboard-safe summary from the LLM."""

    summary: str = Field(
        description="Concise dashboard-safe summary of the investigation outcome."
    )
