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
const openYamlButton = document.getElementById("openYamlButton");
const validateButton = document.getElementById("validateButton");
const saveYamlButton = document.getElementById("saveYamlButton");
const exportGdsButton = document.getElementById("exportGdsButton");
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

openYamlButton.addEventListener("click", openYaml);
validateButton.addEventListener("click", validateYaml);
saveYamlButton.addEventListener("click", saveYaml);
exportGdsButton.addEventListener("click", exportGds);
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

async function openYaml() {
  if (dirty && !window.confirm("Discard unsaved YAML changes?")) {
    setStatus("Open canceled");
    return;
  }
  setBusy(true, "Opening YAML");
  try {
    const data = await postJson("/api/yaml/open", {});
    if (!data.ok) {
      setStatus(data.canceled ? "Open canceled" : "Open failed");
      renderErrors(data.errors || []);
      return;
    }
    editor.value = data.yaml_text;
    dirty = false;
    updateDirtyState();
    renderMessages([{ message: `YAML opened: ${data.path_label}`, ok: true }]);
    setStatus("YAML opened");
    await previewSvg();
  } catch (error) {
    renderMessages([{ message: messageForError(error), ok: false }]);
    setStatus("Open error");
  } finally {
    setBusy(false);
  }
}

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

async function saveYaml() {
  setBusy(true, "Choosing path");
  try {
    const choice = await chooseSavePath("yaml", "config.yaml");
    if (!choice.ok) {
      setStatus(choice.canceled ? "Save canceled" : "Save blocked");
      renderErrors(choice.errors || []);
      return;
    }
    const force = choice.exists ? window.confirm(`Overwrite ${choice.path_label}?`) : false;
    if (choice.exists && !force) {
      setStatus("Overwrite canceled");
      return;
    }
    const data = await postJson("/api/yaml/save", {
      yaml_text: editor.value,
      path_token: choice.path_token,
      force,
    });
    if (!data.ok) {
      renderErrors(data.errors);
      setStatus("Save failed");
      return;
    }
    renderMessages([{ message: `YAML saved: ${data.path_label}`, ok: true }]);
    dirty = false;
    updateDirtyState();
    setStatus("YAML saved");
  } catch (error) {
    renderMessages([{ message: messageForError(error), ok: false }]);
    setStatus("Save error");
  } finally {
    setBusy(false);
  }
}

async function exportGds() {
  setBusy(true, "Choosing path");
  try {
    const choice = await chooseSavePath("gds", "layout.gds");
    if (!choice.ok) {
      setStatus(choice.canceled ? "Export canceled" : "Export blocked");
      renderErrors(choice.errors || []);
      return;
    }
    const force = choice.exists ? window.confirm(`Overwrite ${choice.path_label}?`) : false;
    if (choice.exists && !force) {
      setStatus("Overwrite canceled");
      return;
    }
    setStatus("Exporting GDS");
    const data = await postJson("/api/export/gds", {
      yaml_text: editor.value,
      path_token: choice.path_token,
      force,
    });
    if (!data.ok) {
      renderErrors(data.errors);
      setStatus("Export failed");
      return;
    }
    renderMessages([{ message: `GDS exported: ${data.path_label} (${data.region_count} region(s)).`, ok: true }]);
    setStatus("GDS exported");
  } catch (error) {
    renderMessages([{ message: messageForError(error), ok: false }]);
    setStatus("Export error");
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

async function chooseSavePath(kind, suggestedName) {
  return postJson("/api/file/choose-save", {
    kind,
    suggested_name: suggestedName,
  });
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
  openYamlButton.disabled = isBusy;
  validateButton.disabled = isBusy;
  saveYamlButton.disabled = isBusy;
  exportGdsButton.disabled = isBusy;
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
