// 阶段5：用户覆盖机制测试
if (typeof document === 'undefined') {
    window.document = {};
}

if (typeof window.updateJSONFromForm !== 'function') {
    window.updateJSONFromForm = () => {};
}

if (typeof window.showAlert !== 'function') {
    window.showAlert = () => {};
}

window.LinkageStage5Test = {

    createStubInput(initialValue = '') {
        const listeners = {};
        return {
            value: initialValue,
            type: 'text',
            tagName: 'INPUT',
            dataset: {},
            addEventListener(event, handler) {
                listeners[event] = listeners[event] || [];
                listeners[event].push(handler);
            },
            trigger(event) {
                (listeners[event] || []).forEach(handler => handler({ target: this }));
            }
        };
    },

    createStubIndicator() {
        return {
            textContent: '',
            classList: {
                classes: new Set(['badge', 'badge-secondary']),
                add(cls) { this.classes.add(cls); },
                remove(cls) { this.classes.delete(cls); },
                contains(cls) { return this.classes.has(cls); }
            }
        };
    },

    setupDOM(shape, shapeIndex) {
        const zoomInput = this.createStubInput(String(shape._computed?.zoom ?? shape.zoom ?? ''));
        zoomInput.type = 'number';

        const radiusInput = this.createStubInput(String(shape._computed?.fillet?.radius ?? shape.fillet?.radius ?? ''));
        radiusInput.type = 'number';

        const verticesInput = this.createStubInput(shape._computed?.vertices ?? shape.vertices ?? '');

        const indicatorZoom = this.createStubIndicator();
        const indicatorRadius = this.createStubIndicator();
        const indicatorVertices = this.createStubIndicator();

        const card = {
            dataset: {},
            attributes: {},
            querySelector(selector) {
                const map = {
                    [`[name="shapes[${shapeIndex}].zoom"]`]: zoomInput,
                    [`[name="shapes[${shapeIndex}].fillet.radius"]`]: radiusInput,
                    [`[name="shapes[${shapeIndex}].vertices"]`]: verticesInput,
                    [`[data-inheritance-indicator="zoom"]`]: indicatorZoom,
                    [`[data-inheritance-indicator="fillet.radius"]`]: indicatorRadius,
                    [`[data-inheritance-indicator="vertices"]`]: indicatorVertices
                };
                return map[selector] || null;
            },
            setAttribute(name, value) {
                this.attributes[name] = value;
            },
            getAttribute(name) {
                return this.attributes[name];
            }
        };

        document._cards = document._cards || {};
        document._cards[shapeIndex] = card;

        document.querySelector = (selector) => {
            const match = selector.match(/\[data-shape-index="(\d+)"\]/);
            if (match) {
                return document._cards[match[1]] || null;
            }
            const indicatorMatch = selector.match(/\[data-inheritance-indicator="([\w\.]+)"\]/);
            if (indicatorMatch) {
                const prop = indicatorMatch[1];
                if (prop === 'zoom') return indicatorZoom;
                if (prop === 'fillet.radius') return indicatorRadius;
                if (prop === 'vertices') return indicatorVertices;
            }
            return null;
        };

        return { zoomInput, radiusInput, verticesInput, indicatorZoom, indicatorRadius, indicatorVertices, card };
    },

    setupConfig() {
        const baseShape = {
            id: 'test-base',
            name: '基础形状',
            type: 'polygon',
            vertices: '0,0:10,0:10,10:0,10',
            zoom: 0,
            fillet: { type: 'arc', radius: 5 }
        };

        const derivedShape = {
            id: 'test-derived',
            name: '派生形状',
            type: 'polygon',
            layer: [2, 0],
            derivation: {
                base_shape_id: 'test-base',
                derive_type: 'offset',
                derive_params: { zoom: 1 },
                overrides: {}
            }
        };

        window.config = { shapes: [baseShape, derivedShape] };
        LinkageIdManager.buildIdMap(window.config.shapes);
        window.config.shapes = window.config.shapes.map(shape => LinkagePropertyResolver.resolveShapeProperties(shape));
        return window.config.shapes;
    },

    testUserOverrideDetection() {
        console.log('\n=== 阶段5测试1：用户覆盖检测 ===');
        const shapes = this.setupConfig();
        const derived = shapes[1];
        const { zoomInput } = this.setupDOM(derived, 1);

        LinkageOverrideManager.addOverrideDetection(document._cards['1'], derived, 1);

        zoomInput.value = '2';
        zoomInput.trigger('change');

        const override = derived.derivation.overrides?.zoom;
        const passed = override && override.value === 2;
        console.log('覆盖记录:', override);
        console.log('测试1结果:', passed ? '✅ 通过' : '❌ 失败');
        return passed;
    },

    testSystemUpdateSkipping() {
        console.log('\n=== 阶段5测试2：系统更新跳过 ===');
        const shapes = this.setupConfig();
        const derived = shapes[1];
        const { zoomInput } = this.setupDOM(derived, 1);

        LinkageOverrideManager.addOverrideDetection(document._cards['1'], derived, 1);

        LinkageOverrideManager.isSystemUpdate = true;
        zoomInput.value = '3';
        zoomInput.trigger('change');
        LinkageOverrideManager.isSystemUpdate = false;

        const overrideExists = !!derived.derivation.overrides?.zoom;
        console.log('覆盖是否创建:', overrideExists);
        console.log('测试2结果:', !overrideExists ? '✅ 通过' : '❌ 失败');
        return !overrideExists;
    },

    testOverrideRemoval() {
        console.log('\n=== 阶段5测试3：恢复继承 ===');
        const shapes = this.setupConfig();
        const derived = shapes[1];
        const { zoomInput } = this.setupDOM(derived, 1);

        LinkageOverrideManager.addOverrideDetection(document._cards['1'], derived, 1);

        zoomInput.value = '4';
        zoomInput.trigger('change');

        zoomInput.value = '0';
        zoomInput.trigger('change');

        const overrideExists = !!derived.derivation.overrides?.zoom;
        console.log('覆盖是否存在:', overrideExists);
        console.log('测试3结果:', !overrideExists ? '✅ 通过' : '❌ 失败');
        return !overrideExists;
    },

    testIndicatorUpdates() {
        console.log('\n=== 阶段5测试4：继承指示器 ===');
        const shapes = this.setupConfig();
        const derived = shapes[1];
        const { zoomInput, indicatorZoom } = this.setupDOM(derived, 1);

        LinkageOverrideManager.addOverrideDetection(document._cards['1'], derived, 1);

        zoomInput.value = '5';
        zoomInput.trigger('change');

        const overriddenState = indicatorZoom.classList.contains('badge-warning');

        zoomInput.value = '0';
        zoomInput.trigger('change');

        const inheritedState = indicatorZoom.classList.contains('badge-success');

        const passed = overriddenState && inheritedState;
        console.log('指示器状态: ', {
            overriddenState,
            inheritedState
        });
        console.log('测试4结果:', passed ? '✅ 通过' : '❌ 失败');
        return passed;
    },

    runAllTests() {
        console.log('🚀 开始阶段5功能测试');
        console.log('测试目标：用户覆盖检测与记录');

        const results = {
            test1: this.testUserOverrideDetection(),
            test2: this.testSystemUpdateSkipping(),
            test3: this.testOverrideRemoval(),
            test4: this.testIndicatorUpdates()
        };

        const allPassed = Object.values(results).every(Boolean);

        console.log('\n📊 测试结果汇总:');
        console.log('测试1 - 用户覆盖检测:', results.test1 ? '✅' : '❌');
        console.log('测试2 - 系统更新跳过:', results.test2 ? '✅' : '❌');
        console.log('测试3 - 恢复继承:', results.test3 ? '✅' : '❌');
        console.log('测试4 - 指示器更新:', results.test4 ? '✅' : '❌');

        console.log('\n🎯 总体结果:', allPassed ? '✅ 全部通过' : '❌ 部分失败');

        return {
            allPassed,
            details: results
        };
    }
};

window.testStage5 = () => window.LinkageStage5Test.runAllTests();
