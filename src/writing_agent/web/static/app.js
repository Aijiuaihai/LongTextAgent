const form = document.querySelector("#generateForm");
const resultBox = document.querySelector("#resultBox");
const runState = document.querySelector("#runState");
const submitButton = document.querySelector("#submitButton");
const configLine = document.querySelector("#configLine");

function setState(text, className = "") {
  runState.textContent = text;
  runState.className = `status-pill ${className}`.trim();
}

function renderResult(data) {
  if (data.error) {
    resultBox.innerHTML = `<p class="error-text">${data.error}</p>`;
    return;
  }
  const outputPaths = Object.entries(data.output_paths || {})
    .map(([key, value]) => `<dt>${key}</dt><dd>${value}</dd>`)
    .join("");
  const errors = (data.errors || [])
    .map((item) => `<li>${item}</li>`)
    .join("");
  resultBox.innerHTML = `
    <dl>
      <dt>thread_id</dt>
      <dd>${data.thread_id}</dd>
      <dt>topic</dt>
      <dd>${data.topic}</dd>
      <dt>output_path</dt>
      <dd>${data.output_path || ""}</dd>
      ${outputPaths}
    </dl>
    ${errors ? `<h3>Warnings</h3><ul>${errors}</ul>` : ""}
  `;
}

async function loadConfig() {
  try {
    const response = await fetch("/api/config");
    const data = await response.json();
    configLine.textContent = `${data.llm_provider} · ${data.ollama_model || data.openai_model || ""}`;
  } catch (_error) {
    configLine.textContent = "模型配置读取失败";
  }
}

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  const data = new FormData(form);
  if (!form.rag.checked) {
    data.set("rag", "false");
  }
  if (!form.use_llm.checked) {
    data.set("use_llm", "false");
  }
  setState("生成中", "running");
  submitButton.disabled = true;
  resultBox.innerHTML = "<p>Agent workflow 正在执行，长文本生成可能需要数分钟。</p>";

  try {
    const response = await fetch("/api/generate", {
      method: "POST",
      body: data,
    });
    const payload = await response.json();
    if (!response.ok) {
      setState("失败", "error");
      renderResult(payload);
      return;
    }
    setState("完成", "done");
    renderResult(payload);
  } catch (error) {
    setState("失败", "error");
    renderResult({ error: String(error) });
  } finally {
    submitButton.disabled = false;
  }
});

loadConfig();
