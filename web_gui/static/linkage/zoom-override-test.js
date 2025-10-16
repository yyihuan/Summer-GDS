(function () {
    function cloneDeep(obj) {
        return JSON.parse(JSON.stringify(obj || {}));
    }

    function summarizeShape(shape) {
        if (!shape) {
            return null;
        }
        return {
            id: shape.id,
            name: shape.name,
            type: shape.type,
            zoom: shape.zoom,
            deriveZoom: shape.derivation?.derive_params?.zoom,
            overrideZoom: shape.derivation?.overrides?.zoom?.value,
            overrideKeys: shape.derivation ? Object.keys(shape.derivation.overrides || {}) : [],
            computedZoom: shape._computed?.zoom
        };
    }

    function ensureGlobalConfig(data) {
        window.config = data;
        if (typeof config !== 'undefined') {
            config = data;
        }
    }

    function safeSetJSONEditor(newConfig) {
        if (!window.jsonEditor || typeof window.jsonEditor.set !== 'function') {
            return;
        }
        const options = window.jsonEditor.options || {};
        const originalOnChange = options.onChangeJSON;
        if (window.jsonEditor.options) {
            window.jsonEditor.options.onChangeJSON = null;
        }
        try {
            window.jsonEditor.set(newConfig);
        } catch (error) {
            console.error('[ZoomDebug] 更新 JSON 编辑器失败', error);
        }
        if (window.jsonEditor.options) {
            window.jsonEditor.options.onChangeJSON = originalOnChange;
        }
    }

    async function wait(ms) {
        await new Promise(resolve => setTimeout(resolve, ms));
    }

    window.runZoomOverrideDebugScenario = async function runZoomOverrideDebugScenario() {
        console.log('=== Zoom Override Debug Scenario ===');

        const previousLogRef = window.__linkageDebugLog;
        const previousCounters = window.__linkageDebugCounters ? { ...window.__linkageDebugCounters } : null;
        const testLog = [];
        window.__linkageDebugLog = testLog;
        window.__linkageDebugCounters = {};

        const originalConfig = cloneDeep(window.config || {});
        const originalIndex = typeof currentShapeIndex !== 'undefined' ? currentShapeIndex : 0;
        const container = document.getElementById('shapesContainer');

        try {
            const baseShape = {
                id: 'debug-base-shape',
                type: 'polygon',
                name: '调试基础形状',
                layer: [1, 0],
                vertices: '0,0:10,0:10,10:0,10',
                zoom: 0,
                fillet: {
                    type: 'arc',
                    radius: 5,
                    precision: 0.01
                }
            };

            const derivedShape = {
                id: 'debug-derived-shape',
                type: 'polygon',
                name: '调试派生形状',
                layer: [2, 0],
                derivation: {
                    base_shape_id: 'debug-base-shape',
                    derive_type: 'offset',
                    derive_params: { zoom: 0 },
                    created_at: new Date().toISOString(),
                    overrides: {}
                }
            };

            ensureGlobalConfig({
                ...cloneDeep(window.config || {}),
                shapes: [baseShape, derivedShape]
            });

            if (typeof LinkageIdManager !== 'undefined') {
                LinkageIdManager.buildIdMap(window.config.shapes);
            }

            if (container) {
                container.innerHTML = '';
            }

            renderShapeCard(baseShape, 0);

            const resolvedDerived = LinkagePropertyResolver.resolveShapeProperties(derivedShape);
            window.config.shapes[1] = resolvedDerived;
            renderShapeCard(resolvedDerived, 1);

            if (LinkageOverrideManager?.refreshIndicatorsForShape) {
                LinkageOverrideManager.refreshIndicatorsForShape(resolvedDerived, 1);
            }

            await wait(0);

            const zoomInput = container.querySelector('[data-shape-index="1"] [name="shapes[1].zoom"]');
            if (!zoomInput) {
                throw new Error('未找到派生形状缩放输入框');
            }

            zoomInput.focus();
            zoomInput.value = 3;
            zoomInput.dispatchEvent(new Event('change', { bubbles: true }));

            await wait(200);

            const derivedState = summarizeShape(window.config.shapes[1]);
            console.log('[ZoomDebug] 派生形状状态', derivedState);
            console.log('[ZoomDebug] 调试日志条目', testLog);

            window.__linkageLastTestLog = testLog.slice();
            return {
                derivedShape: derivedState,
                debugLog: testLog.concat()
            };
        } catch (error) {
            console.error('[ZoomDebug] 调试场景执行失败', error);
            throw error;
        } finally {
            ensureGlobalConfig(cloneDeep(originalConfig));
            safeSetJSONEditor(window.config);
            if (typeof updateFormFromJSON === 'function') {
                updateFormFromJSON();
            }
            if (typeof updateYAMLPreview === 'function') {
                updateYAMLPreview();
            }
            if (typeof currentShapeIndex !== 'undefined') {
                currentShapeIndex = originalIndex;
            }

            window.__linkageDebugLog = previousLogRef || [];
            window.__linkageDebugCounters = previousCounters || {};
        }
    };

    window.exportZoomDebugLog = function exportZoomDebugLog() {
        const log = window.__linkageLastTestLog || window.__linkageDebugLog || [];
        console.table(log);
        return log;
    };
})();
