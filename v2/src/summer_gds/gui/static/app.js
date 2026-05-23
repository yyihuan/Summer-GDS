const SAMPLE_YAML = `schema_version: 2
global:
  unit: um
  dbu: 0.001
gds:
  top_cell: TOP
shapes:
  - type: base_shape
    sid: 0
    name: source
    layer: [1, 0]
    source:
      vertices: [[0, 0], [100, 0], [100, 80], [0, 80]]
`;

const TOKEN = window.SUMMER_GDS_SESSION_TOKEN;
const editor = document.getElementById("yamlEditor");
const validateButton = document.getElementById("validateButton");
const previewButton = document.getElementById("previewButton");
const errorList = document.getElementById("errorList");
const previewCanvas = document.getElementById("previewCanvas");
const statusText = document.getElementById("statusText");
const dirtyState = document.getElementById("dirtyState");
const workspace = document.getElementById("workspace");
const splitter = document.getElementById("splitter");

let debounceTimer = 0;
let previewController = null;
let requestSeq = 0;
let dirty = false;

editor.value = SAMPLE_YAML;

validateButton.addEventListener("click", validateYaml);
previewButton.addEventListener("click", previewSvg);
editor.addEventListener("input", () => {
  dirty = true;
  updateDirtyState();
  window.clearTimeout(debounceTimer);
  debounceTimer = window.setTimeout(previewSvg, 450);
});

splitter.addEventListener("pointerdown", (event) => {
  splitter.classList.add("dragging");
  splitter.setPointerCapture(event.pointerId);
});

splitter.addEventListener("pointermove", (event) => {
  if (!splitter.classList.contains("dragging")) {
    return;
  }
  const bounds = workspace.getBoundingClientRect();
  const minPane = Math.min(360, Math.floor((bounds.width - 12) / 2));
  const left = clamp(event.clientX - bounds.left, minPane, bounds.width - minPane - 12);
  const right = bounds.width - left - 12;
  workspace.style.gridTemplateColumns = `${left}px 12px ${right}px`;
});

splitter.addEventListener("pointerup", (event) => {
  splitter.classList.remove("dragging");
  splitter.releasePointerCapture(event.pointerId);
});

updateDirtyState();
previewSvg();

async function validateYaml() {
  setBusy(true, "Validating");
  try {
    const data = await postJson("/api/validate", { yaml_text: editor.value });
    if (data.ok) {
      renderMessages([{ message: `OK, ${data.shape_count} shape(s).`, ok: true }]);
      setStatus("Valid");
      dirty = false;
      updateDirtyState();
      return;
    }
    renderErrors(data.errors);
    setStatus("Invalid");
  } catch (error) {
    renderMessages([{ message: messageForError(error), ok: false }]);
    setStatus("Error");
  } finally {
    setBusy(false);
  }
}

async function previewSvg() {
  requestSeq += 1;
  const requestId = `preview-${requestSeq}`;
  if (previewController) {
    previewController.abort();
  }
  previewController = new AbortController();
  const timeout = window.setTimeout(() => previewController.abort(), 8000);
  setBusy(true, "Rendering");
  try {
    const data = await postJson(
      "/api/preview/svg",
      { yaml_text: editor.value, request_id: requestId },
      previewController.signal,
    );
    if (requestId !== `preview-${requestSeq}`) {
      return;
    }
    if (data.ok) {
      previewCanvas.innerHTML = stripXmlDeclaration(data.svg_text);
      renderMessages([{ message: `Preview ready, ${data.region_count} region(s).`, ok: true }]);
      setStatus("Preview OK");
      dirty = false;
      updateDirtyState();
      return;
    }
    renderErrors(data.errors);
    previewCanvas.innerHTML = `<div class="empty-preview"><strong>预览失败</strong><span>修正 YAML 后会自动重试。</span></div>`;
    setStatus("Preview failed");
  } catch (error) {
    renderMessages([{ message: messageForError(error), ok: false }]);
    setStatus(error.name === "AbortError" ? "Canceled" : "Error");
  } finally {
    window.clearTimeout(timeout);
    setBusy(false);
  }
}

async function postJson(path, payload, signal) {
  const response = await fetch(path, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "X-Summer-GDS-Token": TOKEN,
    },
    body: JSON.stringify(payload),
    signal,
  });
  const data = await response.json();
  if (!response.ok) {
    const message = data.errors?.[0]?.message || `Request failed with ${response.status}`;
    throw new Error(message);
  }
  return data;
}

function setBusy(isBusy, label = "") {
  validateButton.disabled = isBusy;
  previewButton.disabled = isBusy;
  if (label) {
    setStatus(label);
  }
}

function setStatus(label) {
  statusText.textContent = label;
}

function updateDirtyState() {
  dirtyState.textContent = dirty ? "Dirty" : "Clean";
}

function renderErrors(errors) {
  renderMessages(
    errors.map((error) => ({
      message: `${error.code} at ${error.path}: ${error.message}`,
      ok: false,
    })),
  );
}

function renderMessages(messages) {
  errorList.replaceChildren();
  for (const item of messages) {
    const node = document.createElement("p");
    node.className = item.ok ? "message ok" : "message";
    node.textContent = item.message;
    errorList.appendChild(node);
  }
}

function messageForError(error) {
  if (error.name === "AbortError") {
    return "Preview request canceled or timed out.";
  }
  return error.message || "Unexpected GUI error.";
}

function stripXmlDeclaration(svgText) {
  return svgText.replace(/<\?xml[^>]*>\s*/i, "");
}

function clamp(value, min, max) {
  return Math.max(min, Math.min(max, value));
}
