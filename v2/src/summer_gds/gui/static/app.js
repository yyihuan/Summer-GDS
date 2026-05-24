const TOKEN = window.SUMMER_GDS_SESSION_TOKEN;
const REQUEST_TIMEOUT_MS = 15000;
const VALIDATION_TIMEOUT_MS = 30000;
const FILE_DIALOG_TIMEOUT_MS = 120000;
const EXPORT_TIMEOUT_MS = 120000;
const BUSY_WATCHDOG_GRACE_MS = 5000;

const app = document.getElementById("app");
const workspace = document.getElementById("workspace");
const workspaceContent = document.getElementById("workspaceContent");
const shapeList = document.getElementById("shapeList");
const yamlPreviewPanel = document.getElementById("yamlPreviewPanel");
const yamlPreview = document.getElementById("yamlPreview");
const messageList = document.getElementById("messageList");
const statusText = document.getElementById("statusText");
const dirtyState = document.getElementById("dirtyState");
const previewState = document.getElementById("previewState");
const exportState = document.getElementById("exportState");
const previewViewport = document.getElementById("previewViewport");
const previewCanvas = document.getElementById("previewCanvas");
const splitter = document.getElementById("splitter");

const openYamlButton = document.getElementById("openYamlButton");
const saveYamlButton = document.getElementById("saveYamlButton");
const validateButton = document.getElementById("validateButton");
const exportGdsButton = document.getElementById("exportGdsButton");
const builderModeButton = document.getElementById("builderModeButton");
const yamlModeButton = document.getElementById("yamlModeButton");
const globalSettingsButton = document.getElementById("globalSettingsButton");
const addBaseButton = document.getElementById("addBaseButton");
const addViaButton = document.getElementById("addViaButton");
const addRingsButton = document.getElementById("addRingsButton");
const fitPreviewButton = document.getElementById("fitPreviewButton");
const zoomOutButton = document.getElementById("zoomOutButton");
const zoomInButton = document.getElementById("zoomInButton");

const globalDialog = document.getElementById("globalDialog");
const globalForm = document.getElementById("globalForm");
const closeGlobalButton = document.getElementById("closeGlobalButton");
const cancelGlobalButton = document.getElementById("cancelGlobalButton");
const globalDbuInput = document.getElementById("globalDbuInput");
const globalPrecisionInput = document.getElementById("globalPrecisionInput");
const topCellInput = document.getElementById("topCellInput");
const gdsOutputInput = document.getElementById("gdsOutputInput");

const shapeDialog = document.getElementById("shapeDialog");
const shapeForm = document.getElementById("shapeForm");
const closeShapeButton = document.getElementById("closeShapeButton");
const cancelShapeButton = document.getElementById("cancelShapeButton");
const shapeDialogTitle = document.getElementById("shapeDialogTitle");
const shapeDialogType = document.getElementById("shapeDialogType");
const shapeSidInput = document.getElementById("shapeSidInput");
const shapeTypeInput = document.getElementById("shapeTypeInput");
const shapeNameInput = document.getElementById("shapeNameInput");
const shapeLayerInput = document.getElementById("shapeLayerInput");
const shapeDatatypeInput = document.getElementById("shapeDatatypeInput");

const baseEditor = document.getElementById("baseEditor");
const baseSourceModeInput = document.getElementById("baseSourceModeInput");
const baseVerticesEditor = document.getElementById("baseVerticesEditor");
const baseRefEditor = document.getElementById("baseRefEditor");
const baseRefInput = document.getElementById("baseRefInput");
const baseOffsetInput = document.getElementById("baseOffsetInput");
const baseFilletStatus = document.getElementById("baseFilletStatus");
const baseFilletModeInput = document.getElementById("baseFilletModeInput");
const baseFilletRadiusField = document.getElementById("baseFilletRadiusField");
const baseFilletRadiusInput = document.getElementById("baseFilletRadiusInput");
const baseFilletRadiiEditor = document.getElementById("baseFilletRadiiEditor");
const baseFilletRadiiShell = document.getElementById("baseFilletRadiiShell");
const baseFilletRadiiInput = document.getElementById("baseFilletRadiiInput");
const formatBaseFilletRadiiButton = document.getElementById("formatBaseFilletRadiiButton");
const vertexStatus = document.getElementById("vertexStatus");
const vertexListShell = document.getElementById("vertexListShell");
const vertexLineNumbers = document.getElementById("vertexLineNumbers");
const vertexListInput = document.getElementById("vertexListInput");
const formatVertexListButton = document.getElementById("formatVertexListButton");

const viaEditor = document.getElementById("viaEditor");
const viaRefInput = document.getElementById("viaRefInput");
const viaInnerInput = document.getElementById("viaInnerInput");
const viaOuterInput = document.getElementById("viaOuterInput");
const viaInnerFilletInput = document.getElementById("viaInnerFilletInput");
const viaOuterFilletInput = document.getElementById("viaOuterFilletInput");

const ringsEditor = document.getElementById("ringsEditor");
const ringsRefInput = document.getElementById("ringsRefInput");
const ringsCountInput = document.getElementById("ringsCountInput");
const ringsPitchInput = document.getElementById("ringsPitchInput");
const ringsWidthInput = document.getElementById("ringsWidthInput");
const ringsFilletModeInput = document.getElementById("ringsFilletModeInput");
const ringsFilletTableWrap = document.getElementById("ringsFilletTableWrap");
const ringsFilletTable = document.getElementById("ringsFilletTable");
const applySameRingsFilletButton = document.getElementById("applySameRingsFilletButton");

const state = {
  activeMode: "builder",
  formDraft: createDefaultDraft(),
  generatedYamlText: "",
  lastSavedOrLoadedYamlText: "",
  parsedConfig: null,
  yamlStatus: "syncing",
  previewStatus: "idle",
  previewSvgText: "",
  previewRequestId: 0,
  busy: false,
  busyReason: null,
  currentYamlPathLabel: null,
  importedGdsOutput: null,
  messages: [],
};

let previewDebounceTimer = 0;
let previewController = null;
let previewScale = 1;
let vertexRows = [];
let ringsFilletRows = [];
let busyWatchdogTimer = 0;
let lastVertexParse = { ok: true, vertices: [] };
let lastBaseFilletRadiiParse = { ok: true, radii: [] };

bindEvents();
initialize();

function bindEvents() {
  builderModeButton.addEventListener("click", () => setMode("builder"));
  yamlModeButton.addEventListener("click", () => setMode("yaml_preview"));
  globalSettingsButton.addEventListener("click", openGlobalDialog);

  openYamlButton.addEventListener("click", openYaml);
  saveYamlButton.addEventListener("click", saveYaml);
  validateButton.addEventListener("click", validateYaml);
  exportGdsButton.addEventListener("click", exportGds);

  addBaseButton.addEventListener("click", () => addShape("base_shape"));
  addViaButton.addEventListener("click", () => addShape("via"));
  addRingsButton.addEventListener("click", () => addShape("rings"));

  fitPreviewButton.addEventListener("click", fitPreview);
  zoomOutButton.addEventListener("click", () => zoomPreview(0.85));
  zoomInButton.addEventListener("click", () => zoomPreview(1.18));

  globalForm.addEventListener("submit", (event) => {
    event.preventDefault();
    applyGlobalSettings();
  });
  closeGlobalButton.addEventListener("click", closeGlobalDialog);
  cancelGlobalButton.addEventListener("click", closeGlobalDialog);
  for (const input of [globalDbuInput, globalPrecisionInput]) {
    input.addEventListener("input", debounce(validateGlobalFields, 300));
    input.addEventListener("blur", validateGlobalFields);
  }

  shapeForm.addEventListener("submit", (event) => {
    event.preventDefault();
    applyShapeDialog();
  });
  closeShapeButton.addEventListener("click", closeShapeDialog);
  cancelShapeButton.addEventListener("click", closeShapeDialog);
  baseSourceModeInput.addEventListener("change", () => {
    renderBaseSourceMode();
    renderBaseFilletMode();
  });
  baseFilletModeInput.addEventListener("change", handleBaseFilletModeChange);
  baseFilletRadiiInput.addEventListener("input", handleBaseFilletRadiiInput);
  formatBaseFilletRadiiButton.addEventListener("click", formatBaseFilletRadiiList);
  vertexListInput.addEventListener("input", handleVertexListInput);
  vertexListInput.addEventListener("scroll", syncVertexLineNumberScroll);
  formatVertexListButton.addEventListener("click", formatVertexList);
  ringsCountInput.addEventListener("input", () => {
    syncRingsFilletRowsFromInputs();
    renderRingsFilletRows(readInteger(ringsCountInput.value) || 1);
  });
  ringsFilletModeInput.addEventListener("change", renderRingsFilletMode);
  applySameRingsFilletButton.addEventListener("click", applySameRingsFillet);

  splitter.addEventListener("pointerdown", startSplitDrag);
  splitter.addEventListener("pointermove", moveSplitDrag);
  splitter.addEventListener("pointerup", endSplitDrag);
  splitter.addEventListener("keydown", handleSplitterKeydown);
}

function initialize() {
  state.generatedYamlText = serializeDraftToYaml(state.formDraft);
  state.lastSavedOrLoadedYamlText = state.generatedYamlText;
  render();
  syncYamlFromDraft({ preview: true, markDirty: false });
}

function createDefaultDraft() {
  return {
    schema_version: 2,
    global: { unit: "um", dbu: 0.001, precision: null },
    gds: { top_cell: "TOP", output: null },
    shapes: [createBaseShape(0)],
  };
}

function createBaseShape(sid, overrides = {}) {
  return {
    type: "base_shape",
    sid,
    name: overrides.name || `base_${sid}`,
    layer: overrides.layer || [1, 0],
    source: overrides.source || {
      vertices: [
        [0, 0],
        [100, 0],
        [100, 80],
        [0, 80],
      ],
    },
    fillet: overrides.fillet || null,
  };
}

function createViaShape(sid, sourceRef) {
  return {
    type: "via",
    sid,
    name: `via_${sid}`,
    layer: [10, 0],
    source: { ref: sourceRef },
    offsets: { inner: -5, outer: 8 },
    fillet: null,
  };
}

function createRingsShape(sid, sourceRef) {
  return {
    type: "rings",
    sid,
    name: `rings_${sid}`,
    layer: [20, 0],
    source: { ref: sourceRef },
    count: 3,
    pitch: 12,
    width: 4,
    filletMode: "none",
    fillet: null,
  };
}

function render() {
  app.dataset.yamlStatus = state.yamlStatus;
  app.dataset.previewStatus = state.previewStatus;
  app.dataset.dirty = String(isDirty());
  app.dataset.busy = String(state.busy);
  previewViewport.dataset.previewState = state.previewStatus;
  workspaceContent.dataset.mode = state.activeMode;

  dirtyState.textContent = isDirty() ? "YAML 已修改" : "YAML 未修改";
  dirtyState.dataset.state = isDirty() ? "dirty" : "clean";
  previewState.textContent = previewStateText(state.previewStatus);
  previewState.dataset.state = state.previewStatus;

  builderModeButton.classList.toggle("is-active", state.activeMode === "builder");
  builderModeButton.setAttribute("aria-pressed", String(state.activeMode === "builder"));
  yamlModeButton.classList.toggle("is-active", state.activeMode === "yaml_preview");
  yamlModeButton.setAttribute("aria-pressed", String(state.activeMode === "yaml_preview"));
  shapeList.hidden = state.activeMode !== "builder";
  yamlPreviewPanel.hidden = state.activeMode !== "yaml_preview";

  addViaButton.disabled = state.busy || baseShapes().length === 0;
  addRingsButton.disabled = state.busy || baseShapes().length === 0;
  for (const button of [openYamlButton, saveYamlButton, validateButton, exportGdsButton, addBaseButton, globalSettingsButton]) {
    button.disabled = state.busy;
  }

  yamlPreview.value = state.generatedYamlText;
  renderShapeList();
  renderMessages();
}

function renderShapeList() {
  shapeList.replaceChildren();
  if (state.formDraft.shapes.length === 0) {
    const empty = document.createElement("div");
    empty.className = "empty-list";
    empty.textContent = "暂无图形。请先添加基础图形。";
    shapeList.appendChild(empty);
    return;
  }
  for (const shape of state.formDraft.shapes) {
    shapeList.appendChild(shapeCard(shape));
  }
}

function shapeCard(shape) {
  const card = document.createElement("article");
  card.className = "shape-card";
  card.dataset.shapeType = shape.type;
  card.dataset.sid = String(shape.sid);

  const header = document.createElement("header");
  header.className = "shape-card-header";
  header.innerHTML = `
    <div>
      <span class="shape-id">#${shape.sid}</span>
      <strong>${escapeHtml(shape.name)}</strong>
      <span class="type-badge">${shape.type}</span>
    </div>
  `;
  const actions = document.createElement("div");
  actions.className = "shape-actions";
  actions.appendChild(actionButton("编辑", "edit", shape.sid));
  actions.appendChild(actionButton("删除", "delete", shape.sid, "button-danger"));
  if (shape.type === "base_shape") {
    actions.appendChild(actionButton("Offset Copy", "offset-copy", shape.sid));
    actions.appendChild(actionButton("Create Via", "create-via", shape.sid));
    actions.appendChild(actionButton("Create Rings", "create-rings", shape.sid));
  }
  header.appendChild(actions);
  card.appendChild(header);

  const summary = document.createElement("dl");
  summary.className = "shape-summary";
  for (const item of shapeSummary(shape)) {
    const wrapper = document.createElement("div");
    wrapper.innerHTML = `<dt>${escapeHtml(item.label)}</dt><dd>${escapeHtml(item.value)}</dd>`;
    summary.appendChild(wrapper);
  }
  card.appendChild(summary);
  return card;
}

function actionButton(label, action, sid, extraClass = "") {
  const button = document.createElement("button");
  button.className = `button button-ghost ${extraClass}`.trim();
  button.type = "button";
  button.textContent = label;
  button.dataset.action = action;
  button.dataset.sid = String(sid);
  button.addEventListener("click", handleShapeAction);
  return button;
}

function shapeSummary(shape) {
  const layer = `[${shape.layer[0]}, ${shape.layer[1]}]`;
  const source = shape.source.vertices ? `vertices ${shape.source.vertices.length}` : `ref #${shape.source.ref}`;
  if (shape.type === "via") {
    return [
      { label: "Layer", value: layer },
      { label: "Offsets", value: `inner ${shape.offsets.inner}, outer ${shape.offsets.outer}` },
      { label: "Source", value: source },
    ];
  }
  if (shape.type === "rings") {
    return [
      { label: "Layer", value: layer },
      { label: "Rings", value: `count ${shape.count}, pitch ${shape.pitch}, width ${shape.width}` },
      { label: "Source", value: source },
    ];
  }
  return [
    { label: "Layer", value: layer },
    { label: "Source", value: source },
    { label: "Fillet", value: baseFilletSummary(shape.fillet) },
  ];
}

function baseFilletSummary(fillet) {
  if (!fillet) {
    return "none";
  }
  if (fillet.radius !== undefined) {
    return `r=${fillet.radius}`;
  }
  if (fillet.radii) {
    return `radii x${fillet.radii.length}`;
  }
  return "none";
}

function baseFilletMode(fillet) {
  if (!fillet) {
    return "none";
  }
  if (fillet.radii) {
    return "radii";
  }
  if (fillet.radius !== undefined) {
    return "radius";
  }
  return "none";
}

function handleShapeAction(event) {
  const sid = Number(event.currentTarget.dataset.sid);
  const action = event.currentTarget.dataset.action;
  const shape = findShape(sid);
  if (!shape) {
    return;
  }
  if (action === "edit") {
    openShapeDialog(shape);
  } else if (action === "delete") {
    deleteShape(shape);
  } else if (action === "offset-copy") {
    addOffsetCopy(shape);
  } else if (action === "create-via") {
    addShape("via", shape.sid);
  } else if (action === "create-rings") {
    addShape("rings", shape.sid);
  }
}

function addShape(type, sourceRef = null) {
  const sid = nextSid();
  let shape;
  if (type === "base_shape") {
    shape = createBaseShape(sid, { name: `base_${sid}` });
  } else {
    const baseSid = sourceRef ?? baseShapes()[0]?.sid;
    if (baseSid === undefined) {
      pushMessage("请先创建 base_shape。", false);
      render();
      return;
    }
    shape = type === "via" ? createViaShape(sid, baseSid) : createRingsShape(sid, baseSid);
  }
  state.formDraft.shapes.push(shape);
  state.exported = false;
  syncYamlFromDraft({ preview: true });
  openShapeDialog(shape);
}

function addOffsetCopy(sourceShape) {
  const sid = nextSid();
  const shape = createBaseShape(sid, {
    name: `${sourceShape.name}_offset`,
    layer: [...sourceShape.layer],
    source: { ref: sourceShape.sid, offset: 10 },
  });
  state.formDraft.shapes.push(shape);
  syncYamlFromDraft({ preview: true });
  openShapeDialog(shape);
}

function deleteShape(shape) {
  const dependents = state.formDraft.shapes.filter((candidate) => candidate.source?.ref === shape.sid);
  if (dependents.length > 0) {
    pushMessage(`不能删除 #${shape.sid}：仍被 ${dependents.map((item) => `#${item.sid}`).join(", ")} 引用。`, false);
    render();
    return;
  }
  if (!window.confirm(`删除 #${shape.sid} ${shape.name}？`)) {
    return;
  }
  state.formDraft.shapes = state.formDraft.shapes.filter((candidate) => candidate.sid !== shape.sid);
  syncYamlFromDraft({ preview: true });
}

function openGlobalDialog() {
  globalDbuInput.value = state.formDraft.global.dbu;
  globalPrecisionInput.value = state.formDraft.global.precision ?? "";
  topCellInput.value = state.formDraft.gds.top_cell || "TOP";
  gdsOutputInput.value = state.importedGdsOutput || "";
  clearFieldErrors(globalDialog);
  showDialog(globalDialog);
}

function closeGlobalDialog() {
  closeDialog(globalDialog);
}

function applyGlobalSettings() {
  if (!validateGlobalFields()) {
    return;
  }
  state.formDraft.global.dbu = Number(globalDbuInput.value);
  state.formDraft.global.precision = globalPrecisionInput.value === "" ? null : Number(globalPrecisionInput.value);
  state.formDraft.gds.top_cell = topCellInput.value.trim() || "TOP";
  closeGlobalDialog();
  syncYamlFromDraft({ preview: true });
}

function validateGlobalFields() {
  clearFieldErrors(globalDialog);
  const dbu = Number(globalDbuInput.value);
  const precisionText = globalPrecisionInput.value.trim();
  const precision = precisionText === "" ? null : Number(precisionText);
  let ok = true;
  if (!Number.isFinite(dbu) || dbu < 0.00001 || dbu > 1) {
    setFieldError("field-global-dbu", "dbu 必须在 0.00001 到 1 之间。");
    ok = false;
  }
  if (precision !== null) {
    if (!Number.isFinite(precision) || precision <= 0) {
      setFieldError("field-global-precision", "precision 必须是正数。");
      ok = false;
    } else if (Number.isFinite(dbu)) {
      const ratio = precision / dbu;
      if (precision < dbu || Math.abs(ratio - Math.round(ratio)) > 1e-10) {
        setFieldError("field-global-precision", "precision 必须大于等于 dbu，且是 dbu 的整数倍。");
        ok = false;
      }
    }
  }
  return ok;
}

function openShapeDialog(shape) {
  clearFieldErrors(shapeDialog);
  shapeSidInput.value = shape.sid;
  shapeTypeInput.value = shape.type;
  shapeDialogType.textContent = shape.type.toUpperCase();
  shapeDialogTitle.textContent = `编辑 #${shape.sid} ${shape.name}`;
  shapeNameInput.value = shape.name;
  shapeLayerInput.value = shape.layer[0];
  shapeDatatypeInput.value = shape.layer[1];

  baseEditor.hidden = shape.type !== "base_shape";
  viaEditor.hidden = shape.type !== "via";
  ringsEditor.hidden = shape.type !== "rings";

  renderBaseOptions(baseRefInput, shape.sid);
  renderBaseOptions(viaRefInput, shape.sid);
  renderBaseOptions(ringsRefInput, shape.sid);

  if (shape.type === "base_shape") {
    const isRefSource = shape.source.ref !== undefined;
    baseSourceModeInput.value = isRefSource ? "ref" : "vertices";
    vertexRows = shape.source.vertices ? shape.source.vertices.map((point) => [...point]) : [];
    vertexListInput.value = formatVerticesForList(vertexRows);
    handleVertexListInput();
    baseRefInput.value = isRefSource ? String(shape.source.ref) : "";
    baseOffsetInput.value = isRefSource ? shape.source.offset ?? 0 : "";
    baseFilletModeInput.value = baseFilletMode(shape.fillet);
    baseFilletRadiusInput.value = shape.fillet?.radius ?? "";
    baseFilletRadiiInput.value = shape.fillet?.radii ? formatRadiiForList(shape.fillet.radii) : "";
    renderBaseSourceMode();
    renderBaseFilletMode();
  } else if (shape.type === "via") {
    viaRefInput.value = String(shape.source.ref);
    viaInnerInput.value = shape.offsets.inner;
    viaOuterInput.value = shape.offsets.outer;
    viaInnerFilletInput.value = shape.fillet?.inner?.radius ?? "";
    viaOuterFilletInput.value = shape.fillet?.outer?.radius ?? "";
  } else if (shape.type === "rings") {
    ringsRefInput.value = String(shape.source.ref);
    ringsCountInput.value = shape.count;
    ringsPitchInput.value = shape.pitch;
    ringsWidthInput.value = shape.width;
    ringsFilletModeInput.value = shape.fillet?.rings ? "per_ring" : "none";
    ringsFilletRows = shape.fillet?.rings ? shape.fillet.rings.map((ring) => ({
      inner: ring.inner?.radius ?? "",
      outer: ring.outer?.radius ?? "",
    })) : [];
    renderRingsFilletMode();
    renderRingsFilletRows(shape.count);
  }
  showDialog(shapeDialog);
}

function closeShapeDialog() {
  closeDialog(shapeDialog);
}

function applyShapeDialog() {
  clearFieldErrors(shapeDialog);
  const sid = Number(shapeSidInput.value);
  const type = shapeTypeInput.value;
  const shape = findShape(sid);
  if (!shape) {
    return;
  }
  const common = readCommonShapeFields();
  if (!common.ok) {
    return;
  }
  let nextShape = { ...shape, name: common.name, layer: common.layer };
  if (type === "base_shape") {
    const baseUpdate = readBaseFields();
    if (!baseUpdate.ok) {
      return;
    }
    nextShape = { ...nextShape, ...baseUpdate.value };
  } else if (type === "via") {
    const viaUpdate = readViaFields();
    if (!viaUpdate.ok) {
      return;
    }
    nextShape = { ...nextShape, ...viaUpdate.value };
  } else if (type === "rings") {
    const ringsUpdate = readRingsFields();
    if (!ringsUpdate.ok) {
      return;
    }
    nextShape = { ...nextShape, ...ringsUpdate.value };
  }
  state.formDraft.shapes = state.formDraft.shapes.map((candidate) => candidate.sid === sid ? nextShape : candidate);
  closeShapeDialog();
  syncYamlFromDraft({ preview: true });
}

function readCommonShapeFields() {
  const name = shapeNameInput.value.trim();
  const layer = readInteger(shapeLayerInput.value);
  const datatype = readInteger(shapeDatatypeInput.value);
  let ok = true;
  if (!name) {
    setFieldError("field-shape-name", "name 不能为空。");
    ok = false;
  }
  if (layer === null || layer < 0) {
    setFieldError("field-shape-layer", "layer 必须是非负整数。");
    ok = false;
  }
  if (datatype === null || datatype < 0) {
    setFieldError("field-shape-datatype", "datatype 必须是非负整数。");
    ok = false;
  }
  return ok ? { ok: true, name, layer: [layer, datatype] } : { ok: false };
}

function readBaseFields() {
  if (baseSourceModeInput.value === "ref") {
    const ref = readInteger(baseRefInput.value);
    const offset = readFiniteNumber(baseOffsetInput.value);
    const fillet = readBaseFillet(null, false);
    if (ref === null) {
      setFieldError("field-base-source-ref", "请选择 ref。");
      return { ok: false };
    }
    if (offset === null) {
      setFieldError("field-base-source-offset", "offset 必须是有限数值。");
      return { ok: false };
    }
    if (!fillet.ok) {
      return { ok: false };
    }
    return { ok: true, value: { source: { ref, offset }, fillet: fillet.value } };
  }

  const parsed = parseVertexList(vertexListInput.value);
  updateVertexListState(parsed);
  if (!parsed.ok) {
    setFieldError("field-base-vertices-list", parsed.message);
    return { ok: false };
  }
  const fillet = readBaseFillet(parsed.vertices.length, true);
  if (!fillet.ok) {
    return { ok: false };
  }
  return { ok: true, value: { source: { vertices: parsed.vertices }, fillet: fillet.value } };
}

function readViaFields() {
  const ref = readInteger(viaRefInput.value);
  const inner = readFiniteNumber(viaInnerInput.value);
  const outer = readFiniteNumber(viaOuterInput.value);
  let ok = true;
  if (ref === null) {
    setFieldError("field-via-source-ref", "请选择 source ref。");
    ok = false;
  }
  if (inner === null) {
    setFieldError("field-via-inner", "inner offset 必须是有限数值。");
    ok = false;
  }
  if (outer === null) {
    setFieldError("field-via-outer", "outer offset 必须是有限数值。");
    ok = false;
  }
  const fillet = {};
  const innerFillet = readRadius(viaInnerFilletInput.value);
  const outerFillet = readRadius(viaOuterFilletInput.value);
  if (innerFillet) {
    fillet.inner = innerFillet;
  }
  if (outerFillet) {
    fillet.outer = outerFillet;
  }
  return ok ? {
    ok: true,
    value: {
      source: { ref },
      offsets: { inner, outer },
      fillet: Object.keys(fillet).length ? fillet : null,
    },
  } : { ok: false };
}

function readRingsFields() {
  const ref = readInteger(ringsRefInput.value);
  const count = readInteger(ringsCountInput.value);
  const pitch = readFiniteNumber(ringsPitchInput.value);
  const width = readFiniteNumber(ringsWidthInput.value);
  let ok = true;
  if (ref === null) {
    setFieldError("field-rings-source-ref", "请选择 source ref。");
    ok = false;
  }
  if (count === null || count <= 0) {
    setFieldError("field-rings-count", "count 必须是正整数。");
    ok = false;
  }
  if (pitch === null || pitch <= 0) {
    setFieldError("field-rings-pitch", "pitch 必须是正数。");
    ok = false;
  }
  if (width === null || width <= 0) {
    setFieldError("field-rings-width", "width 必须是正数。");
    ok = false;
  }
  if (pitch !== null && width !== null && pitch < width) {
    setFieldError("field-rings-pitch", "pitch 必须大于等于 width。");
    ok = false;
  }

  let fillet = null;
  if (ringsFilletModeInput.value === "per_ring" && count !== null && count > 0) {
    syncRingsFilletRowsFromInputs();
    const rings = [];
    for (let index = 0; index < count; index += 1) {
      const row = ringsFilletRows[index] || { inner: "", outer: "" };
      const inner = row.inner === "" ? null : readFiniteNumber(row.inner);
      const outer = row.outer === "" ? null : readFiniteNumber(row.outer);
      if ((inner === null && row.inner !== "") || (outer === null && row.outer !== "")) {
        markRingFilletRowError(index);
        ok = false;
      }
      rings.push({
        inner: inner === null ? null : { radius: inner },
        outer: outer === null ? null : { radius: outer },
      });
    }
    fillet = { rings };
  }

  return ok ? {
    ok: true,
    value: {
      source: { ref },
      count,
      pitch,
      width,
      filletMode: ringsFilletModeInput.value,
      fillet,
    },
  } : { ok: false };
}

function renderBaseSourceMode() {
  const isRef = baseSourceModeInput.value === "ref";
  baseVerticesEditor.hidden = isRef;
  baseRefEditor.hidden = !isRef;
}

function handleBaseFilletModeChange() {
  if (baseFilletModeInput.value === "radii" && !baseFilletRadiiInput.value.trim()) {
    const parsedVertices = parseVertexList(vertexListInput.value);
    if (parsedVertices.ok) {
      const seedRadius = readFiniteNumber(baseFilletRadiusInput.value) ?? 0;
      baseFilletRadiiInput.value = formatRadiiForList(Array.from({ length: parsedVertices.vertices.length }, () => seedRadius));
    }
  }
  renderBaseFilletMode();
}

function renderBaseFilletMode() {
  const radiiOption = [...baseFilletModeInput.options].find((option) => option.value === "radii");
  const isRef = baseSourceModeInput.value === "ref";
  if (radiiOption) {
    radiiOption.disabled = isRef;
  }
  if (isRef && baseFilletModeInput.value === "radii") {
    baseFilletModeInput.value = "radius";
  }

  const mode = baseFilletModeInput.value;
  baseFilletRadiusField.hidden = mode !== "radius";
  baseFilletRadiiEditor.hidden = mode !== "radii";

  if (mode === "none") {
    baseFilletStatus.textContent = "无倒角";
    baseFilletRadiiShell.dataset.status = "idle";
    return;
  }
  if (mode === "radius") {
    baseFilletStatus.textContent = isRef ? "统一半径 · ref + offset" : "统一半径";
    baseFilletRadiiShell.dataset.status = "idle";
    return;
  }
  handleBaseFilletRadiiInput();
}

function readBaseFillet(expectedVertexCount, allowRadii) {
  const mode = baseFilletModeInput.value;
  if (mode === "none") {
    return { ok: true, value: null };
  }
  if (mode === "radius") {
    if (!baseFilletRadiusInput.value.trim()) {
      return { ok: true, value: null };
    }
    const radius = readFiniteNumber(baseFilletRadiusInput.value);
    if (radius === null || radius < 0) {
      setFieldError("baseFilletRadiusField", "radius 必须是非负有限数值。");
      return { ok: false };
    }
    return { ok: true, value: { radius } };
  }
  if (!allowRadii) {
    setFieldError("field-base-fillet-radii", "ref + offset 图形第一版只支持统一半径。");
    return { ok: false };
  }
  const parsed = parseRadiiList(baseFilletRadiiInput.value, expectedVertexCount);
  updateBaseFilletRadiiState(parsed, expectedVertexCount);
  if (!parsed.ok) {
    setFieldError("field-base-fillet-radii", parsed.message);
    return { ok: false };
  }
  return { ok: true, value: { radii: parsed.radii } };
}

function handleVertexListInput() {
  const parsed = parseVertexList(vertexListInput.value);
  updateVertexListState(parsed);
  if (parsed.ok) {
    vertexRows = parsed.vertices.map((point) => [...point]);
  }
  if (baseFilletModeInput.value === "radii") {
    handleBaseFilletRadiiInput();
  }
}

function formatVertexList() {
  const parsed = parseVertexList(vertexListInput.value);
  updateVertexListState(parsed);
  if (!parsed.ok) {
    return;
  }
  vertexRows = parsed.vertices.map((point) => [...point]);
  vertexListInput.value = formatVerticesForList(vertexRows);
  updateVertexListState(parseVertexList(vertexListInput.value));
}

function updateVertexListState(parsed) {
  lastVertexParse = parsed;
  updateVertexLineNumbers();
  vertexListShell.dataset.status = parsed.ok ? "valid" : "invalid";
  if (!parsed.ok) {
    vertexStatus.textContent = "坐标无效";
    return;
  }
  const area = polygonSignedArea(parsed.vertices);
  vertexStatus.textContent = `${parsed.vertices.length} 点 · 逆时针 · 面积 ${formatNumber(Math.abs(area))}`;
}

function updateVertexLineNumbers() {
  const count = Math.max(1, vertexListInput.value.split("\n").length);
  vertexLineNumbers.textContent = Array.from({ length: count }, (_, index) => String(index + 1)).join("\n");
}

function syncVertexLineNumberScroll() {
  vertexLineNumbers.scrollTop = vertexListInput.scrollTop;
}

function formatVerticesForList(vertices) {
  return vertices.map((point) => `${formatNumber(point[0])},${formatNumber(point[1])}`).join("\n");
}

function handleBaseFilletRadiiInput() {
  const parsedVertices = parseVertexList(vertexListInput.value);
  const expectedCount = parsedVertices.ok ? parsedVertices.vertices.length : null;
  const parsed = parseRadiiList(baseFilletRadiiInput.value, expectedCount);
  updateBaseFilletRadiiState(parsed, expectedCount);
}

function formatBaseFilletRadiiList() {
  const parsedVertices = parseVertexList(vertexListInput.value);
  const expectedCount = parsedVertices.ok ? parsedVertices.vertices.length : null;
  const parsed = parseRadiiList(baseFilletRadiiInput.value, expectedCount);
  updateBaseFilletRadiiState(parsed, expectedCount);
  if (!parsed.ok) {
    return;
  }
  baseFilletRadiiInput.value = formatRadiiForList(parsed.radii);
  updateBaseFilletRadiiState(parseRadiiList(baseFilletRadiiInput.value, expectedCount), expectedCount);
}

function updateBaseFilletRadiiState(parsed, expectedCount) {
  lastBaseFilletRadiiParse = parsed;
  baseFilletRadiiShell.dataset.status = parsed.ok ? "valid" : "invalid";
  if (!parsed.ok) {
    baseFilletStatus.textContent = "逐角半径无效";
    return;
  }
  if (expectedCount === null) {
    baseFilletStatus.textContent = `${parsed.radii.length} 个半径 · 等待合法顶点`;
    return;
  }
  baseFilletStatus.textContent = `${parsed.radii.length} 个半径 · 匹配 ${expectedCount} 个顶点`;
}

function formatRadiiForList(radii) {
  return radii.map((radius) => formatNumber(radius)).join(", ");
}

function parseVertexList(text) {
  const raw = text.trim();
  if (!raw) {
    return { ok: false, message: "vertices 不能为空。", vertices: [] };
  }
  const parsed = raw.startsWith("[") ? parseYamlStyleVertices(raw) : parseDelimitedVertices(raw);
  if (!parsed.ok) {
    return parsed;
  }
  return validateParsedVertices(parsed.vertices);
}

function parseRadiiList(text, expectedCount) {
  const raw = text.trim();
  if (!raw) {
    return { ok: false, message: "逐角半径不能为空。", radii: [] };
  }
  const parsed = raw.startsWith("[") ? parseYamlStyleRadii(raw) : parseDelimitedRadii(raw);
  if (!parsed.ok) {
    return parsed;
  }
  if (expectedCount !== null && parsed.radii.length !== expectedCount) {
    return {
      ok: false,
      message: `半径数量为 ${parsed.radii.length}，但顶点数量为 ${expectedCount}。`,
      radii: parsed.radii,
    };
  }
  return parsed;
}

function parseYamlStyleVertices(raw) {
  try {
    const value = JSON.parse(raw);
    if (!Array.isArray(value)) {
      return { ok: false, message: "YAML 数组格式必须是 [[x, y], ...]。", vertices: [] };
    }
    return coerceVertexPairs(value);
  } catch (_error) {
    return { ok: false, message: "YAML 数组格式无法解析，请使用 [[0, 0], [100, 0]]。", vertices: [] };
  }
}

function parseYamlStyleRadii(raw) {
  try {
    const value = JSON.parse(raw);
    if (!Array.isArray(value)) {
      return { ok: false, message: "radii 数组格式必须是 [1, 2, 0, 3]。", radii: [] };
    }
    return coerceRadii(value);
  } catch (_error) {
    return { ok: false, message: "radii 数组格式无法解析，请使用 [1, 2, 0, 3]。", radii: [] };
  }
}

function parseDelimitedVertices(raw) {
  // TODO: 后续加入更智能的格式识别，例如脚本输出中的括号、空格表格和 CSV 块。
  const normalized = raw
    .replace(/[，]/g, ",")
    .replace(/[；]/g, ";")
    .replace(/[：]/g, ":")
    .replace(/\r/g, "\n")
    .replace(/[;:]/g, "\n");
  const rows = normalized.split("\n").map((line) => line.trim()).filter(Boolean);
  const pairs = [];
  for (const [index, row] of rows.entries()) {
    const parts = row.split(",").map((part) => part.trim()).filter((part) => part !== "");
    if (parts.length !== 2) {
      return { ok: false, message: `第 ${index + 1} 行必须是 x,y。`, vertices: [] };
    }
    const x = readFiniteNumber(parts[0]);
    const y = readFiniteNumber(parts[1]);
    if (x === null || y === null) {
      return { ok: false, message: `第 ${index + 1} 行包含非数字坐标。`, vertices: [] };
    }
    pairs.push([x, y]);
  }
  return { ok: true, vertices: pairs };
}

function parseDelimitedRadii(raw) {
  const normalized = raw
    .replace(/[，]/g, ",")
    .replace(/[；]/g, ";")
    .replace(/\r/g, "\n")
    .replace(/[,;]/g, "\n");
  const values = normalized.split(/\s+/).map((part) => part.trim()).filter(Boolean);
  return coerceRadii(values);
}

function coerceVertexPairs(value) {
  const pairs = [];
  for (const [index, point] of value.entries()) {
    if (!Array.isArray(point) || point.length !== 2) {
      return { ok: false, message: `第 ${index + 1} 个点必须是 [x, y]。`, vertices: [] };
    }
    const x = readFiniteNumber(point[0]);
    const y = readFiniteNumber(point[1]);
    if (x === null || y === null) {
      return { ok: false, message: `第 ${index + 1} 个点包含非数字坐标。`, vertices: [] };
    }
    pairs.push([x, y]);
  }
  return { ok: true, vertices: pairs };
}

function coerceRadii(value) {
  const radii = [];
  for (const [index, rawRadius] of value.entries()) {
    const radius = readFiniteNumber(rawRadius);
    if (radius === null) {
      return { ok: false, message: `第 ${index + 1} 个半径不是有效数字。`, radii: [] };
    }
    if (radius < 0) {
      return { ok: false, message: `第 ${index + 1} 个半径不能为负数。`, radii: [] };
    }
    radii.push(radius);
  }
  return { ok: true, radii };
}

function validateParsedVertices(vertices) {
  if (vertices.length < 3) {
    return { ok: false, message: "vertices 至少需要 3 个点。", vertices };
  }
  if (pointsEqual(vertices[0], vertices[vertices.length - 1])) {
    return { ok: false, message: "首尾点重复。GDS 多边形会自动闭合，不要重复输入第一个点。", vertices };
  }
  const area = polygonSignedArea(vertices);
  if (Math.abs(area) <= 1e-9) {
    return { ok: false, message: "坐标面积为 0，请检查是否共线或点顺序错误。", vertices };
  }
  if (area < 0) {
    return { ok: false, message: "当前点序为顺时针。请反转点顺序后再应用。", vertices };
  }
  return { ok: true, vertices };
}

function polygonSignedArea(vertices) {
  let area = 0;
  for (let index = 0; index < vertices.length; index += 1) {
    const current = vertices[index];
    const next = vertices[(index + 1) % vertices.length];
    area += current[0] * next[1] - next[0] * current[1];
  }
  return area / 2;
}

function pointsEqual(left, right) {
  return Math.abs(left[0] - right[0]) <= 1e-9 && Math.abs(left[1] - right[1]) <= 1e-9;
}

function renderRingsFilletMode() {
  const enabled = ringsFilletModeInput.value === "per_ring";
  ringsFilletTableWrap.hidden = !enabled;
  if (enabled) {
    renderRingsFilletRows(readInteger(ringsCountInput.value) || 1);
  }
}

function renderRingsFilletRows(count) {
  ringsFilletTable.replaceChildren();
  while (ringsFilletRows.length < count) {
    ringsFilletRows.push({ inner: "", outer: "" });
  }
  for (let index = 0; index < count; index += 1) {
    const row = ringsFilletRows[index] || { inner: "", outer: "" };
    const node = document.createElement("div");
    node.className = "ring-fillet-row";
    node.innerHTML = `
      <span class="row-index">Ring ${index}</span>
      <label>inner <input class="input ring-inner" data-kind="number" type="number" min="0" step="0.1" value="${escapeAttribute(row.inner)}"></label>
      <label>outer <input class="input ring-outer" data-kind="number" type="number" min="0" step="0.1" value="${escapeAttribute(row.outer)}"></label>
    `;
    ringsFilletTable.appendChild(node);
  }
}

function syncRingsFilletRowsFromInputs() {
  ringsFilletRows = [...ringsFilletTable.querySelectorAll(".ring-fillet-row")].map((row) => ({
    inner: row.querySelector(".ring-inner").value,
    outer: row.querySelector(".ring-outer").value,
  }));
}

function markRingFilletRowError(index) {
  const row = ringsFilletTable.querySelectorAll(".ring-fillet-row")[index];
  if (row) {
    row.dataset.error = "true";
  }
}

function applySameRingsFillet() {
  syncRingsFilletRowsFromInputs();
  const first = ringsFilletRows[0] || { inner: "", outer: "" };
  const count = readInteger(ringsCountInput.value) || 1;
  ringsFilletRows = Array.from({ length: count }, () => ({ ...first }));
  renderRingsFilletRows(count);
}

async function openYaml() {
  if (guardBusy()) {
    return;
  }
  if (isDirty() && !window.confirm("丢弃当前未保存修改并打开新 YAML？")) {
    setStatus("已取消打开。");
    return;
  }
  setBusy(true, "打开 YAML", FILE_DIALOG_TIMEOUT_MS + REQUEST_TIMEOUT_MS + BUSY_WATCHDOG_GRACE_MS);
  try {
    const data = await postJson("/api/yaml/open", {}, { timeoutMs: FILE_DIALOG_TIMEOUT_MS });
    if (!data.ok) {
      setStatus(data.canceled ? "已取消打开。" : "打开失败。");
      renderApiErrors(data.errors || []);
      return;
    }
    const parsed = await postJson("/api/parse", { yaml_text: data.yaml_text });
    if (!parsed.ok) {
      renderApiErrors(parsed.errors || []);
      setStatus("导入失败：YAML 不符合 v2 协议。");
      return;
    }
    state.formDraft = parsedConfigToDraft(parsed.parsed_config);
    state.importedGdsOutput = parsed.parsed_config.gds?.output || null;
    state.generatedYamlText = parsed.canonical_yaml;
    state.lastSavedOrLoadedYamlText = parsed.canonical_yaml;
    state.currentYamlPathLabel = data.path_label;
    state.yamlStatus = "valid";
    pushMessage(`YAML 已打开：${data.path_label}`, true);
    render();
    await previewSvg();
  } catch (error) {
    handleRequestError(error, "打开失败。");
  } finally {
    setBusy(false);
  }
}

async function validateYaml() {
  if (guardBusy()) {
    return;
  }
  setBusy(true, "校验", VALIDATION_TIMEOUT_MS + BUSY_WATCHDOG_GRACE_MS);
  try {
    const data = await postJson("/api/validate", { yaml_text: state.generatedYamlText }, { timeoutMs: VALIDATION_TIMEOUT_MS });
    if (data.ok) {
      pushMessage(`校验通过，${data.shape_count} 个 shape。`, true);
      setStatus("校验通过。");
    } else {
      renderApiErrors(data.errors);
      setStatus(`校验失败：${data.errors.length} 个错误。`);
    }
  } catch (error) {
    handleRequestError(error, "校验失败。");
  } finally {
    setBusy(false);
  }
}

async function saveYaml() {
  if (guardBusy()) {
    return;
  }
  await writeWithPathChoice({
    kind: "yaml",
    suggestedName: "config.yaml",
    endpoint: "/api/yaml/save",
    successMessage: (data) => `YAML 已保存：${data.path_label}`,
    afterSuccess: () => {
      state.lastSavedOrLoadedYamlText = state.generatedYamlText;
    },
  });
}

async function exportGds() {
  if (guardBusy()) {
    return;
  }
  await writeWithPathChoice({
    kind: "gds",
    suggestedName: "layout.gds",
    endpoint: "/api/export/gds",
    successMessage: (data) => `GDS 已导出：${data.path_label}（${data.region_count} 个 region）`,
    afterSuccess: () => {
      exportState.textContent = "GDS 已导出";
      exportState.dataset.state = "ready";
    },
  });
}

async function writeWithPathChoice({ kind, suggestedName, endpoint, successMessage, afterSuccess }) {
  const isGds = kind === "gds";
  const writeTimeout = isGds ? EXPORT_TIMEOUT_MS : REQUEST_TIMEOUT_MS;
  setBusy(
    true,
    kind === "yaml" ? "选择 YAML 保存位置" : "选择 GDS 保存位置",
    FILE_DIALOG_TIMEOUT_MS + writeTimeout + BUSY_WATCHDOG_GRACE_MS,
  );
  try {
    const choice = await postJson(
      "/api/file/choose-save",
      { kind, suggested_name: suggestedName },
      { timeoutMs: FILE_DIALOG_TIMEOUT_MS },
    );
    if (!choice.ok) {
      setStatus(choice.canceled ? "已取消。" : "无法选择保存位置。");
      renderApiErrors(choice.errors || []);
      return;
    }
    const force = choice.exists ? window.confirm(`覆盖 ${choice.path_label}？`) : false;
    if (choice.exists && !force) {
      setStatus("已取消覆盖。");
      return;
    }
    const data = await postJson(
      endpoint,
      {
        yaml_text: state.generatedYamlText,
        path_token: choice.path_token,
        force,
      },
      { timeoutMs: writeTimeout },
    );
    if (!data.ok) {
      renderApiErrors(data.errors);
      if (hasErrorCode(data, "path_token_expired")) {
        setStatus("保存位置已过期，请重新选择。");
      } else {
        setStatus(kind === "yaml" ? "保存失败。" : "导出失败。");
      }
      return;
    }
    afterSuccess(data);
    pushMessage(successMessage(data), true);
    setStatus(successMessage(data));
    render();
  } catch (error) {
    handleRequestError(error, kind === "yaml" ? "保存失败。" : "导出失败。");
  } finally {
    setBusy(false);
  }
}

async function syncYamlFromDraft({ preview = false, markDirty = true } = {}) {
  state.generatedYamlText = serializeDraftToYaml(state.formDraft);
  state.yamlStatus = "syncing";
  if (markDirty && state.previewStatus === "ready") {
    state.previewStatus = "stale";
  }
  render();
  try {
    const data = await postJson("/api/parse", { yaml_text: state.generatedYamlText });
    if (data.ok) {
      state.generatedYamlText = data.canonical_yaml;
      state.parsedConfig = data.parsed_config;
      state.yamlStatus = "valid";
      if (!markDirty) {
        state.lastSavedOrLoadedYamlText = data.canonical_yaml;
      }
      yamlPreview.value = state.generatedYamlText;
      if (preview) {
        schedulePreview();
      }
    } else {
      state.yamlStatus = "invalid";
      state.previewStatus = "yaml_invalid";
      renderApiErrors(data.errors);
    }
  } catch (error) {
    handleRequestError(error, "YAML 同步失败。");
  } finally {
    render();
  }
}

function schedulePreview() {
  window.clearTimeout(previewDebounceTimer);
  if (state.previewStatus !== "idle") {
    state.previewStatus = "stale";
    render();
  }
  previewDebounceTimer = window.setTimeout(previewSvg, 450);
}

async function previewSvg() {
  if (state.yamlStatus !== "valid") {
    state.previewStatus = "yaml_invalid";
    render();
    return;
  }
  state.previewRequestId += 1;
  const requestId = `preview-${state.previewRequestId}`;
  if (previewController) {
    previewController.abort();
  }
  previewController = new AbortController();
  const controller = previewController;
  const timeout = window.setTimeout(() => controller.abort(), 8000);
  state.previewStatus = "rendering";
  render();
  try {
    const data = await postJson(
      "/api/preview/svg",
      { yaml_text: state.generatedYamlText, request_id: requestId },
      { signal: controller.signal, timeoutMs: 0 },
    );
    if (requestId !== `preview-${state.previewRequestId}`) {
      return;
    }
    if (data.ok) {
      mountSvg(data.svg_text);
      state.previewSvgText = data.svg_text;
      state.previewStatus = "ready";
      setStatus(`预览已更新：${data.region_count} 个 region。`);
      pushMessage(`预览已更新：${data.region_count} 个 region。`, true);
    } else {
      state.previewStatus = "error";
      renderApiErrors(data.errors);
      renderEmptyPreview("预览失败", "修正字段后会自动重试。");
    }
  } catch (error) {
    state.previewStatus = "error";
    handleRequestError(error, error.name === "AbortError" ? "预览超时。" : "预览失败。");
  } finally {
    window.clearTimeout(timeout);
    if (previewController === controller) {
      previewController = null;
    }
    render();
  }
}

function serializeDraftToYaml(draft) {
  const lines = ["schema_version: 2", "global:", "  unit: um", `  dbu: ${formatNumber(draft.global.dbu)}`];
  if (draft.global.precision !== null && draft.global.precision !== undefined && draft.global.precision !== "") {
    lines.push(`  precision: ${formatNumber(draft.global.precision)}`);
  }
  lines.push("gds:", `  top_cell: ${yamlScalar(draft.gds.top_cell || "TOP")}`);
  if (state.importedGdsOutput) {
    lines.push(`  output: ${yamlScalar(state.importedGdsOutput)}`);
  }
  lines.push("shapes:");
  for (const shape of draft.shapes) {
    lines.push(`  - type: ${shape.type}`);
    lines.push(`    sid: ${shape.sid}`);
    lines.push(`    name: ${yamlScalar(shape.name)}`);
    lines.push(`    layer: [${shape.layer[0]}, ${shape.layer[1]}]`);
    lines.push("    source:");
    if (shape.source.vertices) {
      lines.push(`      vertices: [${shape.source.vertices.map((point) => `[${formatNumber(point[0])}, ${formatNumber(point[1])}]`).join(", ")}]`);
    } else {
      lines.push(`      ref: ${shape.source.ref}`);
      if (shape.source.offset !== null && shape.source.offset !== undefined) {
        lines.push(`      offset: ${formatNumber(shape.source.offset)}`);
      }
    }
    appendFilletYaml(lines, shape);
    if (shape.type === "via") {
      lines.push("    offsets:");
      lines.push(`      inner: ${formatNumber(shape.offsets.inner)}`);
      lines.push(`      outer: ${formatNumber(shape.offsets.outer)}`);
    }
    if (shape.type === "rings") {
      lines.push(`    count: ${shape.count}`);
      lines.push(`    pitch: ${formatNumber(shape.pitch)}`);
      lines.push(`    width: ${formatNumber(shape.width)}`);
    }
  }
  return `${lines.join("\n")}\n`;
}

function appendFilletYaml(lines, shape) {
  if (!shape.fillet) {
    return;
  }
  if (shape.type === "base_shape") {
    if (shape.fillet.radius !== undefined) {
      lines.push("    fillet:");
      lines.push(`      radius: ${formatNumber(shape.fillet.radius)}`);
    } else if (shape.fillet.radii) {
      lines.push("    fillet:");
      lines.push(`      radii: [${shape.fillet.radii.map((radius) => formatNumber(radius)).join(", ")}]`);
    }
  }
  if (shape.type === "via") {
    const parts = [];
    if (shape.fillet.inner) {
      parts.push(["inner", shape.fillet.inner.radius]);
    }
    if (shape.fillet.outer) {
      parts.push(["outer", shape.fillet.outer.radius]);
    }
    if (parts.length) {
      lines.push("    fillet:");
      for (const [key, radius] of parts) {
        lines.push(`      ${key}: { radius: ${formatNumber(radius)} }`);
      }
    }
  }
  if (shape.type === "rings" && shape.fillet.rings) {
    lines.push("    fillet:");
    lines.push("      rings:");
    for (const ring of shape.fillet.rings.slice(0, shape.count)) {
      if (ring.inner) {
        lines.push("        -");
        lines.push(`          inner: { radius: ${formatNumber(ring.inner.radius)} }`);
        if (ring.outer) {
          lines.push(`          outer: { radius: ${formatNumber(ring.outer.radius)} }`);
        }
      } else if (ring.outer) {
        lines.push("        -");
        lines.push(`          outer: { radius: ${formatNumber(ring.outer.radius)} }`);
      } else {
        lines.push("        - {}");
      }
    }
  }
}

function parsedConfigToDraft(config) {
  return {
    schema_version: 2,
    global: {
      unit: "um",
      dbu: config.global.dbu,
      precision: config.global.precision ?? null,
    },
    gds: {
      top_cell: config.gds?.top_cell || "TOP",
      output: config.gds?.output || null,
    },
    shapes: config.shapes.map((shape) => ({
      ...shape,
      filletMode: shape.type === "rings" && shape.fillet?.rings ? "per_ring" : "none",
    })),
  };
}

function renderBaseOptions(select, currentSid) {
  select.replaceChildren();
  for (const shape of baseShapes()) {
    if (shape.sid === currentSid) {
      continue;
    }
    const option = document.createElement("option");
    option.value = String(shape.sid);
    option.textContent = `#${shape.sid} ${shape.name}`;
    select.appendChild(option);
  }
}

function baseShapes() {
  return state.formDraft.shapes.filter((shape) => shape.type === "base_shape");
}

function findShape(sid) {
  return state.formDraft.shapes.find((shape) => shape.sid === sid);
}

function nextSid() {
  return state.formDraft.shapes.reduce((max, shape) => Math.max(max, shape.sid), -1) + 1;
}

function isDirty() {
  return state.generatedYamlText !== state.lastSavedOrLoadedYamlText;
}

function setMode(mode) {
  state.activeMode = mode;
  render();
}

function setBusy(isBusy, reason = null, timeoutMs = REQUEST_TIMEOUT_MS + BUSY_WATCHDOG_GRACE_MS) {
  window.clearTimeout(busyWatchdogTimer);
  state.busy = isBusy;
  state.busyReason = reason;
  if (reason) {
    setStatus(reason);
  }
  if (isBusy) {
    busyWatchdogTimer = window.setTimeout(() => {
      if (!state.busy) {
        return;
      }
      state.busy = false;
      state.busyReason = null;
      pushMessage(`${reason || "当前操作"}响应超时，界面已解锁。`, false);
      setStatus("操作超时，已恢复界面。");
      render();
    }, timeoutMs);
  }
  render();
}

function guardBusy() {
  if (!state.busy) {
    return false;
  }
  setStatus(`${state.busyReason || "当前操作"}进行中，请稍候。`);
  return true;
}

function setStatus(message) {
  statusText.textContent = message;
}

function previewStateText(status) {
  return {
    idle: "尚未生成预览",
    stale: "预览待更新",
    rendering: "正在生成预览",
    ready: "预览已就绪",
    error: "预览失败",
    yaml_invalid: "YAML 无效",
  }[status] || status;
}

function pushMessage(message, ok = true) {
  state.messages = [{ message, ok }, ...state.messages].slice(0, 4);
}

function renderMessages() {
  messageList.replaceChildren();
  for (const item of state.messages) {
    const node = document.createElement("p");
    node.className = item.ok ? "message ok" : "message";
    node.textContent = item.message;
    messageList.appendChild(node);
  }
}

function renderApiErrors(errors = []) {
  state.messages = errors.map((error) => ({
    message: `${error.code} at ${error.path}: ${error.message}`,
    ok: false,
  }));
  renderMessages();
}

function handleRequestError(error, fallback) {
  const message = error.name === "AbortError"
    ? "请求已取消或超时。"
    : error.name === "TimeoutError" ? "请求超时，界面已解锁。" : error.message || fallback;
  pushMessage(message, false);
  setStatus(error.name === "TimeoutError" ? message : fallback);
  render();
}

async function postJson(path, payload, options = {}) {
  const requestOptions = normalizeRequestOptions(options);
  let didTimeout = false;
  let timeoutId = 0;
  const signals = [];
  if (requestOptions.signal) {
    signals.push(requestOptions.signal);
  }
  if (requestOptions.timeoutMs !== 0) {
    const timeoutController = new AbortController();
    timeoutId = window.setTimeout(() => {
      didTimeout = true;
      timeoutController.abort();
    }, requestOptions.timeoutMs ?? REQUEST_TIMEOUT_MS);
    signals.push(timeoutController.signal);
  }
  const signal = mergeAbortSignals(signals);
  try {
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
  } catch (error) {
    if (didTimeout) {
      const timeoutError = new Error("请求超时。");
      timeoutError.name = "TimeoutError";
      throw timeoutError;
    }
    throw error;
  } finally {
    window.clearTimeout(timeoutId);
  }
}

function normalizeRequestOptions(options) {
  if (options && typeof options.aborted === "boolean" && typeof options.addEventListener === "function") {
    return { signal: options, timeoutMs: REQUEST_TIMEOUT_MS };
  }
  return options || {};
}

function mergeAbortSignals(signals) {
  const activeSignals = signals.filter(Boolean);
  if (activeSignals.length === 0) {
    return undefined;
  }
  if (activeSignals.length === 1) {
    return activeSignals[0];
  }
  const controller = new AbortController();
  const abort = () => controller.abort();
  for (const signal of activeSignals) {
    if (signal.aborted) {
      abort();
      break;
    }
    signal.addEventListener("abort", abort, { once: true });
  }
  return controller.signal;
}

function mountSvg(svgText) {
  previewCanvas.innerHTML = stripXmlDeclaration(svgText);
  const svg = previewCanvas.querySelector("svg");
  if (svg) {
    svg.setAttribute("preserveAspectRatio", "xMidYMid meet");
    svg.style.transformOrigin = "center center";
    svg.style.transform = `scale(${previewScale})`;
  }
}

function renderEmptyPreview(title, detail) {
  previewCanvas.innerHTML = `<div class="empty-preview"><strong>${escapeHtml(title)}</strong><span>${escapeHtml(detail)}</span></div>`;
}

function fitPreview() {
  previewScale = 1;
  applyPreviewScale();
}

function zoomPreview(factor) {
  previewScale = clamp(previewScale * factor, 0.25, 4);
  applyPreviewScale();
}

function applyPreviewScale() {
  const svg = previewCanvas.querySelector("svg");
  if (svg) {
    svg.style.transform = `scale(${previewScale})`;
  }
}

function startSplitDrag(event) {
  splitter.classList.add("dragging");
  splitter.setPointerCapture(event.pointerId);
}

function moveSplitDrag(event) {
  if (!splitter.classList.contains("dragging")) {
    return;
  }
  setSplitterLeft(event.clientX - workspace.getBoundingClientRect().left);
}

function endSplitDrag(event) {
  splitter.classList.remove("dragging");
  splitter.releasePointerCapture(event.pointerId);
}

function handleSplitterKeydown(event) {
  const bounds = workspace.getBoundingClientRect();
  const current = workspace.querySelector(".workspace-pane").getBoundingClientRect().width;
  if (event.key === "Home") {
    setSplitterLeft(bounds.width * 0.35);
  } else if (event.key === "End") {
    setSplitterLeft(bounds.width * 0.65);
  } else if (event.key === "ArrowLeft") {
    setSplitterLeft(current - (event.shiftKey ? 20 : 5));
  } else if (event.key === "ArrowRight") {
    setSplitterLeft(current + (event.shiftKey ? 20 : 5));
  } else {
    return;
  }
  event.preventDefault();
}

function setSplitterLeft(rawLeft) {
  const bounds = workspace.getBoundingClientRect();
  const splitterWidth = 8;
  const min = bounds.width * 0.35;
  const max = bounds.width * 0.65;
  const left = clamp(rawLeft, min, max);
  const right = bounds.width - left - splitterWidth;
  workspace.style.gridTemplateColumns = `${left}px ${splitterWidth}px ${right}px`;
}

function showDialog(dialog) {
  if (dialog.showModal) {
    dialog.showModal();
  } else {
    dialog.setAttribute("open", "");
  }
}

function closeDialog(dialog) {
  if (dialog.close) {
    dialog.close();
  } else {
    dialog.removeAttribute("open");
  }
}

function clearFieldErrors(root) {
  for (const field of root.querySelectorAll(".field")) {
    field.dataset.error = "false";
    const error = field.querySelector(".field-error");
    if (error) {
      error.textContent = "";
    }
  }
}

function setFieldError(fieldId, message) {
  const field = document.getElementById(fieldId);
  if (!field) {
    pushMessage(message, false);
    return;
  }
  field.dataset.error = "true";
  const error = field.querySelector(".field-error");
  if (error) {
    error.textContent = message;
  }
}

function readInteger(value) {
  if (value === "" || value === null || value === undefined) {
    return null;
  }
  const parsed = Number(value);
  return Number.isInteger(parsed) ? parsed : null;
}

function readFiniteNumber(value) {
  if (value === "" || value === null || value === undefined) {
    return null;
  }
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : null;
}

function readRadius(value) {
  const radius = readFiniteNumber(value);
  return radius === null ? null : { radius };
}

function formatNumber(value) {
  return Number(value).toString();
}

function yamlScalar(value) {
  if (/^[A-Za-z0-9_.:/\\-]+$/.test(value)) {
    return value;
  }
  return JSON.stringify(value);
}

function hasErrorCode(data, code) {
  return Boolean(data.errors?.some((error) => error.code === code));
}

function stripXmlDeclaration(svgText) {
  return svgText.replace(/<\?xml[^>]*>\s*/i, "");
}

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;");
}

function escapeAttribute(value) {
  return escapeHtml(value);
}

function clamp(value, min, max) {
  return Math.max(min, Math.min(max, value));
}

function debounce(fn, delay) {
  let timer = 0;
  return (...args) => {
    window.clearTimeout(timer);
    timer = window.setTimeout(() => fn(...args), delay);
  };
}
