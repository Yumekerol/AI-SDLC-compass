"""
Base Specialist Agent Abstraction

Implements the 3-phase cycle (Gather → Analyze → Insight) driven by
the agent's Target Diagnostic Model (TDM).
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod

from ..llm.base_provider import BaseLLMProvider
from ..models.contextual_profile import ContextualProfile
from ..models.diagnostic_session import ConversationQuestion

logger = logging.getLogger(__name__)


class BaseSpecialistAgent(ABC):
    """
    Abstract base class for the 4 SDLC specialist agents:
    - Requirements & Design (Spec Hygiene)
    - Code & Refactoring (Code Hygiene)
    - QA & Testing (Harness Hygiene)
    - DevOps & Monitoring (Ops Hygiene)
    """

    def __init__(self, llm_provider: BaseLLMProvider, domain_name: str, domain_label: str):
        self.llm = llm_provider
        self.domain_name = domain_name
        self.domain_label = domain_label

    @abstractmethod
    async def gather(
        self, profile: ContextualProfile
    ) -> tuple[dict, list[ConversationQuestion], list[dict]]:
        """
        Phase 1: GATHER
        Extract known fields from scanner signals, user overrides, and Q&A history.
        Identify unfilled knowledge gaps and produce targeted questions.

        Returns:
        - gathered_fields: dict of TDM field statuses
        - questions: list of ConversationQuestion to ask user
        - unresolved_gaps: list of structured gap descriptors for the sidebar
        """
        pass

    @abstractmethod
    async def analyze(
        self, profile: ContextualProfile, gathered_data: dict
    ) -> list[dict]:
        """
        Phase 2: ANALYZE
        Run domain reasoning across the gathered context.
        Evaluates risks, debt hotspots, and readiness blockers.

        Returns:
        - analysis_dimensions: list of dimension evaluations with findings and severities
        """
        pass

    @abstractmethod
    async def insight(
        self,
        profile: ContextualProfile,
        gathered_data: dict,
        analysis_data: list[dict],
    ) -> dict:
        """
        Phase 3: INSIGHT
        Produce final domain scorecard, structured insights, and prioritized recommendations.

        Returns:
        - domain_insight_result: dict matching the domain TDM insight schema
        """
        pass

    async def run_full_cycle(self, profile: ContextualProfile) -> dict:
        """Execute all 3 phases sequentially and return complete TDM output."""
        gathered, questions, gaps = await self.gather(profile)
        analysis = await self.analyze(profile, gathered)
        insights = await self.insight(profile, gathered, analysis)
        return {
            "domain": self.domain_name,
            "domain_label": self.domain_label,
            "gather": gathered,
            "questions": [q.model_dump() for q in questions],
            "gaps": gaps,
            "analysis": analysis,
            **insights,
        }
