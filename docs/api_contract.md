# AI-SDLC Compass — Figma → API Contract Mapping

> Mapping every feature visible in the Figma screens to the backend API that needs to support them.

---

## Figma Features the Original Plan Was Missing

| # | Feature from Figma | Impact on Backend |
| :--- | :--- | :--- |
| 1 | **Access token for private repos** | `POST /sessions` needs an optional `access_token` field; `github_ingestion.py` must support authenticated clones |
| 2 | **Privacy & consent tracking** | Session model needs a `consent_given: bool` field; scanning must refuse to start without it |
| 3 | **Editable scanner signals** | Need `PATCH /sessions/{id}/signals` so users can correct scanner assumptions before agents run |
| 4 | **Confidence levels per signal** | Scanner output must include `confidence: "high" | "medium" | "low"` and `confidence_source` per signal group |
| 5 | **Evidence file paths** | Scanner must return the actual file paths it inspected as proof (e.g., `["api/requirements.txt", "web/package.json"]`) |
| 6 | **PoC eligibility & scope check** | Scanner must count supported vs excluded files and flag if repo exceeds PoC scope (~50 files) |
| 7 | **Save draft** | `PUT /sessions/{id}/draft` to persist mid-diagnostic progress (partial Q&A, incomplete agent runs) |
| 8 | **Unresolved knowledge gaps** | Agents must expose their current gap list as a structured field, not just questions |

All 8 are now incorporated into the API design below.

---

## Step 1: Connect Repository

**Figma Features:**
- Git URL input + optional access token
- ZIP upload alternative
- Privacy & consent checkbox (required before scanning)
- PoC scope info sidebar
- "Scan repository" button

### API Endpoints

```
POST /api/v1/sessions
```
```json
// Request
{
  "source_type": "git" | "zip",
  "git_url": "https://github.com/user/repo.git",     // if git
  "access_token": "ghp_xxx...",                        // optional, for private repos
  "consent_given": true                                // required = true
}

// Response
{
  "session_id": "uuid",
  "status": "created",
  "created_at": "2026-10-13T14:30:00Z"
}
```

```
POST /api/v1/sessions/{id}/upload
```
```
// Multipart form upload for ZIP files
// Content-Type: multipart/form-data
// Field: "archive" (file)
```

```
POST /api/v1/sessions/{id}/scan
```
```json
// Response
{
  "session_id": "uuid",
  "status": "scanning" | "scan_complete",
  "scan_started_at": "...",
  "estimated_duration_ms": 2000
}
```

---

## Step 2: Review Signals

**Figma Features:**
- Repository header: name, branch, commit hash, scan status badge
- "Eligible for PoC" / scope assessment with supported vs excluded file counts
- 6 editable signal cards, each with:
  - Confidence level badge (`High` / `Medium` / `Low`)
  - Confidence source (e.g., "File extensions", "Dependency manifests")
  - Actual data values
  - "Edit" button (user can override scanner assumptions)
  - Sample evidence file paths
- "Warnings & missing signals" card
- "Confirm & add team context" button

### API Endpoints

```
GET /api/v1/sessions/{id}/signals
```
```json
// Response — The full scanner output structured for the 6 UI cards
{
  "session_id": "uuid",
  "repository": {
    "name": "atlas-service",
    "branch": "main",
    "commit_hash": "a8f2c10",
    "source_type": "git"
  },
  "scope": {
    "eligible_for_poc": true,
    "supported_code_files": 48,
    "excluded_items": 212,
    "exclusion_rules": ["node_modules", ".git", "binaries", "generated files"],
    "scope_warnings": []                // e.g., "Repository exceeds 50-file PoC scope"
  },
  "signal_groups": {
    "languages": {
      "confidence": "high",
      "confidence_source": "File extensions",
      "data": {
        "primary_language": "Python",
        "breakdown": [
          {"language": "Python", "files": 29, "percentage": 60},
          {"language": "JavaScript", "files": 19, "percentage": 40}
        ]
      },
      "evidence_paths": ["api/app.py", "web/src/*.js", "tests/test_*.py"],
      "user_edited": false
    },
    "size_and_structure": {
      "confidence": "mixed",
      "confidence_source": "Counts + estimates",
      "data": {
        "code_files": 48,
        "loc_estimate": 6400,
        "module_estimate": 6,
        "avg_file_size_loc": 133
      },
      "evidence_paths": ["api/app/", "web/src/", "tests/"],
      "user_edited": false
    },
    "stack_and_tooling": {
      "confidence": "high",
      "confidence_source": "Dependency manifests",
      "data": {
        "frameworks": ["FastAPI", "React"],
        "testing_libraries": ["pytest", "Vitest"],
        "build_tools": ["Vite", "pip"],
        "linters": [],
        "formatters": []
      },
      "evidence_paths": ["api/requirements.txt", "web/package.json", "pyproject.toml"],
      "user_edited": false
    },
    "cicd_and_operations": {
      "confidence": "medium",
      "confidence_source": "Config inspection",
      "data": {
        "cicd_tool": "GitHub Actions",
        "cicd_description": "Build job detected",
        "has_containerization": true,
        "dockerfile_path": "Dockerfile",
        "has_documentation": true,
        "documentation_notes": "README present - No architecture document found",
        "has_test_step_in_ci": false,
        "has_deploy_step_in_ci": false
      },
      "evidence_paths": [".github/workflows/build.yml", "Dockerfile", "README.md"],
      "user_edited": false
    },
    "quality_indicators": {
      "confidence": "estimated",
      "confidence_source": "Not executed coverage",
      "data": {
        "test_to_code_file_ratio": 14.3,
        "test_file_count": 6,
        "source_file_count": 42,
        "executed_coverage": null,
        "has_quality_gate": false,
        "quality_gate_notes": "No enforced test gate detected in CI"
      },
      "evidence_paths": ["tests/", "web/src/*test.js"],
      "user_edited": false
    },
    "warnings_and_gaps": {
      "confidence": "low",
      "confidence_source": "Needs confirmation",
      "data": {
        "warnings": [
          {
            "category": "monitoring",
            "title": "Monitoring visibility is incomplete",
            "description": "No telemetry or alert configuration detected. Monitoring may live outside this repository."
          },
          {
            "category": "testing",
            "title": "Test tools present; CI test step absent",
            "description": "Confirm whether tests run in another pipeline before treating this as a delivery gap."
          }
        ]
      },
      "evidence_paths": [],
      "user_edited": false
    }
  }
}
```

```
PATCH /api/v1/sessions/{id}/signals
```
```json
// Request — User corrects specific signal groups
{
  "signal_groups": {
    "stack_and_tooling": {
      "data": {
        "frameworks": ["FastAPI", "React"],
        "testing_libraries": ["pytest", "Vitest", "Playwright"],  // user added Playwright
        "build_tools": ["Vite", "pip"],
        "linters": ["ESLint"],                                      // user added ESLint
        "formatters": ["Prettier"]                                  // user added Prettier
      }
    }
  }
}

// Response: updated signals with user_edited: true on modified groups
```

```
POST /api/v1/sessions/{id}/confirm-signals
```
```json
// Locks signals and transitions session to "team_context" phase
// Response
{
  "session_id": "uuid",
  "status": "awaiting_team_context",
  "contextual_profile_initialized": true
}
```

---

## Step 3: Team Context — Diagnostic Conversation

**Figma Features:**
- **Left panel: Chat conversation**
  - Supervisor introduces scan findings
  - Each specialist agent asks domain-specific questions in sequence
  - Team representative types free-text responses
  - Multi-turn back-and-forth
  - Message composer with send button
- **Right panel: Live diagnostic sidebar**
  - Repository metadata summary (branch, commit, languages, frameworks, scanner stats)
  - Specialist activity indicators (which agents are active/thinking)
  - Unresolved knowledge gaps (per agent domain)
  - Targeted follow-up questions (per agent domain, with "Next" button)
  - "Path to an evolving diagnostic" section
  - "Save draft" and "Continue diagnostic" buttons

### API Endpoints

```
POST /api/v1/sessions/{id}/diagnose
```
```json
// Starts the diagnostic pipeline: supervisor → agents → Q&A
// Response
{
  "session_id": "uuid",
  "status": "diagnosing",
  "initial_messages": [
    {
      "id": "msg-1",
      "role": "supervisor",
      "content": "Atlas Service has 48 code files...",
      "timestamp": "..."
    },
    {
      "id": "msg-2",
      "role": "agent",
      "agent_domain": "requirements_design",
      "agent_label": "Requirements & Design",
      "content": "Can you confirm whether acceptance criteria...",
      "questions": [
        {
          "question_id": "q-1",
          "text": "Are there any critical business paths that aren't...",
          "priority": "high",
          "tdm_field": "acceptance_criteria_exist"
        }
      ],
      "timestamp": "..."
    }
  ]
}
```

```
WebSocket /api/v1/ws/sessions/{id}/conversation
```
```json
// Client → Server: user message
{
  "type": "user_message",
  "content": "We use Jira, acceptance criteria are often verbal...",
  "responding_to_questions": ["q-1", "q-2"]    // optional: links answer to specific questions
}

// Server → Client: agent response
{
  "type": "agent_message",
  "role": "agent",
  "agent_domain": "code_refactoring",
  "agent_label": "Code & Refactoring",
  "content": "You mentioned repetitive implementation is most visible in...",
  "questions": [...],
  "timestamp": "..."
}

// Server → Client: status updates
{
  "type": "agent_status",
  "agents": {
    "requirements_design": {"status": "waiting_for_input", "progress": 0.6},
    "code_refactoring": {"status": "analyzing", "progress": 0.3},
    "qa_testing": {"status": "gathering", "progress": 0.1},
    "devops_monitoring": {"status": "idle", "progress": 0.0}
  }
}

// Server → Client: supervisor summary
{
  "type": "supervisor_message",
  "content": "The conversation has covered enough of writing...",
  "can_proceed_to_report": true
}
```

```
GET /api/v1/sessions/{id}/conversation
```
```json
// Returns full conversation history (for page reload / reconnection)
{
  "messages": [...],
  "agent_statuses": {...}
}
```

```
GET /api/v1/sessions/{id}/knowledge-gaps
```
```json
// Right sidebar: unresolved gaps and follow-up questions per agent
{
  "gaps": {
    "requirements_design": {
      "resolved": 4,
      "total": 6,
      "unresolved": [
        {
          "field": "design_review_process",
          "description": "No information about whether architecture decisions...",
          "priority": "medium"
        }
      ],
      "follow_up_questions": [
        {
          "question_id": "q-12",
          "text": "Are there any critical business paths that aren't...",
          "priority": "high"
        }
      ]
    },
    "code_refactoring": {
      "resolved": 3,
      "total": 8,
      "unresolved": [...],
      "follow_up_questions": [...]
    },
    "qa_testing": {...},
    "devops_monitoring": {...}
  }
}
```

```
PUT /api/v1/sessions/{id}/draft
```
```json
// Saves current diagnostic progress (conversation, partial TDMs)
// Response
{
  "session_id": "uuid",
  "status": "draft_saved",
  "saved_at": "..."
}
```

```
POST /api/v1/sessions/{id}/continue-diagnostic
```
```json
// Triggers final agent analysis + synthesis after conversation is complete
// Response
{
  "session_id": "uuid",
  "status": "synthesizing"
}
```

---

## Step 4: Diagnostic Report

**Figma Features:**
- Repository header with diagnostic status
- Executive summary / overview section
- **Diagnostic conversation recap** (left panel showing key exchanges)
- **Readiness & maturity sidebar:**
  - Foundational maturity assessment
  - Structural confidence level
  - Targeted follow-up questions summary
  - Pattern & risk analysis points
- **Banner: "Stabilise testing and release practices before scaling AI adoption"**
  - Overall readiness verdict with recommendation tagline
- **Impact evidence scorecard:**
  - Multiple scored categories (e.g., Requirements clarity, Code health, Test coverage, Ops maturity)
  - Each with a numerical/percentage score
- **Phase-by-phase recommendations:**
  - Phase 1: Foundational (fix hygiene first)
  - Phase 2: Quick wins (high readiness + high ROI)
  - Phase 3: Advanced (full automation)
  - Each phase has individual recommendation cards with:
    - Title and description
    - Effort estimate
    - Impact/ROI indicator
    - Risk level
    - Prerequisites
- **Disclaimer section**

### API Endpoints

```
GET /api/v1/sessions/{id}/report
```
```json
// Full diagnostic report as structured JSON (Vue app renders this)
{
  "session_id": "uuid",
  "generated_at": "...",
  "repository": {
    "name": "atlas-service",
    "branch": "main",
    "commit_hash": "a8f2c10",
    "languages": ["Python", "JavaScript"],
    "frameworks": ["FastAPI", "React"]
  },

  "executive_summary": {
    "headline": "Stabilise testing and release practices before scaling AI adoption",
    "overall_readiness": "medium",
    "overall_readiness_score": 5.2,
    "summary_text": "Atlas Service has a solid Python/FastAPI foundation but critical gaps in test coverage and deployment automation create risk..."
  },

  "readiness_scorecard": {
    "spec_hygiene": {
      "domain": "Requirements & Design",
      "readiness_score": 6,
      "opportunity_score": 8,
      "readiness_label": "Medium",
      "verdict": "API contracts partially documented; acceptance criteria inconsistent"
    },
    "code_hygiene": {
      "domain": "Code & Refactoring",
      "readiness_score": 7,
      "opportunity_score": 9,
      "readiness_label": "Medium-High",
      "verdict": "Linter present but not enforced in CI; complexity hotspots in /services/"
    },
    "harness_hygiene": {
      "domain": "QA & Testing",
      "readiness_score": 4,
      "opportunity_score": 10,
      "readiness_label": "Low",
      "verdict": "Test runner exists but coverage is illusory — only utils tested"
    },
    "ops_hygiene": {
      "domain": "DevOps & Monitoring",
      "readiness_score": 3,
      "opportunity_score": 7,
      "readiness_label": "Critical",
      "verdict": "Manual deployment with no rollback; unstructured logging"
    }
  },

  "knowledge_gaps_summary": {
    "total_resolved": 18,
    "total_asked": 22,
    "unresolved_gaps": [
      {
        "domain": "devops_monitoring",
        "field": "downtime_history",
        "description": "No information about recent outages or root causes"
      }
    ]
  },

  "phased_recommendations": {
    "phase_1_foundation": {
      "phase_label": "Phase 1: Stabilise before scaling",
      "phase_description": "Fix structural hygiene gaps that would make AI adoption risky",
      "estimated_effort": "1-2 sprints",
      "recommendations": [
        {
          "id": "rec-1",
          "title": "Enforce linter and formatter in CI pipeline",
          "domain": "code_refactoring",
          "description": "Add ESLint + Prettier check as a required CI gate...",
          "effort": "Small (1-2 days)",
          "impact": "high",
          "risk_level": "low",
          "prerequisites": [],
          "ai_relevance": "Ensures AI-generated code matches team style conventions"
        },
        {
          "id": "rec-2",
          "title": "Add integration tests for core API route handlers",
          "domain": "qa_testing",
          "description": "The 8 route handlers in /routes/ handle user data but have zero test coverage...",
          "effort": "Medium (1 sprint)",
          "impact": "critical",
          "risk_level": "high",
          "prerequisites": [],
          "ai_relevance": "Creates the safety net needed to validate AI-generated code"
        },
        {
          "id": "rec-3",
          "title": "Implement CI/CD pipeline with staging environment",
          "domain": "devops_monitoring",
          "description": "Manual SSH deployment means every release is a high-risk event...",
          "effort": "Medium (1 sprint)",
          "impact": "critical",
          "risk_level": "critical",
          "prerequisites": [],
          "ai_relevance": "Required before any automated deployment tooling"
        }
      ]
    },
    "phase_2_quick_wins": {
      "phase_label": "Phase 2: High-ROI AI adoption",
      "phase_description": "Deploy AI tools where readiness is proven and ROI is immediate",
      "estimated_effort": "2-3 sprints",
      "recommendations": [
        {
          "id": "rec-4",
          "title": "AI-powered unit test generation for /routes/",
          "domain": "qa_testing",
          "description": "Use AI test generators targeting the untested API route handlers...",
          "effort": "Small (2-3 days setup)",
          "impact": "very_high",
          "risk_level": "low",
          "prerequisites": ["rec-2"],
          "ai_relevance": "Highest ROI AI opportunity in the project"
        },
        {
          "id": "rec-5",
          "title": "AI PR summarizer and automated first-pass review",
          "domain": "code_refactoring",
          "description": "PR reviews average 3+ days. AI summarization reduces cognitive load...",
          "effort": "Small (1-2 days setup)",
          "impact": "high",
          "risk_level": "low",
          "prerequisites": ["rec-1"],
          "ai_relevance": "Cuts PR turnaround from 3+ days to <1 day"
        }
      ]
    },
    "phase_3_advanced": {
      "phase_label": "Phase 3: Advanced AI workflows",
      "phase_description": "Unlock gated opportunities once foundations are stable",
      "estimated_effort": "Ongoing",
      "recommendations": [
        {
          "id": "rec-6",
          "title": "AI log incident root-cause analyser",
          "domain": "devops_monitoring",
          "description": "Once structured logging is in place, AI can scan logs during alerts...",
          "effort": "Medium (1 sprint)",
          "impact": "high",
          "risk_level": "medium",
          "prerequisites": ["rec-3"],
          "ai_relevance": "Cuts MTTR by ~50%"
        }
      ]
    }
  },

  "conversation_highlights": [
    {
      "agent_domain": "qa_testing",
      "key_exchange": "Team confirmed tests only cover /utils/; QA engineer manually uses Postman",
      "insight_derived": "Coverage illusion — 14.3% ratio masks zero coverage on business logic"
    }
  ],

  "disclaimers": {
    "scope": "This diagnostic covers the reviewed repository scope only.",
    "accuracy": "Signals are estimates based on static analysis; executed metrics were not measured.",
    "affiliation": "Independent concept. Not affiliated with or endorsed by Accenture."
  }
}
```

```
GET /api/v1/sessions/{id}/report/pdf
```
```
// Returns the rendered PDF file
// Content-Type: application/pdf
```

---

## Complete Endpoint Summary

| Method | Path | Step | Purpose |
| :--- | :--- | :---: | :--- |
| `POST` | `/api/v1/sessions` | 1 | Create session (git URL or ZIP, with consent) |
| `POST` | `/api/v1/sessions/{id}/upload` | 1 | Upload ZIP archive |
| `POST` | `/api/v1/sessions/{id}/scan` | 1 | Trigger the Light Scanner |
| `GET` | `/api/v1/sessions/{id}/signals` | 2 | Get all scanner signals (6 card groups) |
| `PATCH` | `/api/v1/sessions/{id}/signals` | 2 | User edits/corrects signal groups |
| `POST` | `/api/v1/sessions/{id}/confirm-signals` | 2 | Lock signals, initialize contextual profile |
| `POST` | `/api/v1/sessions/{id}/diagnose` | 3 | Start diagnostic (supervisor + agents) |
| `WS` | `/api/v1/ws/sessions/{id}/conversation` | 3 | Real-time conversation with agents |
| `GET` | `/api/v1/sessions/{id}/conversation` | 3 | Fetch full conversation history |
| `GET` | `/api/v1/sessions/{id}/knowledge-gaps` | 3 | Get unresolved gaps per agent |
| `PUT` | `/api/v1/sessions/{id}/draft` | 3 | Save diagnostic progress |
| `POST` | `/api/v1/sessions/{id}/continue-diagnostic` | 3 | Finalize and trigger synthesis |
| `GET` | `/api/v1/sessions/{id}/report` | 4 | Get full report as JSON |
| `GET` | `/api/v1/sessions/{id}/report/pdf` | 4 | Download report as PDF |
| `GET` | `/api/v1/sessions/{id}` | * | Get session status and metadata |

> [!IMPORTANT]
> **Ready to build?** This API contract covers every feature visible in the Figma. Your Vue teammate can start building against these endpoints while we implement the backend in parallel. Should I proceed with coding Phase 1?
