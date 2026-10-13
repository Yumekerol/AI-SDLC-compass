"""
Question Manager

Batches, prioritizes, and maps user answers to specific TDM fields
in the ContextualProfile living document.
"""

from __future__ import annotations

import logging
from typing import Any

from ..models.contextual_profile import ContextualProfile, TeamContext
from ..models.diagnostic_session import ConversationQuestion

logger = logging.getLogger(__name__)


class QuestionManager:
    """Manages question routing and answer mapping."""

    @staticmethod
    def map_answer_to_team_context(
        team_context: TeamContext,
        tdm_field: str,
        answer: str,
    ) -> None:
        """Map user answer into the structured TeamContext model."""
        clean_ans = answer.strip()
        field_lower = tdm_field.lower()

        if field_lower == "requirements_format":
            team_context.requirements_format = clean_ans
        elif field_lower == "acceptance_criteria_exist":
            team_context.acceptance_criteria_exist = clean_ans
        elif field_lower == "code_review_process":
            team_context.code_review_process = clean_ans
        elif field_lower == "avg_pr_review_time":
            team_context.avg_pr_review_time = clean_ans
        elif field_lower == "boilerplate_pain":
            team_context.boilerplate_pain = clean_ans
        elif field_lower == "critical_untested_modules":
            team_context.critical_untested_modules = clean_ans
        elif field_lower == "test_types_present":
            team_context.test_types_present = [item.strip() for item in clean_ans.split(",")]
        elif field_lower == "deployment_method":
            team_context.deployment_method = clean_ans
        elif field_lower == "rollback_strategy":
            team_context.rollback_strategy = clean_ans
        elif field_lower == "downtime_history":
            team_context.downtime_history = clean_ans
        elif field_lower == "team_size":
            try:
                team_context.team_size = int(clean_ans)
            except ValueError:
                pass
        else:
            team_context.declared_pain_points.append(f"{tdm_field}: {clean_ans}")

    @staticmethod
    def deduplicate_and_rank_questions(
        questions: list[ConversationQuestion],
    ) -> list[ConversationQuestion]:
        """Rank questions by priority (high -> medium -> low)."""
        priority_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
        return sorted(
            questions,
            key=lambda q: priority_order.get(q.priority.lower(), 2),
        )
