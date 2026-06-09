async function api(path, options = {}) {
  const response = await fetch(path, {
    headers: options.body instanceof FormData ? {} : { "Content-Type": "application/json" },
    ...options,
  });
  const text = await response.text();
  const data = text ? JSON.parse(text) : {};
  if (!response.ok) {
    throw new Error(data.error || response.statusText);
  }
  return data;
}

function lines(value) {
  return String(value || "")
    .split("\n")
    .map((item) => item.trim())
    .filter(Boolean);
}

function card(html) {
  const div = document.createElement("div");
  div.className = "item";
  div.innerHTML = html;
  return div;
}

async function uploadSelectedFiles(input, targetTextarea) {
  const paths = [];
  for (const file of input.files || []) {
    const data = new FormData();
    data.append("file", file);
    const uploaded = await api("/api/files/upload", { method: "POST", body: data });
    paths.push(uploaded.path);
  }
  if (paths.length) {
    targetTextarea.value = [...lines(targetTextarea.value), ...paths].join("\n");
  }
}

async function loadRecentJobs() {
  const target = document.querySelector("#recentJobs");
  if (!target) return;
  const jobs = await api("/api/jobs");
  target.innerHTML = "";
  for (const job of jobs.slice(-8).reverse()) {
    target.appendChild(
      card(`<strong>${job.topic}</strong><span class="status ${job.status}">${job.status}</span><p class="muted">${job.thread_id}<br>${job.current_step || ""}</p><a href="/jobs/${job.job_id}">打开任务</a>`),
    );
  }
}

async function initIndex() {
  await loadRecentJobs();
  const upload = document.querySelector("#sourceUpload");
  const sourcePaths = document.querySelector("#sourcePaths");
  upload?.addEventListener("change", () => uploadSelectedFiles(upload, sourcePaths));
  document.querySelector("#jobForm")?.addEventListener("submit", async (event) => {
    event.preventDefault();
    const form = new FormData(event.target);
    const constraints = lines(form.get("constraints"));
    const payload = {
      topic: form.get("topic"),
      document_type: form.get("document_type"),
      audience: form.get("audience"),
      target_length: form.get("target_length"),
      style: form.get("style"),
      constraints,
      source_paths: lines(form.get("source_paths")),
      collection: form.get("collection") || "",
      rag: form.get("rag") === "on",
      rag_mode: form.get("rag_mode"),
      top_k: Number(form.get("top_k") || 5),
      output_format: form.get("output_format"),
      docx_template: form.get("docx_template") || "",
      thread_id: form.get("thread_id") || null,
      use_llm: form.get("use_llm") === "on",
      mode: form.get("mode"),
      max_agent_rounds: Number(form.get("max_agent_rounds") || 2),
      agent_debug: form.get("agent_debug") === "on",
      review_outline: form.get("review_outline") === "on",
      review_final: form.get("review_final") === "on",
    };
    const result = await api("/api/jobs", { method: "POST", body: JSON.stringify(payload) });
    location.href = `/jobs/${result.job_id}`;
  });
}

async function renderJob(jobId) {
  const job = await api(`/api/jobs/${jobId}`);
  document.querySelector("#jobTitle").textContent = `${job.topic} · ${job.thread_id}`;
  document.querySelector("#jobSummary").innerHTML = `<p><span class="status ${job.status}">${job.status}</span></p><p class="muted">current_step: ${job.current_step || ""}</p>`;
  const outputs = document.querySelector("#jobOutputs");
  outputs.innerHTML = "";
  for (const [kind, path] of Object.entries(job.output_files || {})) {
    outputs.appendChild(card(`<strong>${kind}</strong><p class="muted">${path}</p>`));
  }
  if (job.status === "interrupted") {
    document.querySelector("#reviewBox").classList.remove("hidden");
    document.querySelector("#interruptPayload").textContent = JSON.stringify(job.interrupt_payload, null, 2);
  }
  const timeline = document.querySelector("#agentTimeline");
  if (timeline) {
    timeline.textContent = JSON.stringify({
      agent_results: job.agent_results || [],
      supervisor_decisions: job.supervisor_decisions || [],
      evaluation_result: job.evaluation_result || {},
    }, null, 2);
  }
  const metrics = document.querySelector("#agentMetrics");
  if (metrics) {
    try {
      metrics.textContent = JSON.stringify(
        await api(`/api/jobs/${jobId}/agent-metrics`),
        null,
        2,
      );
    } catch (error) {
      metrics.textContent = String(error);
    }
  }
  const traceGraph = document.querySelector("#agentTraceGraph");
  if (traceGraph) {
    try {
      const trace = await api(`/api/jobs/${jobId}/agent-trace`);
      traceGraph.innerHTML = "";
      for (const node of trace.nodes || []) {
        const button = document.createElement("button");
        button.className = `trace-node ${node.status || ""}`;
        button.textContent = `${node.label} ${node.status || ""}`;
        button.addEventListener("click", () => {
          document.querySelector("#agentTraceDetail").textContent = JSON.stringify(node, null, 2);
        });
        traceGraph.appendChild(button);
        const edge = (trace.edges || []).find((item) => item.from === node.id);
        if (edge) {
          const arrow = document.createElement("span");
          arrow.className = "trace-edge";
          arrow.textContent = "→";
          traceGraph.appendChild(arrow);
        }
      }
      if (!traceGraph.children.length) {
        traceGraph.textContent = "No agent trace yet.";
      }
    } catch (error) {
      traceGraph.textContent = String(error);
    }
  }
}

function startJobEvents(jobId) {
  const log = document.querySelector("#jobLog");
  const source = new EventSource(`/api/jobs/${jobId}/events`);
  for (const name of ["started", "step_started", "step_finished", "agent_started", "agent_finished", "agent_failed", "supervisor_decision", "citation_audit_completed", "evaluation_completed", "trace_updated", "interrupted", "resumed", "exported", "failed", "completed", "cancel_requested"]) {
    source.addEventListener(name, (event) => {
      const item = JSON.parse(event.data);
      log.textContent += `[${item.created_at}] ${item.event} ${item.step || ""} ${item.message || ""}\n`;
      if (["completed", "failed", "interrupted"].includes(item.event)) {
        renderJob(jobId);
      }
    });
  }
}

async function initJob() {
  const jobId = document.body.dataset.jobId;
  await renderJob(jobId);
  startJobEvents(jobId);
  document.querySelector("#refreshJob")?.addEventListener("click", () => renderJob(jobId));
  document.querySelector("#resumeButton")?.addEventListener("click", async () => {
    const review = document.querySelector("#reviewText").value;
    await api(`/api/jobs/${jobId}/resume`, {
      method: "POST",
      body: JSON.stringify({ review }),
    });
    location.reload();
  });
}

async function initCollections() {
  const list = document.querySelector("#collectionList");
  async function refresh() {
    const rows = await api("/api/collections");
    list.innerHTML = "";
    for (const row of rows) {
      list.appendChild(card(`<strong>${row.collection_name}</strong><p class="muted">sources=${row.source_count}, chunks=${row.chunk_count}<br>${row.updated_at || ""}</p>`));
    }
  }
  await refresh();
  document.querySelector("#collectionForm")?.addEventListener("submit", async (event) => {
    event.preventDefault();
    const form = new FormData(event.target);
    await api("/api/collections", {
      method: "POST",
      body: JSON.stringify({ collection: form.get("collection"), source_paths: lines(form.get("source_paths")), reset: true }),
    });
    await refresh();
  });
  document.querySelector("#retrieveButton")?.addEventListener("click", async () => {
    const collection = new FormData(document.querySelector("#collectionForm")).get("collection");
    const query = document.querySelector("#retrieveQuery").value;
    const result = await api(`/api/collections/${collection}/retrieve`, {
      method: "POST",
      body: JSON.stringify({ query, top_k: 5 }),
    });
    document.querySelector("#retrieveResult").textContent = JSON.stringify(result, null, 2);
  });
}

let selectedDocumentId = null;

async function initDocuments() {
  const list = document.querySelector("#documentList");
  const docs = await api("/api/documents");
  for (const doc of docs) {
    const item = card(`<strong>${doc.name}</strong><p class="muted">${doc.path}</p><a href="/api/documents/${doc.document_id}/download">下载</a>`);
    item.addEventListener("click", async () => {
      selectedDocumentId = doc.document_id;
      const preview = await api(`/api/documents/${doc.document_id}/preview`);
      document.querySelector("#documentPreview").textContent = preview.content || JSON.stringify(preview, null, 2);
    });
    list.appendChild(item);
  }
  async function docAction(action) {
    if (!selectedDocumentId) return;
    const collection = document.querySelector("#docCollection").value || null;
    const result = await api(`/api/documents/${selectedDocumentId}/${action}`, {
      method: "POST",
      body: JSON.stringify({ collection }),
    });
    document.querySelector("#documentPreview").textContent = JSON.stringify(result, null, 2);
  }
  document.querySelector("#verifyDoc")?.addEventListener("click", () => docAction("verify-citations"));
  document.querySelector("#repairDoc")?.addEventListener("click", () => docAction("repair-citations"));
  document.querySelector("#evaluateDoc")?.addEventListener("click", () => docAction("evaluate"));
}

async function initSettings() {
  document.querySelector("#healthBox").textContent = JSON.stringify(await api("/api/health"), null, 2);
  document.querySelector("#settingsBox").textContent = JSON.stringify(await api("/api/settings"), null, 2);
  document.querySelector("#traceCheck")?.addEventListener("click", async () => {
    document.querySelector("#settingsActionBox").textContent = JSON.stringify(await api("/api/settings/trace-check"), null, 2);
  });
  document.querySelector("#checkModel")?.addEventListener("click", async () => {
    document.querySelector("#settingsActionBox").textContent = "checking model...";
    document.querySelector("#settingsActionBox").textContent = JSON.stringify(await api("/api/settings/check-model", { method: "POST", body: "{}" }), null, 2);
  });
}

const page = document.body.dataset.page;
if (page === "index") initIndex();
if (page === "job") initJob();
if (page === "collections") initCollections();
if (page === "documents") initDocuments();
if (page === "settings") initSettings();
