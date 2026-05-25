(function () {
    function cloneDeep(obj) {
        return JSON.parse(JSON.stringify(obj || {}));
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
            console.error('[RingsDebug] 更新 JSON 编辑器失败', error);
        }
        if (window.jsonEditor.options) {
            window.jsonEditor.options.onChangeJSON = originalOnChange;
        }
    }

    async function wait(ms) {
        await new Promise(resolve => setTimeout(resolve, ms));
    }

    function summarizeDerivedShape(shape) {
        if (!shape) {
            return null;
        }
        return {
            id: shape.id,
            name: shape.name,
            raw: {
                ring_width: shape.ring_width,
                ring_space: shape.ring_space,
                ring_num: shape.ring_num
            },
            computed: {
                ring_width: shape._computed?.ring_width,
                ring_space: shape._computed?.ring_space,
                ring_num: shape._computed?.ring_num
            }
        };
    }

    window.runRingsInheritanceDebugScenario = async function runRingsInheritanceDebugScenario() {
        console.log('=== Rings Inheritance Debug Scenario ===');

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
                id: 'debug-rings-base',
                type: 'rings',
                name: '调试环阵列-基础',
                vertices: '0,0:10,0:10,10:0,10',
                ring_width: '1,2,3',
                ring_space: '0.5,0.5,0.5',
                ring_num: 3,
                layer: [1, 0],
                fillet: { type: 'none' }
            };

            const derivedShape = {
                id: 'debug-rings-derived',
                type: 'rings',
                name: '调试环阵列-派生',
                layer: [2, 0],
                derivation: {
                    base_shape_id: 'debug-rings-base',
                    derive_type: 'offset',
                    derive_params: {},
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
            let resolvedDerived = LinkagePropertyResolver.resolveShapeProperties(derivedShape);
            window.config.shapes[1] = resolvedDerived;
            renderShapeCard(resolvedDerived, 1);

            if (LinkageOverrideManager?.refreshIndicatorsForShape) {
                LinkageOverrideManager.refreshIndicatorsForShape(resolvedDerived, 1);
            }

            await wait(0);

            const baseRingWidthInput = container?.querySelector('[data-shape-index="0"] [name="shapes[0].ring_width"]');
            const baseRingSpaceInput = container?.querySelector('[data-shape-index="0"] [name="shapes[0].ring_space"]');
            const baseRingNumInput = container?.querySelector('[data-shape-index="0"] [name="shapes[0].ring_num"]');

            if (!baseRingWidthInput || !baseRingSpaceInput || !baseRingNumInput) {
                throw new Error('未找到基础环阵列输入框');
            }

            baseRingWidthInput.value = '5,5,5';
            baseRingWidthInput.dispatchEvent(new Event('change', { bubbles: true }));

            baseRingSpaceInput.value = '1,1,1';
            baseRingSpaceInput.dispatchEvent(new Event('change', { bubbles: true }));

            baseRingNumInput.value = 4;
            baseRingNumInput.dispatchEvent(new Event('change', { bubbles: true }));

            await wait(250);

            resolvedDerived = window.config.shapes[1];
            const summary = summarizeDerivedShape(resolvedDerived);
            console.log('[RingsDebug] 派生形状状态', summary);
            console.log('[RingsDebug] 调试日志条目', testLog);

            window.__linkageLastRingsTestLog = testLog.slice();
            return {
                derivedShape: summary,
                debugLog: testLog.concat()
            };
        } catch (error) {
            console.error('[RingsDebug] 调试场景执行失败', error);
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

    window.exportRingsDebugLog = function exportRingsDebugLog() {
        const log = window.__linkageLastRingsTestLog || window.__linkageDebugLog || [];
        console.table(log);
        return log;
    };

    window.runCircleInheritanceDebugScenario = async function runCircleInheritanceDebugScenario() {
        console.log('=== Circle Inheritance Debug Scenario ===');

        const previousLogRef = window.__linkageDebugLog;
        const previousCounters = window.__linkageDebugCounters ? { ...window.__linkageDebugCounters } : null;
        const testLog = [];
        window.__linkageDebugLog = testLog;
        window.__linkageDebugCounters = {};

        const originalConfig = cloneDeep(window.config || {});
        const originalIndex = typeof currentShapeIndex !== 'undefined' ? currentShapeIndex : 0;
        const container = document.getElementById('shapesContainer');

        function summarizeCircle(shape) {
            if (!shape) return null;
            return {
                id: shape.id,
                name: shape.name,
                raw: {
                    vertices: shape.vertices,
                    metadata: cloneDeep(shape._metadata)
                },
                computed: {
                    vertices: shape._computed?.vertices,
                    metadata: cloneDeep(shape._computed?._metadata || shape._metadata)
                }
            };
        }

        try {
            const baseShape = {
                id: 'debug-circle-base',
                type: 'polygon',
                name: '调试圆形-基础',
                layer: [1, 0],
                vertices: '5.000,0.000:4.619,1.913:3.535,3.536:1.913,4.619:0.000,5.000:-1.913,4.619:-3.536,3.536:-4.619,1.913:-5.000,0.000:-4.619,-1.913:-3.536,-3.536:-1.913,-4.619:0.000,-5.000:1.913,-4.619:3.535,-3.536:4.619,-1.913',
                zoom: 0,
                fillet: { type: 'none' },
                _metadata: {
                    source: 'circle',
                    params: {
                        center_x: 0,
                        center_y: 0,
                        radius: 5,
                        segments: 16
                    }
                }
            };

            const derivedShape = {
                id: 'debug-circle-derived',
                type: 'polygon',
                name: '调试圆形-派生',
                layer: [2, 0],
                derivation: {
                    base_shape_id: 'debug-circle-base',
                    derive_type: 'offset',
                    derive_params: {},
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
            let resolvedDerived = LinkagePropertyResolver.resolveShapeProperties(derivedShape);
            window.config.shapes[1] = resolvedDerived;
            renderShapeCard(resolvedDerived, 1);

            if (LinkageOverrideManager?.refreshIndicatorsForShape) {
                LinkageOverrideManager.refreshIndicatorsForShape(resolvedDerived, 1);
            }

            await wait(120);

            const baseCard = container?.querySelector('[data-shape-index="0"]');
            const circleInputs = baseCard ? {
                centerX: baseCard.querySelector('[name="shapes[0].circle.center_x"]'),
                centerY: baseCard.querySelector('[name="shapes[0].circle.center_y"]'),
                radius: baseCard.querySelector('[name="shapes[0].circle.radius"]'),
                segments: baseCard.querySelector('[name="shapes[0].circle.segments"]')
            } : {};

            if (!circleInputs.centerX || !circleInputs.centerY || !circleInputs.radius || !circleInputs.segments) {
                throw new Error('未找到基础圆形输入框');
            }

            circleInputs.centerX.value = 2.5;
            circleInputs.centerY.value = -1.5;
            circleInputs.radius.value = 8;
            circleInputs.segments.value = 24;

            ['centerX', 'centerY', 'radius', 'segments'].forEach(key => {
                const input = circleInputs[key];
                input.dispatchEvent(new Event('input', { bubbles: true }));
                input.dispatchEvent(new Event('change', { bubbles: true }));
            });

            await wait(400);

            resolvedDerived = window.config.shapes[1];
            const summary = summarizeCircle(resolvedDerived);
            console.log('[CircleDebug] 派生形状状态', summary);
            console.log('[CircleDebug] 调试日志条目', testLog);

            window.__linkageLastCircleTestLog = testLog.slice();
            return {
                derivedShape: summary,
                debugLog: testLog.concat()
            };
        } catch (error) {
            console.error('[CircleDebug] 调试场景执行失败', error);
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

    window.exportCircleDebugLog = function exportCircleDebugLog() {
        const log = window.__linkageLastCircleTestLog || window.__linkageDebugLog || [];
        console.table(log);
        return log;
    };
})();
