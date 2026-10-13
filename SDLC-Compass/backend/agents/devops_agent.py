"""
DevOps & Monitoring Specialist Agent

Assesses OPS HYGIENE:
- Evaluates CI/CD automation, containerization, observability, and rollback mechanisms.
- Assesses whether the environment is robust enough to support automated AI deployments.
- Identifies operational tasks where AI observability reduces mean time to resolution (MTTR).
"""

from __future__ import annotations

import logging
from uuid import uuid4

from ..llm.base_provider import BaseLLMProvider
from ..models.contextual_profile import ContextualProfile
from ..models.diagnostic_session import ConversationQuestion
from ..models.tdm_devops import DevOpsGatherFields
from ..models.tdm_requirements import RequirementsInsight, RequirementsRecommendation, TDMFieldStatus
from .base_agent import BaseSpecialistAgent

logger = logging.getLogger(__name__)


class DevOpsAgent(BaseSpecialistAgent):
    """Specialist agent for DevOps & Monitoring (Ops Hygiene)."""

    def __init__(self, llm_provider: BaseLLMProvider):
        super().__init__(
            llm_provider=llm_provider,
            domain_name="devops_monitoring",
            domain_label="DevOps & Monitoring",
        )

    async def gather(
        self, profile: ContextualProfile
    ) -> tuple[dict, list[ConversationQuestion], list[dict]]:
        tc = profile.team_context
        scanner_signals = profile.scanner_signals or {}
        cicd_data = scanner_signals.get("cicd_and_operations", {}).get("data", {})

        gather = DevOpsGatherFields()
        questions: list[ConversationQuestion] = []
        gaps: list[dict] = []

        # 1. Pipeline
        cicd_tool = cicd_data.get("cicd_tool")
        if cicd_tool:
            gather.has_pipeline = TDMFieldStatus(
                value=cicd_tool,
                source="scanner",
                confidence="high",
                filled=True,
            )
        else:
            gather.has_pipeline = TDMFieldStatus(
                value=None, source="scanner", confidence="low", filled=False
            )
            gaps.append({
                "field": "has_pipeline",
                "description": "No automated CI/CD pipeline detected in repository.",
                "priority": "critical",
            })

        # 2. Containerization
        has_docker = cicd_data.get("has_containerization", False)
        gather.has_dockerfile = TDMFieldStatus(
            value="Dockerfile present" if has_docker else None,
            source="scanner",
            confidence="high",
            filled=has_docker,
        )
        if not has_docker:
            gaps.append({
                "field": "has_dockerfile",
                "description": "Containerization / Docker configurations missing.",
                "priority": "high",
            })

        # 3. Deployment method
        if tc.deployment_method:
            gather.deployment_method = TDMFieldStatus(
                value=tc.deployment_method,
                source="user_qa",
                confidence="high",
                filled=True,
            )
        else:
            q = ConversationQuestion(
                question_id=f"q-{uuid4().hex[:6]}",
                text="How is your application deployed to staging and production environments (e.g. automated via CI/CD, container registry push, or manual server scripts)?",
                priority="high",
                tdm_field="deployment_method",
            )
            questions.append(q)
            gaps.append({
                "field": "deployment_method",
                "description": "Deployment mechanics and release process are unconfirmed.",
                "priority": "high",
            })

        # 4. Rollback strategy
        if tc.rollback_strategy:
            gather.rollback_strategy = TDMFieldStatus(
                value=tc.rollback_strategy,
                source="user_qa",
                confidence="high",
                filled=True,
            )
        else:
            q = ConversationQuestion(
                question_id=f"q-{uuid4().hex[:6]}",
                text="If a production release breaks, how does the team rollback (e.g. single-click automated rollback, git revert PR, or manual database/server restoration)?",
                priority="medium",
                tdm_field="rollback_strategy",
            )
            questions.append(q)
            gaps.append({
                "field": "rollback_strategy",
                "description": "Rollback capabilities in the event of flawed AI deployments are unknown.",
                "priority": "medium",
            })

        # 5. Monitoring tools
        mon_tools = cicd_data.get("monitoring_tools", [])
        if tc.logging_strategy:
            mon_tools.append(tc.logging_strategy)
        if mon_tools:
            gather.monitoring_tools = TDMFieldStatus(
                value=", ".join(mon_tools),
                source="mixed",
                confidence="high",
                filled=True,
            )
        else:
            gather.monitoring_tools = TDMFieldStatus(
                value=None, source="scanner", confidence="low", filled=False
            )
            gaps.append({
                "field": "monitoring_tools",
                "description": "Telemetry, APM, and log monitoring systems are unverified.",
                "priority": "high",
            })

        # 6. Downtime history
        if tc.downtime_history:
            gather.downtime_history = TDMFieldStatus(
                value=tc.downtime_history,
                source="user_qa",
                confidence="high",
                filled=True,
            )

        return gather.model_dump(), questions, gaps

    async def analyze(
        self, profile: ContextualProfile, gathered_data: dict
    ) -> list[dict]:
        has_pipe = gathered_data.get("has_pipeline", {}).get("filled", False)
        has_dock = gathered_data.get("has_dockerfile", {}).get("filled", False)

        analysis = [
            {
                "dimension": "deployment_automation_safety",
                "description": "Is release execution automated, reproducible, and verifiable?",
                "finding": "Automated deployments with canary or blue-green verification are required before considering autonomous agent commits." if not has_pipe else "CI/CD foundation exists; requires automated rollback gates.",
                "severity": "critical" if not has_pipe else "medium",
            },
            {
                "dimension": "observability_and_telemetry_gap",
                "description": "Can automated agents detect regressions post-deploy?",
                "finding": "Telemetry must be structured with distributed tracing and error alerting so AI agents can triage incidents.",
                "severity": "high",
            },
            {
                "dimension": "infrastructure_as_code_standardization",
                "description": "Are environment definitions declarative and reproducible?",
                "finding": "Environment definitions require containerization to spin up preview environments on pull requests.",
                "severity": "high" if not has_dock else "low",
            },
        ]
        return analysis

    async def insight(
        self,
        profile: ContextualProfile,
        gathered_data: dict,
        analysis_data: list[dict],
    ) -> dict:
        has_pipe = gathered_data.get("has_pipeline", {}).get("filled", False)
        has_dock = gathered_data.get("has_dockerfile", {}).get("filled", False)

        readiness = 3
        if has_pipe:
            readiness += 3
        if has_dock:
            readiness += 2

        opportunity = 7  # Good opportunity in CI/CD pipeline generation and AI incident root cause analysis

        label = "Critical" if readiness <= 3 else "Low" if readiness <= 5 else "Medium" if readiness <= 7 else "High"

        insights = [
            RequirementsInsight(
                title="Automated deployment pipelines are a prerequisite for agentic loops",
                description="Without reproducible CI/CD pipelines, increasing development velocity with AI creates operational deployment bottlenecks and outages.",
                evidence="Deployment relies on manual steps or lacks automated staging validation gates.",
                risk_level="critical",
                ai_opportunity="medium",
            ),
            RequirementsInsight(
                title="AI opportunity in automated CI pipeline and Dockerfile authoring",
                description="AI tools can generate complete GitHub Actions workflows, multi-stage Dockerfiles, and staging compose environments in minutes.",
                evidence="Standard framework stack enables rapid turnkey DevOps templating.",
                risk_level="low",
                ai_opportunity="high",
            ),
        ]

        recommendations = [
            RequirementsRecommendation(
                title="Containerize application and define staging environment in CI/CD",
                description="Implement multi-stage Docker build and configure automated pipeline deployment to an isolated staging environment.",
                is_foundation=True,
                effort="Medium (1 sprint)",
                impact="critical",
                ai_relevance="Enables automated PR preview environments where AI-generated code changes can be dynamically validated.",
            ),
            RequirementsRecommendation(
                title="Implement Structured Logging and APM Monitoring Gates",
                description="Configure OpenTelemetry / Sentry error tracking with automated alerts on regression spikes post-deployment.",
                is_foundation=True,
                effort="Small (1-2 days)",
                impact="high",
                ai_relevance="Gives AI agents and engineers actionable telemetry for incident root cause analysis.",
            ),
            RequirementsRecommendation(
                title="Adopt AI Incident Triage and Log Analyzer",
                description="Deploy an AI incident responder that parses stack traces, queries recent commits, and suggests immediate mitigation rollbacks.",
                is_foundation=False,
                effort="Medium (1 sprint)",
                impact="high",
                ai_relevance="Dramatically reduces mean time to resolution (MTTR) during outages.",
            ),
        ]

        return {
            "readiness_score": readiness,
            "opportunity_score": opportunity,
            "readiness_label": label,
            "verdict": "Deployments require containerized CI/CD automation before autonomous AI delivery workflows can be enabled safely.",
            "insights": [i.model_dump() for i in insights],
            "recommendations": [r.model_dump() for r in recommendations],
            "gather_complete": True,
            "analysis_complete": True,
            "insight_complete": True,
        }
