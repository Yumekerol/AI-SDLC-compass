# AI-SDLC Compass — Agent & LLM Transition Guide
## From Mock/Heuristic to Production Agentic Reasoning

> **Purpose:** This guide walks developers through transforming the specialist agents from prototype rule-based heuristics into active generative AI agents powered by Ollama, OpenAI, Anthropic, or Google Gemini.

---

## 1. Architecture: The Agent vs. Provider Separation

The system uses a strict **decoupled abstraction layer**:

```mermaid
flowchart TD
    subgraph Specialists["Specialist Agent Layer (backend/agents/)"]
        ReqAgent["RequirementsAgent\n(Spec Hygiene)"]
        CodeAgent["CodeAgent\n(Code Hygiene)"]
        QAAgent["QAAgent\n(Harness Hygiene)"]
        DevOpsAgent["DevOpsAgent\n(Ops Hygiene)"]
    end

    subgraph Abstraction["LLM Interface (backend/llm/)"]
        BaseLLM["BaseLLMProvider\n• generate_text()\n• generate_structured(schema)"]
    end

    subgraph Providers["Concrete Providers"]
        MockP["MockLLMProvider\n(Offline Fallback)"]
        OllamaP["OllamaProvider\n(Free Local Llama 3.1)"]
        OpenAIP["OpenAIProvider\n(GPT-4o)"]
        ClaudeP["AnthropicProvider\n(Claude 3.5 Sonnet)"]
        GeminiP["GoogleProvider\n(Gemini 1.5 Pro)"]
    end

    Specialists --> BaseLLM
    BaseLLM --> MockP
    BaseLLM --> OllamaP
    BaseLLM --> OpenAIP
    BaseLLM --> ClaudeP
    BaseLLM --> GeminiP
```

- **Specialist Agents (`backend/agents/`):** Define *what* to analyze, prompt engineering, context extraction from the `ContextualProfile`, and the expected Pydantic output schemas. Agents **never** write vendor-specific API code.
- **LLM Providers (`backend/llm/`):** Handle authentication, HTTP communication, temperature, retry logic, and converting raw text into validated Pydantic models.

---

## 2. Code Walkthrough: Upgrading an Agent from Heuristic to Real LLM

Let us examine `backend/agents/code_agent.py`. Currently, it uses static heuristics for rapid zero-cost offline testing. Here is how to upgrade its `analyze()` and `insight()` methods to use active LLM reasoning.

### 2.1 Defining the Output Schemas for the LLM
Define Pydantic response models that the LLM must conform to:

```python
from pydantic import BaseModel, Field

class LLMCodeAnalysisOutput(BaseModel):
    findings: list[dict] = Field(
        description="List of evaluated dimensions with 'dimension', 'description', 'finding', 'severity'"
    )

class LLMCodeInsightOutput(BaseModel):
    readiness_score: int = Field(ge=1, le=10, description="Readiness score from 1 to 10")
    opportunity_score: int = Field(ge=1, le=10, description="Opportunity score from 1 to 10")
    readiness_label: str = Field(description="'High', 'Medium', 'Low', or 'Critical'")
    verdict: str = Field(description="One-sentence executive verdict")
    insights: list[dict] = Field(description="List of title, description, evidence, risk_level, ai_opportunity")
    recommendations: list[dict] = Field(description="List of title, description, is_foundation, effort, impact, ai_relevance")
```

### 2.2 Updating `CodeAgent.analyze()` to Prompt the LLM
Replace static analysis with `self.llm.generate_structured()`:

```python
async def analyze(self, profile: ContextualProfile, gathered_data: dict) -> list[dict]:
    # 1. Build the prompt with gathered code metrics and team context
    prompt = f"""
    You are a Principal Software Engineer assessing CODE HYGIENE for AI adoption readiness.
    
    ### REPOSITORY METRICS:
    - Primary Language: {gathered_data.get('primary_language', {}).get('value')}
    - Frameworks: {gathered_data.get('frameworks', {}).get('value')}
    - Style Enforcement (Linters/Formatters): {gathered_data.get('code_style_enforcement', {}).get('value')}
    
    ### TEAM CONTEXT:
    - Code Review Process: {gathered_data.get('code_review_process', {}).get('value')}
    - Average PR Review Time: {gathered_data.get('avg_pr_review_time', {}).get('value')}
    - Repetitive Boilerplate Pain Points: {gathered_data.get('boilerplate_pain', {}).get('value')}
    - Known Refactoring Backlog: {gathered_data.get('refactoring_backlog', {}).get('value')}
    
    ### INSTRUCTIONS:
    Evaluate these 3 dimensions:
    1. code_modularity_and_size: Can code be safely scoped into LLM context windows?
    2. style_enforcement_in_ci: Are linting and formatting gates mechanically enforced?
    3. review_throughput_bottlenecks: Does PR latency slow down team velocity?
    
    For each, return 'dimension', 'description', 'finding', and 'severity' ('critical'/'high'/'medium'/'low').
    """

    try:
        # 2. Call the active LLM provider (Ollama, OpenAI, Claude, or Gemini)
        response = await self.llm.generate_structured(
            prompt=prompt,
            response_schema=LLMCodeAnalysisOutput,
            system_prompt="You are an expert SDLC diagnostic evaluator. Always return strictly valid JSON.",
            temperature=0.2
        )
        return response.findings
    except Exception as ex:
        logger.warning(f"LLM generation failed ({ex}), falling back to heuristic analysis")
        # Graceful fallback to rule-based analysis
        return self._heuristic_analyze(profile, gathered_data)
```

### 2.3 Updating `CodeAgent.insight()` to Generate Recommendations
Use the LLM to synthesize prioritized consulting recommendations:

```python
async def insight(
    self,
    profile: ContextualProfile,
    gathered_data: dict,
    analysis_data: list[dict],
) -> dict:
    prompt = f"""
    You are a Consulting Partner delivering an AI-SDLC Readiness Assessment.
    
    ### ANALYSIS FINDINGS:
    {analysis_data}
    
    ### INSTRUCTIONS:
    Synthesize the findings and return:
    1. readiness_score (1-10): How prepared is this codebase to safely adopt AI coding assistants?
    2. opportunity_score (1-10): Potential velocity ROI from AI code tools.
    3. readiness_label: 'High' (>=8), 'Medium' (>=5), 'Low' (>=3), 'Critical' (<3).
    4. verdict: One-sentence executive assessment.
    5. insights: 2 deep observations citing evidence.
    6. recommendations: 2-3 specific recommendations. Mark 'is_foundation=True' if it is a prerequisite hygiene fix (like adding linters) before adopting AI tools.
    """

    try:
        response = await self.llm.generate_structured(
            prompt=prompt,
            response_schema=LLMCodeInsightOutput,
            system_prompt="You are an enterprise AI adoption consultant. Focus on actionable ROI and safety guardrails.",
            temperature=0.3
        )
        return response.model_dump()
    except Exception as ex:
        logger.warning(f"LLM insight generation failed ({ex}), using heuristic insight")
        return self._heuristic_insight(profile, gathered_data, analysis_data)
```

---

## 3. Provider Configuration & Zero-Code Switching

All providers are already implemented in `backend/llm/`. You switch providers purely through environment variables in `.env`.

### Provider 1: Local Ollama (Free, Zero API Cost)
Best for: Local development, offline demos, zero-budget PoCs.

1. Install Ollama: [ollama.com](https://ollama.com)
2. Pull a structured-output capable model:
   ```bash
   ollama pull llama3.1
   # OR
   ollama pull mistral
   ```
3. Set your `.env`:
   ```env
   LLM_PROVIDER=ollama
   LLM_MODEL=llama3.1
   OLLAMA_HOST=http://localhost:11434
   ```

### Provider 2: OpenAI (GPT-4o)
Best for: Highest structured output reliability and speed.

1. Get an API key from [platform.openai.com](https://platform.openai.com).
2. Set your `.env`:
   ```env
   LLM_PROVIDER=openai
   OPENAI_API_KEY=sk-proj-xxxxxxxxxxxxxxxxxxxxxxxx
   OPENAI_MODEL=gpt-4o-mini
   # or gpt-4o
   ```

### Provider 3: Anthropic Claude (Claude 3.5 Sonnet)
Best for: Deepest code reasoning and nuanced architectural insights.

1. Get an API key from [console.anthropic.com](https://console.anthropic.com).
2. Set your `.env`:
   ```env
   LLM_PROVIDER=anthropic
   ANTHROPIC_API_KEY=sk-ant-xxxxxxxxxxxxxxxxxxxxxxxx
   ANTHROPIC_MODEL=claude-3-5-sonnet-20241022
   ```

### Provider 4: Google Gemini (Gemini 1.5 Pro)
Best for: Large context window analysis (ingesting entire architecture docs).

1. Get an API key from [aistudio.google.com](https://aistudio.google.com) or GCP Vertex AI.
2. Set your `.env`:
   ```env
   LLM_PROVIDER=google
   GOOGLE_API_KEY=AIzaSyxxxxxxxxxxxxxxxxxxxxxxx
   GOOGLE_MODEL=gemini-1.5-pro
   ```

### Provider 5: Mock Provider (Built-in Offline Fallback)
If no key is present and Ollama is not running, the system automatically falls back to `MockLLMProvider`, guaranteeing that unit tests and CI pipelines never crash.

---

## 4. How the Providers Enforce Structured Output Under the Hood

Each provider file in `backend/llm/` implements schema validation differently based on the provider API capabilities:

| Provider | File | Mechanism Used |
| :--- | :--- | :--- |
| **Ollama** | `backend/llm/ollama_provider.py` | Uses Ollama's native `format="json"` API flag combined with the Pydantic JSON schema injected into the prompt. |
| **OpenAI** | `backend/llm/openai_provider.py` | Uses OpenAI's `response_format={"type": "json_object"}` and validates output with `response_schema.model_validate()`. |
| **Anthropic** | `backend/llm/anthropic_provider.py` | Injects the schema as a strict system prompt constraint and extracts JSON using regex fallback. |
| **Google** | `backend/llm/google_provider.py` | Passes system instruction requiring JSON conformance and parses the response parts. |

---

## 5. Testing Your Agent with Real LLMs

You can test any provider from the terminal in one command:

```bash
# Test with Ollama
py -c "
import asyncio
from backend.llm import get_llm_provider
from backend.models.tdm_code import CodeGatherFields

async def test():
    llm = get_llm_provider()
    print('Testing provider:', llm.__class__.__name__)
    res = await llm.generate_text('Explain why test harnesses are crucial for AI coding assistants in 2 sentences.')
    print('Response:\n', res)

asyncio.run(test())
"
```

---

## 6. Summary: The Step-by-Step Transition Plan

1. **Step 1 (Today):** Use the working prototype with Mock / Ollama locally for frontend development.
2. **Step 2 (When API Keys Arrive):** Add `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, or `GOOGLE_API_KEY` to `.env`.
3. **Step 3 (Upgrade Prompts):** Update `requirements_agent.py`, `code_agent.py`, `qa_agent.py`, and `devops_agent.py` to call `self.llm.generate_structured()` using the pattern shown in Section 2 above.
4. **Step 4 (Validation):** Run `py tests/test_api.py` to confirm the 12 lifecycle stages still pass with real LLM generation.
