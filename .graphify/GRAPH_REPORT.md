# Graph Report - .  (2026-08-11)

## Corpus Check
- 266 files · ~165,911 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 1220 nodes · 2363 edges · 58 communities detected
- Extraction: 95% EXTRACTED · 5% INFERRED · 0% AMBIGUOUS · INFERRED: 108 edges (avg confidence: 0.5)
- Token cost: 0 input · 0 output
- Edge kinds: calls: 796 · contains: 792 · ON_BRANCH: 223 · method: 151 · uses: 108 · MODIFIES: 103 · PARENT_OF: 100 · rationale_for: 67 · inherits: 15 · imports_from: 8


## Input Scope
- Requested: auto
- Resolved: committed (source: default-auto)
- Included files: 266 · Candidates: 294
- Excluded: 1 untracked · 19689 ignored · 0 sensitive · 1 missing committed
- Recommendation: Use --scope all or graphify.yaml inputs.corpus for a knowledge-base folder.

## Graph Freshness
- Built from Git commit: `5b9d54d`
- Compare this hash to `git rev-parse HEAD` before trusting freshness-sensitive graph output.
## God Nodes (most connected - your core abstractions)
1. `Frame` - 22 edges
2. `MainWindow` - 21 edges
3. `QtSaveFileDialog` - 19 edges
4. `GuiSession` - 19 edges
5. `openShapeDialog()` - 19 edges
6. `BundleProbe` - 18 edges
7. `render()` - 17 edges
8. `FakeSaveDialog` - 17 edges
9. `ShutdownCoordinator` - 15 edges
10. `FakeDialog` - 15 edges

## Surprising Connections (you probably didn't know these)
- `FakeDialog` --uses--> `QtSaveFileDialog`  [INFERRED]
  tests/gui/qt_unit/test_qt_dialog.py → src/summer_gds/gui/qt_dialog.py
- `ExportOptions` --uses--> `ConfigError`  [INFERRED]
  src/summer_gds/app/service.py → src/summer_gds/schema/errors.py
- `ExportResult` --uses--> `ConfigError`  [INFERRED]
  src/summer_gds/app/service.py → src/summer_gds/schema/errors.py
- `创建或获取图层索引                  参数:             layer_info: 图层信息元组 (layer_num, dataty` --uses--> `LayerManager`  [INFERRED]
  summer_gds_v1/gds_utils/cell.py → summer_gds_v1/gds_utils/layer.py
- `向单元格添加区域                  参数:             region: Region 对象             layer_in` --uses--> `LayerManager`  [INFERRED]
  summer_gds_v1/gds_utils/cell.py → summer_gds_v1/gds_utils/layer.py

## Communities

### Community 0 - "Community 0"
Cohesion: 0.02
Nodes (118): addBaseButton, addRingsButton, addViaButton, app, applySameRingsFilletButton, baseEditor, baseFilletModeInput, baseFilletRadiiEditor (+110 more)

### Community 1 - "Community 1"
Cohesion: 0.06
Nodes (100): codex/qt-desktop-shell, main, refactor/simplified, 0044d01 WIP: add MVP schema foundation, 00a8758 添加人工测试指南和快速测试脚本, 03c3e9d 功能:添加全局精度控制, 03c60b4 功能:完成qt gui内gds下载, 096c6a4 添加圆形输入功能 (+92 more)

### Community 2 - "Community 2"
Cohesion: 0.06
Nodes (21): activate_bundle_probe(), _assert_regular_control_file(), BundleProbe, ProbeActivationError, ProbeFileDialog, _origin(), OriginInterceptor, RestrictedPage (+13 more)

### Community 3 - "Community 3"
Cohesion: 0.06
Nodes (21): LogBridge, LogEvent, QueueLogHandler, 日志桥接工具。  该模块在阶段 2 中用于将 Python logging 的 WARNING+ 级别消息 转换为线程安全的事件队列，供 Qt 或 CLI 侧消, 将日志消息写入 queue.Queue 的 handler。, _build_parser(), LaunchOptions, _load_config() (+13 more)

### Community 4 - "Community 4"
Cohesion: 0.09
Nodes (19): Frame, 根据顶点的凹凸性自适应应用不同的倒角半径                  Args:             convex_radius (float or, 生成偏移后的新Frame                  参数:             width: 偏移宽度，正值为外扩，负值为内缩（当前版本仅支持外扩）, 初始化 Frame          参数:             vertices: 顶点列表 [(x1,y1), (x2,y2), ...], 封装 KLayout Region 对象的类，用于创建和操作多边形区域, 获取内部的 KLayout Region 对象                  返回:             db.Region: KLayout Regi, 从 Frame 对象创建多个环          参数:             initial_frame: 初始 Frame 对象, 布尔减法运算                  参数:             other: 另一个 Region 对象 (+11 more)

### Community 5 - "Community 5"
Cohesion: 0.06
Nodes (20): Cell, 获取图层索引                  参数:             layer_info: 图层信息元组 (layer_num, datatype), 创建或获取图层索引                  参数:             layer_info: 图层信息元组 (layer_num, dataty, 向单元格添加区域                  参数:             region: Region 对象             layer_in, 获取图层管理器                  返回:             LayerManager: 图层管理器对象, 初始化 Cell 对象                  参数:             kdb_cell: KLayout Cell 对象, GDS, 初始化 GDS 对象          参数:             input_file: GDS 输入文件路径，如果为None则创建新的布局 (+12 more)

### Community 6 - "Community 6"
Cohesion: 0.10
Nodes (39): applySameRingsFillet(), applyShapeDialog(), closeShapeDialog(), coerceRadii(), computeViaOuterConcentricSpec(), createEmptyRingFilletRow(), formatRadiiForList(), formatRingsConcentricRadiiList() (+31 more)

### Community 7 - "Community 7"
Cohesion: 0.12
Nodes (27): addShape(), bindPrecisionListToggleEvents(), bindRadiusListToggleEvents(), bindShapeCardEvents(), config, confirmAddVia(), escapeHtml(), fillShapeFormValues() (+19 more)

### Community 8 - "Community 8"
Cohesion: 0.10
Nodes (11): _DialogRequest, _name_filter(), QtSaveFileDialog, Synchronous worker-facing adapter backed by GUI-thread asynchronous dialogs., QObject, FakeDialog, _pump_until(), test_second_dialog_returns_busy_without_queueing() (+3 more)

### Community 9 - "Community 9"
Cohesion: 0.14
Nodes (13): _atomic_write_text(), _dialog_error_response(), GuiSession, _parse_error_response(), PathToken, _preview_error_response(), secretsafe_token(), _simple_error_response() (+5 more)

### Community 10 - "Community 10"
Cohesion: 0.16
Nodes (28): deleteShape(), exportGds(), guardBusy(), handleRequestError(), hasErrorCode(), initialize(), isDirty(), mergeAbortSignals() (+20 more)

### Community 11 - "Community 11"
Cohesion: 0.08
Nodes (24): calc_segments_for_arc_span(), _ensure_float_list(), normalize_arc_fillet_config(), 根据 via 场景的半径配置拆分出适合 polygon2ring 使用的配置三元组。, 将倒角半径/精度列表按顶点顺序反转，可用于顶点序列逆转时保持对应关系。     不修改入参，返回拷贝。, 根据弦高（圆弧到 chord 中点的距离）限制计算分段数。      Args:         radius: 圆弧半径，要求 > 0         arc, resolve_via_fillet_configs(), sync_reverse_radius_list() (+16 more)

### Community 12 - "Community 12"
Cohesion: 0.08
Nodes (10): Application services., 393e838 feat: promote v2 to project root as summer-gds v2.0, Geometry pipeline primitives., baseShape, derivedShape, Protocol and geometry models., YAML v2 schema parsing., VertexValidator (+2 more)

### Community 13 - "Community 13"
Cohesion: 0.16
Nodes (22): HTTPRedirectHandler, _atomic_json(), _atomic_text(), _business_probe(), _clean_environment(), _executable(), _json_request(), main() (+14 more)

### Community 14 - "Community 14"
Cohesion: 0.29
Nodes (18): choose_path(), FakeSaveDialog, make_client(), post_json(), test_choose_save_cancel_is_explicit(), test_choose_save_returns_token_without_writing(), test_dialog_failure_is_not_reported_as_cancel(), test_force_retry_can_reuse_valid_token() (+10 more)

### Community 15 - "Community 15"
Cohesion: 0.12
Nodes (22): addOffsetCopy(), addShape(), applyGlobalSettings(), baseFilletMode(), baseShapes(), clearFieldErrors(), closeDialog(), closeGlobalDialog() (+14 more)

### Community 16 - "Community 16"
Cohesion: 0.28
Nodes (20): _contains_yaml_alias_or_anchor(), _depth(), _finite_float(), _is_int(), _parse_count(), _parse_gds(), _parse_global(), _parse_layer() (+12 more)

### Community 17 - "Community 17"
Cohesion: 0.14
Nodes (8): FakeServerHandle, FakeWebviewModule, FakeWindow, test_launch_desktop_forces_edgechromium_on_windows(), test_loopback_server_serves_gui_and_stops(), test_pywebview_open_dialog_maps_yaml(), test_pywebview_save_dialog_maps_yaml_and_cancel(), test_pywebview_save_dialog_returns_selected_path()

### Community 18 - "Community 18"
Cohesion: 0.14
Nodes (19): appendFilletYaml(), coerceVertexPairs(), formatNumber(), formatRadiusSpecInline(), formatRingsVertexList(), formatVertexList(), formatVerticesForList(), parseDelimitedVertices() (+11 more)

### Community 19 - "Community 19"
Cohesion: 0.20
Nodes (13): _import_webview(), launch_desktop(), _log(), _log_webview_runtime(), LoopbackServerHandle, main(), _public_start_kwargs(), Write crash log and attempt a GUI error dialog so --windowed isn't silent. (+5 more)

### Community 20 - "Community 20"
Cohesion: 0.18
Nodes (8): Exception, DialogFailure, NullSaveFileDialog, SaveFileDialog, Protocol, ConfigError, ConfigIssue, issue()

### Community 21 - "Community 21"
Cohesion: 0.29
Nodes (13): _load_verifier(), test_bundle_inventory_accepts_windows_klayout_gds_plugin_name(), test_bundle_inventory_requires_klayout_gds_plugin(), test_bundle_verifier_sends_json_content_type_for_api_requests(), test_bundle_verifier_token_pattern_matches_the_bootstrap_assignment(), test_windows_bundle_inventory_requires_matching_plugin_copies(), test_windows_bundle_inventory_uses_pyinstaller_runtime_payload_root(), test_windows_bundle_verifier_clears_readonly_before_delete_retry() (+5 more)

### Community 22 - "Community 22"
Cohesion: 0.25
Nodes (12): test_cli_export_png_dry_run_writes_nothing(), test_cli_preview_and_generate_shortcuts(), test_cli_validate_json_error(), test_cli_validate_success(), write_config(), _build_parser(), _exit_code_for_config_error(), main() (+4 more)

### Community 23 - "Community 23"
Cohesion: 0.26
Nodes (10): detectAndSync(), detectChanges(), enhanceUpdateJSONFromForm(), forceRecalculateShape(), getConfig(), syncAllDerivedShapes(), syncDerivedShapes(), updateFormValues() (+2 more)

### Community 24 - "Community 24"
Cohesion: 0.18
Nodes (13): BaseShapeSpec, ConfigSpec, GdsSpec, GlobalSpec, RadiusSpec, RingFilletSpec, RingsFilletSpec, RingsSpec (+5 more)

### Community 25 - "Community 25"
Cohesion: 0.23
Nodes (9): ensure_metadata_compatibility(), ensure_string_values(), generate_gds(), load_config(), process_metadata(), 确保元数据兼容性，为没有元数据的配置添加默认元数据, 确保ring_width和ring_space保持为字符串类型, save_config() (+1 more)

### Community 26 - "Community 26"
Cohesion: 0.29
Nodes (12): assert_code(), parse(), test_rejects_dbu_and_precision_mismatch(), test_rejects_duplicate_sid(), test_rejects_forward_ref_and_ref_to_non_base_shape(), test_rejects_invalid_rings_count_pitch_width_and_fillet_length(), test_rejects_non_finite_and_bool_numbers(), test_rejects_non_mapping_or_deep_yaml() (+4 more)

### Community 27 - "Community 27"
Cohesion: 0.17
Nodes (5): atomic_temp_output_path(), Return an adjacent temporary name while preserving the writer's suffix., 1a85671 docs: refresh Graphify evidence for Qt shell, 5b9d54d test: decode static frontend fixtures as UTF-8, 7ef43db feat: migrate desktop shell to QtWebEngine

### Community 28 - "Community 28"
Cohesion: 0.36
Nodes (11): apply_fillet(), _arc_points(), _arc_points_for_corner(), _expand_radii(), _interior_angle(), _minor_sweep(), _point_from_unit(), _segments_for_arc() (+3 more)

### Community 29 - "Community 29"
Cohesion: 0.38
Nodes (10): make_client(), post_json(), test_api_rejects_missing_session_token(), test_api_returns_503_app_closing_after_gate_shutdown(), test_parse_reports_contract_errors_without_throwing(), test_parse_returns_normalized_config_and_field_map(), test_preview_svg_reports_geometry_errors(), test_preview_svg_returns_svg_text_and_removes_temp_files() (+2 more)

### Community 30 - "Community 30"
Cohesion: 0.26
Nodes (7): addOverrideDetection(), createOverride(), enhanceFormEventBinding(), handleUserOverride(), removeOverride(), syncCardDerivation(), updateInheritanceIndicator()

### Community 31 - "Community 31"
Cohesion: 0.39
Nodes (10): printTestSummary(), recordTest(), runAllTests(), testBasicPropertyExtraction(), testBatchShapeResolution(), testDeriveParamsApplication(), testEdgeCases(), testInheritanceResolution() (+2 more)

### Community 32 - "Community 32"
Cohesion: 0.32
Nodes (11): runAllTests(), setupTestEnvironment(), teardownTestEnvironment(), testChangeDetection(), testDerivedShapeSync(), testOverrideSkipSync(), testPropertyComparison(), testRingPropertiesInheritance() (+3 more)

### Community 33 - "Community 33"
Cohesion: 0.35
Nodes (9): assert_code(), test_force_allows_overwrite(), test_gds_dry_run_requires_final_gds_output_path(), test_output_path_errors_are_reported_before_writing(), test_png_and_gds_exports_write_files(), test_png_dry_run_uses_cli_out_and_writes_nothing(), test_svg_export_uses_image_renderer(), test_validate_config_file_does_not_require_gds_output() (+1 more)

### Community 34 - "Community 34"
Cohesion: 0.31
Nodes (9): cross(), has_consecutive_duplicate_points(), is_simple_polygon(), normalize_counterclockwise(), _on_segment(), _orientation(), points_equal(), segments_intersect() (+1 more)

### Community 35 - "Community 35"
Cohesion: 0.33
Nodes (8): canonical_yaml(), config_to_dict(), _fillet_to_dict(), _path_to_string(), _radius_to_dict(), _ring_fillet_to_dict(), _shape_to_dict(), _source_to_dict()

### Community 36 - "Community 36"
Cohesion: 0.51
Nodes (9): _execute_base_shape(), execute_config(), _execute_rings(), _execute_via(), _offset_boundary(), _resolve_ref_boundary(), _resolve_shape_source_boundary(), _resolve_source_boundary() (+1 more)

### Community 37 - "Community 37"
Cohesion: 0.38
Nodes (9): bbox_tuple(), run_config(), test_rings_each_ring_inner_and_outer_fillet_are_independent(), test_rings_output_count_and_offsets_match_protocol(), test_rings_with_per_ring_fillet_increases_boundary_point_count(), test_rings_without_fillet_keeps_outer_boundaries_unfilleted(), test_via_inner_and_outer_fillet_are_independent(), test_via_inner_bigger_than_outer_reports_empty_boolean() (+1 more)

### Community 39 - "Community 39"
Cohesion: 0.24
Nodes (3): comparePropertyValues(), getPropertyTypeInfo(), normalizePropertyValue()

### Community 40 - "Community 40"
Cohesion: 0.24
Nodes (3): checkStage1ValidationPoints(), generateReport(), runAllTests()

### Community 41 - "Community 41"
Cohesion: 0.51
Nodes (9): createStubIndicator(), createStubInput(), runAllTests(), setupConfig(), setupDOM(), testIndicatorUpdates(), testOverrideRemoval(), testSystemUpdateSkipping() (+1 more)

### Community 42 - "Community 42"
Cohesion: 0.39
Nodes (8): export_artifact(), ExportOptions, ExportResult, _resolve_output_path(), _temp_output_path(), validate_config_file(), _validate_output_path(), ImageOutputConfig

### Community 43 - "Community 43"
Cohesion: 0.28
Nodes (3): applyDerivedParams(), extractComputedProps(), resolveShapeProperties()

### Community 44 - "Community 44"
Cohesion: 0.36
Nodes (8): generateSuggestions(), generateValidationReport(), validateDerivationConfig(), validateOverrideConfig(), validateReferenceIntegrity(), validateShapeConfig(), validateShapesConfig(), validateSystemCompatibility()

### Community 45 - "Community 45"
Cohesion: 0.50
Nodes (8): BoundaryMetadata, BoundaryObject, GeometryContext, RegionMetadata, RegionObject, ShapeResult, LayerSpec, Point

### Community 46 - "Community 46"
Cohesion: 0.39
Nodes (8): format_vertices(), main(), make_control_list(), _normalize_line(), parse_args(), process_file(), 读取文本坐标文件并按 find_polygon_corners 的格式解析。, read_coordinate_file()

### Community 47 - "Community 47"
Cohesion: 0.22
Nodes (9): actionButton(), baseFilletSummary(), escapeAttribute(), escapeHtml(), renderEmptyPreview(), renderRingFilletSideControls(), renderShapeList(), shapeCard() (+1 more)

### Community 48 - "Community 48"
Cohesion: 0.28
Nodes (9): baseFilletRadiiExpectedCount(), findShape(), formatBaseFilletRadiiList(), handleBaseFilletModeChange(), handleBaseFilletRadiiInput(), handleVertexListInput(), renderBaseFilletMode(), seedBaseFilletRadiiCount() (+1 more)

### Community 49 - "Community 49"
Cohesion: 0.39
Nodes (8): format_vertices(), main(), make_control_list(), _normalize_line(), parse_args(), process_file(), 读取文本坐标文件并按 find_polygon_corners 的格式解析。, read_coordinate_file()

### Community 50 - "Community 50"
Cohesion: 0.57
Nodes (7): base_yaml(), run_config(), test_base_fillet_outputs_more_points_but_canonical_boundary_stays_prefillet(), test_base_ref_offset_happens_before_fillet_and_updates_canonical_boundary(), test_base_shape_accepts_common_convex_concave_sharp_and_obtuse_inputs(), test_rejects_positive_fillet_on_collinear_corner(), test_rejects_self_intersecting_hourglass_topology()

### Community 52 - "Community 52"
Cohesion: 0.33
Nodes (2): cloneDeep(), summarizeCircle()

### Community 54 - "Community 54"
Cohesion: 0.29
Nodes (7): applyPreviewScale(), clamp(), fitPreview(), handleSplitterKeydown(), moveSplitDrag(), setSplitterLeft(), zoomPreview()

### Community 55 - "Community 55"
Cohesion: 0.47
Nodes (4): boundary_to_region(), dbu_to_um(), region_to_boundary(), um_to_dbu()

### Community 56 - "Community 56"
Cohesion: 0.40
Nodes (2): detectCircularDependency(), findShapeById()

### Community 60 - "Community 60"
Cohesion: 0.60
Nodes (4): calculate_md5(), compare_gds_files(), main(), 对比基准 GDS 文件和当前生成的 GDS 文件          Args:         baseline_dir: 基准文件目录         cur

### Community 61 - "Community 61"
Cohesion: 0.70
Nodes (4): _combined_bbox(), _metadata_for_format(), render_image(), _stable_color()

### Community 62 - "Community 62"
Cohesion: 0.67
Nodes (3): fillet_gds(), main(), 对GDS文件中的所有多边形进行倒角处理      参数:         input_file: 输入GDS文件路径         output_file:

### Community 64 - "Community 64"
Cohesion: 1.00
Nodes (2): main(), _revision()

## Knowledge Gaps
- **174 isolated node(s):** `Remove a verifier temporary tree, tolerating Windows' copied DLL attributes.`, `Return the directory exposed to a frozen application as ``_MEIPASS``.`, `Summer GDS v2 implementation.`, `Application services.`, `Return an adjacent temporary name while preserving the writer's suffix.` (+169 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **Thin community `Community 52`** (2 nodes): `cloneDeep()`, `summarizeCircle()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 56`** (2 nodes): `detectCircularDependency()`, `findShapeById()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 64`** (2 nodes): `main()`, `_revision()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `MainWindow` connect `Community 3` to `Community 2`?**
  _High betweenness centrality (0.028) - this node is a cross-community bridge._
- **What connects `Remove a verifier temporary tree, tolerating Windows' copied DLL attributes.`, `Return the directory exposed to a frozen application as ``_MEIPASS``.`, `Summer GDS v2 implementation.` to the rest of the system?**
  _174 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `Community 0` be split into smaller, more focused modules?**
  _Cohesion score 0.016 - nodes in this community are weakly interconnected._
- **Should `Community 1` be split into smaller, more focused modules?**
  _Cohesion score 0.06323232323232324 - nodes in this community are weakly interconnected._
- **Should `Community 2` be split into smaller, more focused modules?**
  _Cohesion score 0.05803571428571429 - nodes in this community are weakly interconnected._
- **Should `Community 3` be split into smaller, more focused modules?**
  _Cohesion score 0.06464646464646465 - nodes in this community are weakly interconnected._
- **Should `Community 4` be split into smaller, more focused modules?**
  _Cohesion score 0.09175377468060394 - nodes in this community are weakly interconnected._