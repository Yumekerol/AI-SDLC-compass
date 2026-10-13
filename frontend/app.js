/**
 * AI-SDLC Compass — Frontend Client Application
 * Handles the 4-step diagnostic state machine and API communication.
 */

const API_BASE = window.location.origin.includes(":8000") 
    ? `${window.location.origin}/api/v1` 
    : "http://localhost:8000/api/v1";

let currentSessionId = null;
let currentSignals = null;
let currentReport = null;

// DOM Elements
const stepNavs = [1, 2, 3, 4].map(n => document.getElementById(`step-nav-${n}`));
const stepViews = [1, 2, 3, 4].map(n => document.getElementById(`step-${n}`));
const connectForm = document.getElementById("connect-form");
const btnScan = document.getElementById("btn-scan");
const btnConfirmSignals = document.getElementById("btn-confirm-signals");
const btnSaveDraft = document.getElementById("btn-save-draft");
const chatForm = document.getElementById("chat-input-form");
const chatInput = document.getElementById("chat-input");
const chatMessagesContainer = document.getElementById("chat-messages-container");
const btnGenerateReport = document.getElementById("btn-generate-report");
const btnDownloadPdf = document.getElementById("btn-download-pdf");
const btnRestart = document.getElementById("btn-restart");

// Navigation State Machine
function goToStep(stepNum) {
    stepViews.forEach((view, idx) => {
        if (idx + 1 === stepNum) {
            view.classList.add("active");
        } else {
            view.classList.remove("active");
        }
    });

    stepNavs.forEach((nav, idx) => {
        const n = idx + 1;
        if (n === stepNum) {
            nav.classList.add("active");
            nav.classList.remove("completed");
        } else if (n < stepNum) {
            nav.classList.remove("active");
            nav.classList.add("completed");
        } else {
            nav.classList.remove("active", "completed");
        }
    });

    // Update lines
    for (let i = 1; i <= 3; i++) {
        const line = document.getElementById(`line-${i}`);
        if (line) {
            if (i < stepNum) {
                line.classList.add("active");
            } else {
                line.classList.remove("active");
            }
        }
    }
}

// ─── Step 1: Connect & Scan ──────────────────────────────────────────

connectForm.addEventListener("submit", async (e) => {
    e.preventDefault();
    const gitUrl = document.getElementById("git-url").value.trim();
    const accessToken = document.getElementById("access-token").value.trim() || null;
    const consentGiven = document.getElementById("consent-check").checked;

    btnScan.disabled = true;
    btnScan.querySelector("span").textContent = "Creating Session...";

    try {
        // 1. Create Session
        const createRes = await fetch(`${API_BASE}/sessions`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                source_type: "git",
                git_url: gitUrl,
                access_token: accessToken,
                consent_given: consentGiven,
            }),
        });

        if (!createRes.ok) {
            const err = await createRes.json();
            throw new Error(err.detail || "Failed to create session");
        }

        const createData = await createRes.json();
        currentSessionId = createData.session_id;

        // 2. Trigger Scan
        btnScan.querySelector("span").textContent = "Cloning & Scanning Codebase...";
        const scanRes = await fetch(`${API_BASE}/sessions/${currentSessionId}/scan`, {
            method: "POST",
        });

        if (!scanRes.ok) {
            const err = await scanRes.json();
            throw new Error(err.detail || "Failed to start scanner");
        }

        // Poll for scan completion
        await pollScanStatus(currentSessionId);

        // Load signals and move to Step 2
        await loadSignals(currentSessionId);
        goToStep(2);

    } catch (err) {
        alert(`Error: ${err.message}`);
    } finally {
        btnScan.disabled = false;
        btnScan.querySelector("span").textContent = "Scan Repository";
    }
});

async function pollScanStatus(sessionId) {
    while (true) {
        await new Promise(r => setTimeout(r, 1000));
        const res = await fetch(`${API_BASE}/sessions/${sessionId}`);
        if (!res.ok) continue;
        const data = await res.json();
        if (data.status === "awaiting_signal_review" || data.status === "scan_complete") {
            return;
        }
        if (data.status === "error") {
            throw new Error(data.error_message || "Scanner encountered an error");
        }
    }
}

// ─── Step 2: Review Signals ──────────────────────────────────────────

async function loadSignals(sessionId) {
    const res = await fetch(`${API_BASE}/sessions/${sessionId}/signals`);
    if (!res.ok) throw new Error("Could not fetch signals");

    currentSignals = await res.json();
    renderSignals(currentSignals);
}

function renderSignals(data) {
    const repo = data.repository || {};
    const scope = data.scope || {};
    const groups = data.signal_groups || {};

    document.getElementById("signals-repo-name").textContent = repo.name || "Repository";
    document.getElementById("signals-repo-branch").textContent = repo.branch || "main";
    document.getElementById("signals-scope-summary").innerHTML = `
        <span><strong>${scope.supported_code_files || 0}</strong> code files analyzed</span> • 
        <span>${scope.eligible_for_poc ? "Eligible for PoC" : "Extended Scope"}</span>
    `;

    const container = document.getElementById("signal-cards-container");
    container.innerHTML = "";

    const cardDefs = [
        {
            key: "languages",
            title: "Languages & Distribution",
            render: (g) => {
                const b = g.data?.breakdown || [];
                return b.map(l => `<div><strong>${l.language}:</strong> ${l.files} files (${l.percentage}%)</div>`).join("") || "No code files detected.";
            }
        },
        {
            key: "size_and_structure",
            title: "Size & Architecture Structure",
            render: (g) => {
                const d = g.data || {};
                return `
                    <div>Total Source Files: <strong>${d.code_files || 0}</strong></div>
                    <div>Estimated LoC: <strong>${(d.loc_estimate || 0).toLocaleString()}</strong></div>
                    <div>Distinct Modules: <strong>${d.module_estimate || 0}</strong></div>
                    <div>Avg File Size: <strong>${d.avg_file_size_loc || 0} LoC</strong></div>
                `;
            }
        },
        {
            key: "stack_and_tooling",
            title: "Frameworks & Dependencies",
            render: (g) => {
                const d = g.data || {};
                return `
                    <div>Frameworks: <strong>${(d.frameworks || []).join(", ") || "None"}</strong></div>
                    <div>Testing Libraries: <strong>${(d.testing_libraries || []).join(", ") || "None"}</strong></div>
                    <div>Linters / Formatters: <strong>${[...(d.linters||[]), ...(d.formatters||[])].join(", ") || "None"}</strong></div>
                `;
            }
        },
        {
            key: "cicd_and_operations",
            title: "CI/CD & Operational Infrastructure",
            render: (g) => {
                const d = g.data || {};
                return `
                    <div>Pipeline: <strong>${d.cicd_tool || "None detected"}</strong></div>
                    <div>Containerization: <strong>${d.has_containerization ? "Dockerfile present" : "None"}</strong></div>
                    <div>Monitoring Config: <strong>${d.has_monitoring_config ? d.monitoring_tools?.join(", ") : "None detected"}</strong></div>
                `;
            }
        },
        {
            key: "quality_indicators",
            title: "Quality Gates & Testing Signals",
            render: (g) => {
                const d = g.data || {};
                return `
                    <div>Test File Count: <strong>${d.test_file_count || 0}</strong></div>
                    <div>Test-to-Code Ratio: <strong>${d.test_to_code_file_ratio || 0}</strong></div>
                    <div>Quality Gate: <strong>${d.has_quality_gate ? "Enforced" : "None"}</strong></div>
                `;
            }
        },
        {
            key: "warnings_and_gaps",
            title: "Warnings & Missing Signals",
            render: (g) => {
                const w = g.data?.warnings || [];
                return w.length 
                    ? w.map(item => `<div style="margin-bottom: 6px;"><strong style="color: #f59e0b;">⚠ ${item.title}:</strong> ${item.description}</div>`).join("")
                    : "<div style='color: #10b981;'>✓ All expected core signals detected.</div>";
            }
        }
    ];

    cardDefs.forEach(cd => {
        const group = groups[cd.key] || {};
        const conf = group.confidence || "low";
        const badgeClass = conf === "high" ? "badge-success" : conf === "medium" ? "badge-warning" : "badge-accent";

        const card = document.createElement("div");
        card.className = "signal-card glass-panel";
        card.innerHTML = `
            <div class="signal-card-header">
                <span class="signal-card-title">${cd.title}</span>
                <span class="badge ${badgeClass}">${conf} Confidence</span>
            </div>
            <div class="signal-card-content">
                ${cd.render(group)}
            </div>
            ${group.evidence_paths?.length ? `
                <div class="signal-evidence">
                    Evidence: ${group.evidence_paths.slice(0, 3).join(", ")}
                </div>
            ` : ""}
        `;
        container.appendChild(card);
    });
}

btnConfirmSignals.addEventListener("click", async () => {
    btnConfirmSignals.disabled = true;
    try {
        await fetch(`${API_BASE}/sessions/${currentSessionId}/confirm-signals`, { method: "POST" });
        await startDiagnostic(currentSessionId);
        goToStep(3);
    } catch (err) {
        alert(err.message);
    } finally {
        btnConfirmSignals.disabled = false;
    }
});

// ─── Step 3: Team Context Conversation ───────────────────────────────

async function startDiagnostic(sessionId) {
    const res = await fetch(`${API_BASE}/sessions/${sessionId}/diagnose`, { method: "POST" });
    if (!res.ok) throw new Error("Failed to start diagnostic");
    const data = await res.json();
    renderConversation(data.initial_messages || []);
    await loadGaps(sessionId);
}

function renderConversation(messages) {
    chatMessagesContainer.innerHTML = "";
    messages.forEach(msg => appendMessageToChat(msg));
    chatMessagesContainer.scrollTop = chatMessagesContainer.scrollHeight;
}

function appendMessageToChat(msg) {
    const el = document.createElement("div");
    el.className = `chat-message ${msg.role}`;

    let headerTag = "";
    if (msg.role === "agent") {
        headerTag = `<div class="msg-agent-tag">${msg.agent_label || "Specialist Agent"}</div>`;
    } else if (msg.role === "supervisor") {
        headerTag = `<div class="msg-agent-tag" style="color: #818cf8;">Supervisor</div>`;
    }

    let questionsHtml = "";
    if (msg.questions && msg.questions.length) {
        questionsHtml = msg.questions.map(q => `
            <div style="background: rgba(0,0,0,0.25); padding: 8px 12px; border-radius: 6px; margin-top: 8px; border-left: 3px solid #38bdf8;">
                <div style="font-size: 0.85rem; font-weight: 600;">❓ ${q.text}</div>
            </div>
        `).join("");
    }

    el.innerHTML = `
        ${headerTag}
        <div>${msg.content}</div>
        ${questionsHtml}
    `;
    chatMessagesContainer.appendChild(el);
    chatMessagesContainer.scrollTop = chatMessagesContainer.scrollHeight;
}

chatForm.addEventListener("submit", async (e) => {
    e.preventDefault();
    const content = chatInput.value.trim();
    if (!content) return;

    chatInput.value = "";
    appendMessageToChat({ role: "user", content: content });

    try {
        const res = await fetch(`${API_BASE}/sessions/${currentSessionId}/conversation`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ content: content }),
        });

        if (!res.ok) throw new Error("Failed to send message");
        const data = await res.json();
        (data.new_messages || []).forEach(m => appendMessageToChat(m));
        renderAgentStatuses(data.agent_statuses || {});
        await loadGaps(currentSessionId);
    } catch (err) {
        alert(err.message);
    }
});

async function loadGaps(sessionId) {
    const res = await fetch(`${API_BASE}/sessions/${sessionId}/knowledge-gaps`);
    if (!res.ok) return;
    const data = await res.json();
    const gapsContainer = document.getElementById("unresolved-gaps-list");
    gapsContainer.innerHTML = "";

    const gaps = data.gaps || {};
    let count = 0;
    for (const [domain, dData] of Object.entries(gaps)) {
        (dData.unresolved || []).forEach(g => {
            count++;
            const div = document.createElement("div");
            div.className = "gap-item";
            div.innerHTML = `<strong>${g.field}:</strong> ${g.description}`;
            gapsContainer.appendChild(div);
        });
    }

    if (count === 0) {
        gapsContainer.innerHTML = "<div style='color: #10b981; font-size: 0.85rem;'>✓ All core knowledge gaps resolved!</div>";
    }

    // Default statuses
    renderAgentStatuses({
        "requirements_design": { status: "active", progress: 0.8 },
        "code_refactoring": { status: "active", progress: 0.7 },
        "qa_testing": { status: "active", progress: 0.6 },
        "devops_monitoring": { status: "active", progress: 0.5 },
    });
}

function renderAgentStatuses(statuses) {
    const container = document.getElementById("agent-status-list");
    container.innerHTML = "";

    const labels = {
        "requirements_design": "Requirements & Design",
        "code_refactoring": "Code & Refactoring",
        "qa_testing": "QA & Testing",
        "devops_monitoring": "DevOps & Monitoring",
    };

    for (const [key, label] of Object.entries(labels)) {
        const st = statuses[key] || { status: "idle", progress: 0 };
        const div = document.createElement("div");
        div.className = "agent-status-item";
        div.innerHTML = `
            <span>${label}</span>
            <span class="badge ${st.status === 'complete' ? 'badge-success' : 'badge-accent'}">${st.status}</span>
        `;
        container.appendChild(div);
    }
}

btnSaveDraft.addEventListener("click", async () => {
    await fetch(`${API_BASE}/sessions/${currentSessionId}/draft`, { method: "PUT" });
    alert("Diagnostic draft saved successfully.");
});

btnGenerateReport.addEventListener("click", async () => {
    btnGenerateReport.disabled = true;
    btnGenerateReport.querySelector("span").textContent = "Synthesizing Cross-Domain Report...";
    try {
        await fetch(`${API_BASE}/sessions/${currentSessionId}/continue-diagnostic`, { method: "POST" });
        await loadReport(currentSessionId);
        goToStep(4);
    } catch (err) {
        alert(err.message);
    } finally {
        btnGenerateReport.disabled = false;
        btnGenerateReport.querySelector("span").textContent = "Continue Diagnostic (Generate Report)";
    }
});

// ─── Step 4: Diagnostic Report ───────────────────────────────────────

async function loadReport(sessionId) {
    const res = await fetch(`${API_BASE}/sessions/${sessionId}/report`);
    if (!res.ok) throw new Error("Could not load report");
    currentReport = await res.json();
    renderReport(currentReport);
}

function renderReport(report) {
    const exec = report.executive_summary || {};
    const repo = report.repository || {};
    const scorecard = report.readiness_scorecard || {};
    const phased = report.phased_recommendations || {};

    document.getElementById("report-headline").textContent = exec.headline || "Diagnostic Report";
    document.getElementById("report-repo-summary").textContent = `
        ${repo.name || "Repository"} • Primary: ${(repo.languages || []).join(", ")} • ${(repo.frameworks || []).join(", ")}
    `;

    // Verdict card
    const verdictCard = document.getElementById("report-verdict-card");
    verdictCard.innerHTML = `
        <h3 style="margin-bottom: 8px; color: #ffffff;">Executive Readiness Verdict</h3>
        <p style="color: #cbd5e1; font-size: 1.05rem; margin-bottom: 16px;">${exec.summary_text || ""}</p>
        <div style="display: flex; gap: 20px; align-items: center;">
            <div style="background: rgba(0,0,0,0.3); padding: 8px 16px; border-radius: 8px;">
                Overall AI Readiness Index: <strong style="color: #38bdf8; font-size: 1.3rem;">${exec.overall_readiness_score || 0} / 10</strong>
            </div>
            <span class="badge ${exec.overall_readiness === 'high' ? 'badge-success' : 'badge-warning'}">
                ${exec.overall_readiness?.toUpperCase()} READINESS
            </span>
        </div>
    `;

    // Scorecard
    const scContainer = document.getElementById("report-scorecard-container");
    scContainer.innerHTML = "";
    for (const [key, card] of Object.entries(scorecard)) {
        const item = document.createElement("div");
        item.className = "scorecard-item";
        const score = card.readiness_score || 0;
        const color = score >= 7 ? "var(--success)" : score >= 4 ? "var(--warning)" : "var(--danger)";
        item.innerHTML = `
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
                <h4>${card.domain_label || key}</h4>
                <span style="color: ${color}; font-weight: 700; font-size: 1.1rem;">${score}/10</span>
            </div>
            <p style="color: #94a3b8; font-size: 0.85rem; margin-bottom: 8px;">${card.verdict || ""}</p>
            <div style="font-size: 0.8rem; color: #64748b;">AI Opportunity: <strong>${card.opportunity_score || 0}/10</strong></div>
        `;
        scContainer.appendChild(item);
    }

    // Phased Roadmap
    const rmContainer = document.getElementById("report-roadmap-container");
    rmContainer.innerHTML = "";
    for (const [phaseKey, phaseData] of Object.entries(phased)) {
        const phaseDiv = document.createElement("div");
        phaseDiv.className = "phase-card";

        const recsList = (phaseData.recommendations || []).map(r => `
            <div style="background: rgba(255,255,255,0.03); border-radius: 8px; padding: 12px; margin-top: 10px; border-left: 3px solid #38bdf8;">
                <div style="font-weight: 600; color: #fff;">${r.title}</div>
                <div style="color: #94a3b8; font-size: 0.85rem; margin: 4px 0;">${r.description}</div>
                <div style="display: flex; gap: 16px; font-size: 0.8rem; color: #64748b;">
                    <span>Effort: <strong style="color: #e2e8f0;">${r.effort}</strong></span>
                    <span>Impact: <strong style="color: #38bdf8;">${r.impact.toUpperCase()}</strong></span>
                    ${r.prerequisites?.length ? `<span>Prerequisites: <strong style="color: #f59e0b;">${r.prerequisites.join(", ")}</strong></span>` : ""}
                </div>
            </div>
        `).join("");

        phaseDiv.innerHTML = `
            <h4>${phaseData.phase_label}</h4>
            <p style="color: #64748b; font-size: 0.85rem;">${phaseData.phase_description} • Effort: ${phaseData.estimated_effort}</p>
            ${recsList}
        `;
        rmContainer.appendChild(phaseDiv);
    }
}

btnDownloadPdf.addEventListener("click", () => {
    if (currentSessionId) {
        window.open(`${API_BASE}/sessions/${currentSessionId}/report/pdf`, "_blank");
    }
});

btnRestart.addEventListener("click", () => {
    currentSessionId = null;
    currentSignals = null;
    currentReport = null;
    goToStep(1);
});
