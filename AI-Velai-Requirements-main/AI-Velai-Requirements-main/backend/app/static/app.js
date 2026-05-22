const state = {
  companyToken: localStorage.getItem("vellai_company_token") || "",
  candidateToken: localStorage.getItem("vellai_candidate_token") || "",
  roles: [],
  jobs: [],
  selectedRole: null,
  session: {
    mode: null,
    assessmentId: null,
    mockInterviewId: null,
    questionId: null,
    totalQuestions: 0,
    currentIndex: 0,
    finished: false,
  },
  transcript: [],
};

const el = {
  sessionMessage: document.getElementById("session-message"),
  roleTitle: document.getElementById("role-title"),
  roleBadge: document.getElementById("role-badge"),
  roleDescription: document.getElementById("role-description"),
  roleAssessmentCount: document.getElementById("role-assessment-count"),
  roleMockAvailability: document.getElementById("role-mock-availability"),
  roleSkills: document.getElementById("role-skills"),
  roleList: document.getElementById("role-list"),
  questionIndex: document.getElementById("question-index"),
  questionText: document.getElementById("question-text"),
  questionCompetency: document.getElementById("question-competency"),
  questionDifficulty: document.getElementById("question-difficulty"),
  answerInput: document.getElementById("answer-input"),
  resultStatus: document.getElementById("result-status"),
  resultScore: document.getElementById("result-score"),
  resultRecommendation: document.getElementById("result-recommendation"),
  resultDetails: document.getElementById("result-details"),
  transcript: document.getElementById("transcript"),
  companyForm: document.getElementById("company-form"),
  candidateForm: document.getElementById("candidate-form"),
  jobForm: document.getElementById("job-form"),
  loadSample: document.getElementById("load-sample"),
  refreshRoles: document.getElementById("refresh-roles"),
  startAssessment: document.getElementById("start-assessment"),
  startMock: document.getElementById("start-mock"),
  finishSession: document.getElementById("finish-session"),
  submitAnswer: document.getElementById("submit-answer"),
  clearAnswer: document.getElementById("clear-answer"),
  clearTranscript: document.getElementById("clear-transcript"),
};

const SAMPLE_JOB = {
  title: "AI Engineer",
  department: "Engineering",
  location: "Chennai / Remote",
  employment_type: "Full-time",
  seniority: "Mid",
  skills: "Python, FastAPI, LLM, RAG, Evaluation, Prompting",
  simple_input:
    "Build production AI interview workflows that generate role-aware questions, evaluate candidate answers with evidence, and create a diagnostic report with learning guidance. The role needs strong Python, FastAPI, prompt design, and practical product thinking.",
};

function tokenLabel(token) {
  if (!token) {
    return "Not connected";
  }
  if (token.length <= 16) {
    return token;
  }
  return `${token.slice(0, 10)}...${token.slice(-6)}`;
}

function setSessionText(text, kind = "default") {
  if (!el.sessionMessage) return;
  el.sessionMessage.textContent = text;
  el.sessionMessage.style.color =
    kind === "error" ? "var(--danger)" : kind === "success" ? "var(--accent)" : "var(--text)";
}

function updateTokenIndicators() {
  return;
}

function setMode(mode) {
  state.session.mode = mode;
}

function resetSession({ preserveResult = false } = {}) {
  state.session.questionId = null;
  state.session.totalQuestions = 0;
  state.session.currentIndex = 0;
  state.session.finished = false;
  if (!preserveResult) {
    state.session.assessmentId = null;
    state.session.mockInterviewId = null;
    state.transcript = [];
    renderTranscript();
    renderResult(null);
  }
  renderQuestion(null);
  setMode(null);
  setSessionText("No active interview");
}

async function api(path, options = {}, token = "") {
  const headers = {
    "Content-Type": "application/json",
    ...(options.headers || {}),
  };
  if (token) {
    headers.Authorization = `Bearer ${token}`;
  }
  const response = await fetch(path, {
    ...options,
    headers,
    body: options.body ? JSON.stringify(options.body) : undefined,
  });
  const raw = await response.text();
  let payload = null;
  if (raw) {
    try {
      payload = JSON.parse(raw);
    } catch {
      payload = raw;
    }
  }
  if (!response.ok) {
    const detail =
      payload && typeof payload === "object" && "detail" in payload ? payload.detail : raw || response.statusText;
    throw new Error(detail || `Request failed with status ${response.status}`);
  }
  return payload;
}

function renderTranscript() {
  if (!state.transcript.length) {
    el.transcript.innerHTML = '<div class="muted">Transcript will appear here as you answer questions.</div>';
    return;
  }
  el.transcript.innerHTML = state.transcript
    .map((entry) => {
      const label = entry.kind === "answer" ? "Answer" : entry.kind === "feedback" ? "Feedback" : "Question";
      return `
        <article class="turn ${entry.kind}">
          <div class="turn-head">
            <strong>${label}</strong>
            <span>${entry.meta || ""}</span>
          </div>
          <div>${escapeHtml(entry.text)}</div>
        </article>
      `;
    })
    .join("");
}

function renderQuestion(question) {
  state.session.questionId = question?.id || null;
  if (!question) {
    el.questionText.textContent = "Start a session to see the first question.";
    el.questionCompetency.textContent = "Competency: -";
    el.questionDifficulty.textContent = "Difficulty: -";
    el.questionIndex.textContent = "0 / 0";
    return;
  }
  el.questionText.textContent = question.text || "Question unavailable.";
  el.questionCompetency.textContent = `Competency: ${question.competency || "-"}`;
  el.questionDifficulty.textContent = `Difficulty: ${question.difficulty || "-"}`;
  const current = state.session.currentIndex || 1;
  const total = state.session.totalQuestions || current;
  el.questionIndex.textContent = `${current} / ${total}`;
}

function renderRole(role) {
  state.selectedRole = role;
  if (!role) {
    el.roleTitle.textContent = "Select a role";
    el.roleBadge.textContent = "Waiting";
    el.roleDescription.textContent =
      "Pick a role card to see the job description, generated questions, and interview controls.";
    el.roleAssessmentCount.textContent = "0";
    el.roleMockAvailability.textContent = "Yes";
    el.roleSkills.textContent = "-";
    return;
  }
  el.roleTitle.textContent = role.title;
  el.roleBadge.textContent = role.department || role.seniority || "Role";
  el.roleDescription.textContent = role.description || "No description returned by the API.";
  el.roleAssessmentCount.textContent = String(role.assessment_question_count ?? 0);
  el.roleMockAvailability.textContent = role.mock_interview_available ? "Yes" : "No";
  el.roleSkills.textContent = (role.skills || []).join(", ") || "-";
}

function renderRoles() {
  if (!state.roles.length) {
    el.roleList.innerHTML = '<div class="muted" style="padding: 0 22px 22px;">No roles yet. Create one above.</div>';
    return;
  }
  el.roleList.innerHTML = state.roles
    .map((role) => {
      const isActive = state.selectedRole && state.selectedRole.job_id === role.job_id ? "active" : "";
      const skillPill = (role.skills || []).slice(0, 3).map((skill) => `<span class="chip">${escapeHtml(skill)}</span>`).join("");
      return `
        <article class="role-card ${isActive}" data-role-id="${role.job_id}">
          <div class="section-head" style="padding: 0;">
            <div>
              <h3>${escapeHtml(role.title)}</h3>
              <div class="meta">
                <span>${escapeHtml(role.company_name || "Independent")}</span>
                <span>${escapeHtml(role.location || "Remote")}</span>
                <span>${escapeHtml(role.seniority || "Open")}</span>
              </div>
            </div>
            <span class="badge">${role.assessment_question_count} Qs</span>
          </div>
          <div class="meta">${skillPill || "<span class='muted'>No skills listed.</span>"}</div>
        </article>
      `;
    })
    .join("");
}

function renderResult(result) {
  if (!result) {
    el.resultStatus.textContent = "No result yet";
    el.resultScore.textContent = "-";
    el.resultRecommendation.textContent = "-";
    el.resultDetails.textContent =
      "Finish an assessment or mock session to see the structured feedback here.";
    return;
  }

  el.resultStatus.textContent = result.status || "completed";
  if (result.career_score) {
    el.resultScore.textContent = `${result.career_score.combined_score.toFixed(1)} / 100`;
    el.resultRecommendation.textContent = result.career_score.recommendation || "-";
    el.resultDetails.innerHTML = `
      <div class="muted">Assessment score: ${result.career_score.assessment_score.toFixed(1)}</div>
      <div class="muted">Mock interview score: ${result.career_score.mock_interview_score.toFixed(1)}</div>
      <div class="muted">Referral eligible: ${result.career_score.referral_eligible ? "Yes" : "No"}</div>
      ${result.career_score.recommendation ? `<p style="margin-top:10px;">${escapeHtml(result.career_score.recommendation)}</p>` : ""}
      ${result.recommended_jobs?.length
        ? `<p style="margin-top:10px;">Recommended roles: ${result.recommended_jobs
            .map((job) => `${escapeHtml(job.title)} (${job.match_score.toFixed(1)})`)
            .join(", ")}</p>`
        : "<p style='margin-top:10px;'>No referral jobs were returned for this run.</p>"}
    `;
  } else {
    el.resultScore.textContent = `${(result.overall_score ?? 0).toFixed(1)} / 100`;
    el.resultRecommendation.textContent = result.recommendation || "complete";
    el.resultDetails.innerHTML = `
      ${result.summary ? `<p>${escapeHtml(result.summary)}</p>` : ""}
      ${result.strengths ? `<p style="margin-top:10px;"><strong>Strengths:</strong> ${escapeHtml(result.strengths)}</p>` : ""}
      ${result.gaps ? `<p style="margin-top:10px;"><strong>Gaps:</strong> ${escapeHtml(result.gaps)}</p>` : ""}
      ${result.next_step ? `<p style="margin-top:10px;"><strong>Next step:</strong> ${escapeHtml(result.next_step)}</p>` : ""}
      ${result.recommended_jobs?.length
        ? `<p style="margin-top:10px;">Recommended jobs: ${result.recommended_jobs
            .map((job) => `${escapeHtml(job.title)} (${job.match_score.toFixed(1)})`)
            .join(", ")}</p>`
        : ""}
    `;
  }
}

function appendTurn(kind, text, meta = "") {
  state.transcript.push({ kind, text, meta });
  renderTranscript();
}

async function loadHealth() {
  try {
    await api("/health");
    setSessionText("Backend connected", "success");
  } catch (error) {
    setSessionText(error.message, "error");
  }
}

async function loadRoles() {
  const roles = await api("/roles");
  state.roles = roles || [];
  renderRoles();
  if (!state.selectedRole && state.roles.length) {
    renderRole(state.roles[0]);
  } else if (state.selectedRole) {
    const updated = state.roles.find((role) => role.job_id === state.selectedRole.job_id);
    if (updated) {
      renderRole(updated);
    }
  }
}

async function loadJobs() {
  state.jobs = await api("/jobs");
}

async function handleAuth(form, mode) {
  const formData = new FormData(form);
  const payload = Object.fromEntries(formData.entries());
  let response;
  if (mode === "register-company") {
    response = await api("/company/register", { method: "POST", body: payload });
    state.companyToken = response.access_token;
    localStorage.setItem("vellai_company_token", state.companyToken);
    setSessionText("Company account connected", "success");
  } else if (mode === "login-company") {
    response = await api("/company/login", { method: "POST", body: payload });
    state.companyToken = response.access_token;
    localStorage.setItem("vellai_company_token", state.companyToken);
    setSessionText("Company login successful", "success");
  } else if (mode === "register-candidate") {
    response = await api("/candidate/register", { method: "POST", body: payload });
    state.candidateToken = response.access_token;
    localStorage.setItem("vellai_candidate_token", state.candidateToken);
    setSessionText("Candidate account connected", "success");
  } else if (mode === "login-candidate") {
    response = await api("/candidate/login", { method: "POST", body: payload });
    state.candidateToken = response.access_token;
    localStorage.setItem("vellai_candidate_token", state.candidateToken);
    setSessionText("Candidate login successful", "success");
  }
  updateTokenIndicators();
}

async function createJob(form) {
  if (!state.companyToken) {
    throw new Error("Connect a company account before creating a role.");
  }
  const payload = Object.fromEntries(new FormData(form).entries());
  payload.skills = payload.skills
    ? payload.skills
        .split(",")
        .map((item) => item.trim())
        .filter(Boolean)
    : [];
  const response = await api("/jobs/create", { method: "POST", body: payload }, state.companyToken);
  setSessionText(`Role created: ${response.title}`, "success");
  await refreshCollections(response.id);
}

async function refreshCollections(selectJobId = null) {
  await Promise.all([loadJobs(), loadRoles()]);
  if (selectJobId) {
    const match = state.roles.find((role) => role.job_id === selectJobId);
    if (match) {
      renderRole(match);
    }
  }
  renderRoles();
}

async function startAssessment() {
  if (!state.selectedRole) {
    throw new Error("Select a role first.");
  }
  if (!state.candidateToken) {
    throw new Error("Connect a candidate account first.");
  }
  const response = await api(
    `/roles/${state.selectedRole.job_id}/assessment/start`,
    { method: "POST", body: {} },
    state.candidateToken,
  );
  resetSession();
  state.session.mode = "assessment";
  state.session.assessmentId = response.assessment_id;
  state.session.totalQuestions = response.total_questions || 0;
  state.session.currentIndex = response.first_question ? 1 : 0;
  renderQuestion(response.first_question);
  appendTurn("question", response.first_question?.text || "No question returned", "Assessment");
  setMode("assessment");
  setSessionText(`Assessment started: ${response.assessment_id}`, "success");
}

async function startMock() {
  if (!state.selectedRole) {
    throw new Error("Select a role first.");
  }
  if (!state.candidateToken) {
    throw new Error("Connect a candidate account first.");
  }
  const response = await api(
    `/roles/${state.selectedRole.job_id}/mock-interview/start`,
    { method: "POST", body: {} },
    state.candidateToken,
  );
  resetSession();
  state.session.mode = "mock";
  state.session.mockInterviewId = response.mock_interview_id;
  state.session.totalQuestions = response.total_questions || 0;
  state.session.currentIndex = response.first_question ? 1 : 0;
  renderQuestion(response.first_question);
  appendTurn("question", response.first_question?.text || "No question returned", "Mock");
  setMode("mock");
  setSessionText(`Mock interview started: ${response.mock_interview_id}`, "success");
}

async function submitAnswer() {
  const answer = el.answerInput.value.trim();
  if (!answer) {
    throw new Error("Write an answer before submitting.");
  }
  if (!state.session.mode) {
    throw new Error("Start an assessment or mock interview first.");
  }
  const questionId = state.session.questionId || null;
  if (!questionId) {
    throw new Error("No active question is available.");
  }

  appendTurn("answer", answer, "Candidate");

  if (state.session.mode === "assessment") {
    if (!state.session.assessmentId) {
      throw new Error("Assessment session is missing.");
    }
    const response = await api(
      "/assessment/answer",
      {
        method: "POST",
        body: {
          assessment_id: state.session.assessmentId,
          question_id: questionId,
          answer_text: answer,
        },
      },
      state.candidateToken,
    );
    appendTurn("feedback", response.feedback || "No feedback returned", `Score ${response.score.toFixed(1)}`);
    if (response.needs_followup) {
      appendTurn("feedback", response.followup_reason || "A follow-up is required.", "Follow-up required");
    }
    state.session.currentIndex += 1;
    state.session.questionId = response.next_question?.id || null;
    renderQuestion(response.next_question || null);
    if (response.completed || !response.next_question) {
      setSessionText("Assessment question set completed. Finalize when ready.", "success");
    }
  } else {
    if (!state.session.mockInterviewId) {
      throw new Error("Mock interview session is missing.");
    }
    const response = await api(
      "/mock-interviews/answer",
      {
        method: "POST",
        body: {
          mock_interview_id: state.session.mockInterviewId,
          question_id: questionId,
          answer_text: answer,
        },
      },
      state.candidateToken,
    );
    appendTurn("feedback", response.feedback || "No feedback returned", `Score ${response.score.toFixed(1)}`);
    if (response.needs_followup) {
      appendTurn("feedback", response.followup_reason || "A follow-up is required.", "Follow-up required");
    }
    state.session.currentIndex += 1;
    state.session.questionId = response.next_question?.id || null;
    renderQuestion(response.next_question || null);
    if (response.completed || !response.next_question) {
      setSessionText("Mock questions completed. Finalize when the assessment is ready.", "success");
    }
  }

  el.answerInput.value = "";
}

async function finishMock() {
  if (!state.session.mockInterviewId) {
    throw new Error("Start a mock interview first.");
  }
  const result = await api(
    "/mock-interviews/finish",
    {
      method: "POST",
      body: {
        mock_interview_id: state.session.mockInterviewId,
      },
    },
    state.candidateToken,
  );
  renderResult(result);
  setSessionText("Mock interview completed", "success");
}

async function finishAssessment() {
  if (!state.session.assessmentId) {
    throw new Error("Start an assessment first.");
  }
  const result = await api(
    "/assessment/finish",
    {
      method: "POST",
      body: {
        assessment_id: state.session.assessmentId,
      },
    },
    state.candidateToken,
  );
  renderResult(result);
  setSessionText("Assessment completed", "success");
}

function selectRoleById(roleId) {
  const role = state.roles.find((item) => item.job_id === roleId);
  if (!role) {
    return;
  }
  renderRole(role);
  renderRoles();
  setSessionText(`Selected ${role.title}`, "success");
}

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}

function wireEvents() {
  el.companyForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    const action = event.submitter?.dataset.action;
    try {
      await handleAuth(event.currentTarget, action);
      await refreshCollections();
    } catch (error) {
      setSessionText(error.message, "error");
    }
  });

  el.candidateForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    const action = event.submitter?.dataset.action;
    try {
      await handleAuth(event.currentTarget, action);
      await refreshCollections();
    } catch (error) {
      setSessionText(error.message, "error");
    }
  });

  el.jobForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    try {
      await createJob(event.currentTarget);
      event.currentTarget.reset();
    } catch (error) {
      setSessionText(error.message, "error");
    }
  });

  el.loadSample.addEventListener("click", () => {
    const formData = new FormData(el.jobForm);
    Object.entries(SAMPLE_JOB).forEach(([key, value]) => {
      const input = el.jobForm.elements.namedItem(key);
      if (input) {
        input.value = value;
      }
    });
    setSessionText("Sample role text loaded into the form", "success");
  });

  el.refreshRoles.addEventListener("click", async () => {
    try {
      await refreshCollections();
      setSessionText("Roles refreshed", "success");
    } catch (error) {
      setSessionText(error.message, "error");
    }
  });

  el.roleList.addEventListener("click", async (event) => {
    const card = event.target.closest(".role-card");
    if (!card) {
      return;
    }
    selectRoleById(card.dataset.roleId);
  });

  el.startAssessment.addEventListener("click", async () => {
    try {
      await startAssessment();
    } catch (error) {
      setSessionText(error.message, "error");
    }
  });

  el.startMock.addEventListener("click", async () => {
    try {
      await startMock();
    } catch (error) {
      setSessionText(error.message, "error");
    }
  });

  el.finishSession.addEventListener("click", async () => {
    try {
      if (state.session.mode === "assessment") {
        await finishAssessment();
      } else {
        await finishMock();
      }
    } catch (error) {
      setSessionText(error.message, "error");
    }
  });

  el.submitAnswer.addEventListener("click", async () => {
    try {
      await submitAnswer();
    } catch (error) {
      setSessionText(error.message, "error");
    }
  });

  el.clearAnswer.addEventListener("click", () => {
    el.answerInput.value = "";
  });

  el.clearTranscript.addEventListener("click", () => {
    state.transcript = [];
    renderTranscript();
    resetSession({ preserveResult: true });
    setSessionText("View reset", "success");
  });
}

async function boot() {
  updateTokenIndicators();
  renderTranscript();
  setMode(null);
  renderResult(null);
  renderQuestion(null);
  wireEvents();
  await loadHealth();
  try {
    await Promise.all([loadJobs(), loadRoles()]);
    if (state.roles.length) {
      renderRole(state.roles[0]);
      renderRoles();
    }
  } catch (error) {
    setSessionText(error.message, "error");
  }
}

boot();
