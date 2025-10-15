// 阶段4：变更检测与同步机制测试
window.LinkageStage4Test = {

    testData: {
        baseShape: {
            id: 'test-base-shape',
            type: 'polygon',
            name: '基础形状测试',
            vertices: '0,0:10,0:10,10:0,10',
            fillet: {
                type: 'arc',
                radius: 5,
                precision: 0.01
            },
            zoom: 0,
            layer: [1, 0]
        },

        derivedShape: {
            id: 'test-derived-shape',
            type: 'polygon',
            name: '派生形状测试',
            layer: [2, 0],
            derivation: {
                base_shape_id: 'test-base-shape',
                derive_type: 'offset',
                derive_params: {
                    zoom: 1
                },
                created_at: new Date().toISOString(),
                overrides: {}
            }
        }
    },

    setupTestEnvironment() {
        console.log('=== 阶段4测试：设置测试环境 ===');

        this.originalConfig = JSON.parse(JSON.stringify(window.config || { shapes: [] }));
        if (!window.config) {
            window.config = { shapes: [] };
        }

        window.config.shapes = [
            JSON.parse(JSON.stringify(this.testData.baseShape)),
            JSON.parse(JSON.stringify(this.testData.derivedShape))
        ];

        LinkageIdManager.buildIdMap(window.config.shapes);
        console.log('测试环境设置完成', window.config.shapes);
    },

    teardownTestEnvironment() {
        if (this.originalConfig) {
            window.config.shapes = this.originalConfig.shapes || [];
        } else {
            window.config.shapes = [];
        }

        LinkageIdManager.buildIdMap(window.config.shapes);
        console.log('测试环境已清理');
    },

    testChangeDetection() {
        console.log('\n=== 测试1：变更检测准确性 ===');

        const previous = JSON.parse(JSON.stringify(window.config.shapes));
        window.config.shapes[0].fillet.radius = 8;
        window.config.shapes[0].zoom = 2;

        const changes = LinkageSyncManager.detectChanges(previous, window.config.shapes);

        const passed =
            changes.length === 1 &&
            changes[0].shapeId === 'test-base-shape' &&
            changes[0].changedProperties.includes('fillet.radius') &&
            changes[0].changedProperties.includes('zoom');

        console.log('变更检测结果:', changes);
        console.log('测试1结果:', passed ? '✅ 通过' : '❌ 失败');
        return passed;
    },

    testPropertyComparison() {
        console.log('\n=== 测试2：属性比较准确性 ===');

        const shapeA = {
            vertices: '0,0:10,0:10,10:0,10',
            fillet: { type: 'arc', radius: 5 },
            zoom: 0
        };

        const shapeB = {
            vertices: '0,0:10,0:10,10:0,10',
            fillet: { type: 'arc', radius: 7 },
            zoom: 0
        };

        const changed = LinkageSyncManager.detectPropertyChanges(shapeA, shapeB);
        const passed = changed.length === 1 && changed[0] === 'fillet.radius';

        console.log('属性比较结果:', changed);
        console.log('测试2结果:', passed ? '✅ 通过' : '❌ 失败');
        return passed;
    },

    testDerivedShapeSync() {
        console.log('\n=== 测试3：派生形状同步机制 ===');

        const resolved = LinkagePropertyResolver.resolveShapeProperties(window.config.shapes[1]);
        window.config.shapes[1] = resolved;

        window.config.shapes[0].fillet.radius = 9;
        window.config.shapes[0].zoom = 2;
        window.config.shapes[0].vertices = '0,0:20,0:20,20:0,20';

        console.log('同步前派生形状属性:', {
            radius: resolved._computed?.fillet?.radius,
            zoom: resolved._computed?.zoom,
            vertices: resolved._computed?.vertices
        });

        LinkageSyncManager.syncDerivedShapes('test-base-shape', ['fillet.radius', 'zoom', 'vertices']);

        const afterSync = LinkagePropertyResolver.resolveShapeProperties(window.config.shapes[1]);
        const summary = {
            radius: afterSync._computed?.fillet?.radius,
            zoom: afterSync._computed?.zoom,
            vertices: afterSync._computed?.vertices
        };

        console.log('同步后派生形状属性:', summary);

        const expected = {
            radius: window.config.shapes[0].fillet.radius,
            zoom: window.config.shapes[0].zoom,
            vertices: window.config.shapes[0].vertices
        };

        const passed =
            summary.radius === expected.radius &&
            summary.zoom === expected.zoom &&
            summary.vertices === expected.vertices;

        console.log('测试3结果:', passed ? '✅ 通过' : '❌ 失败');
        return passed;
    },

    testOverrideSkipSync() {
        console.log('\n=== 测试4：覆盖属性跳过同步 ===');

        window.config.shapes[1].derivation.overrides = {
            'fillet.radius': {
                value: 15,
                overridden: true,
                overridden_at: new Date().toISOString(),
                reason: 'user_manual_edit'
            }
        };

        const resolved = LinkagePropertyResolver.resolveShapeProperties(window.config.shapes[1]);
        window.config.shapes[1] = resolved;
        console.log('设置覆盖后的半径:', resolved._computed?.fillet?.radius);

        window.config.shapes[0].fillet.radius = 20;
        LinkageSyncManager.syncDerivedShapes('test-base-shape', ['fillet.radius']);

        const afterSync = LinkagePropertyResolver.resolveShapeProperties(window.config.shapes[1]);
        const passed = afterSync._computed?.fillet?.radius === 15;

        console.log('同步后的半径:', afterSync._computed?.fillet?.radius);
        console.log('测试4结果:', passed ? '✅ 通过' : '❌ 失败');
        return passed;
    },

    testSyncPerformance() {
        console.log('\n=== 测试5：性能测试 ===');

        const baseShape = JSON.parse(JSON.stringify(this.testData.baseShape));
        const shapes = [baseShape];

        for (let i = 0; i < 10; i += 1) {
            shapes.push({
                id: `test-derived-${i}`,
                type: 'polygon',
                name: `派生形状${i}`,
                layer: [i + 2, 0],
                derivation: {
                    base_shape_id: baseShape.id,
                    derive_type: 'offset',
                    derive_params: { zoom: i + 1 },
                    created_at: new Date().toISOString(),
                    overrides: {}
                }
            });
        }

        window.config.shapes = shapes;
        LinkageIdManager.buildIdMap(window.config.shapes);
        window.config.shapes = window.config.shapes.map(shape => LinkagePropertyResolver.resolveShapeProperties(shape));

        const start = performance.now();
        LinkageSyncManager.syncDerivedShapes(baseShape.id, ['fillet.radius', 'zoom']);
        const duration = performance.now() - start;

        const passed = duration < 50;
        console.log(`10个派生形状同步耗时: ${duration.toFixed(2)}ms`);
        console.log('测试5结果:', passed ? '✅ 通过' : '❌ 失败');

        return { passed, duration };
    },

    testSilentJSONUpdate() {
        console.log('\n=== 测试6：JSON编辑器静默更新 ===');

        let changeTriggered = false;

        window.jsonEditor = {
            options: {
                onChangeJSON: () => {
                    changeTriggered = true;
                    console.log('JSON编辑器 onChange 事件被触发');
                }
            },
            set: () => {
                console.log('JSON编辑器 set 方法被调用');
            }
        };

        window.updateYAMLPreview = () => {
            console.log('YAML 预览更新被调用');
        };

        LinkageSyncManager.updateJSONEditorSilently();

        const passed = changeTriggered === false;
        console.log('测试6结果:', passed ? '✅ 通过' : '❌ 失败');

        delete window.jsonEditor;
        delete window.updateYAMLPreview;
        return passed;
    },

    runAllTests() {
        console.log('🚀 开始阶段4功能测试');
        console.log('测试目标：变更检测与同步机制');

        this.setupTestEnvironment();

        const results = {
            test1: this.testChangeDetection(),
            test2: this.testPropertyComparison(),
            test3: this.testDerivedShapeSync(),
            test4: this.testOverrideSkipSync(),
            test5: this.testSyncPerformance(),
            test6: this.testSilentJSONUpdate()
        };

        this.teardownTestEnvironment();

        const allPassed = Object.values(results).every(item => typeof item === 'boolean' ? item : item.passed);

        console.log('\n📊 测试结果汇总:');
        console.log('测试1 - 变更检测准确性:', results.test1 ? '✅' : '❌');
        console.log('测试2 - 属性比较准确性:', results.test2 ? '✅' : '❌');
        console.log('测试3 - 派生形状同步:', results.test3 ? '✅' : '❌');
        console.log('测试4 - 覆盖属性跳过:', results.test4 ? '✅' : '❌');
        console.log('测试5 - 性能测试:', results.test5.passed ? '✅' : '❌', `(${results.test5.duration.toFixed(2)}ms)`);
        console.log('测试6 - 静默更新:', results.test6 ? '✅' : '❌');

        console.log('\n🎯 总体结果:', allPassed ? '✅ 全部通过' : '❌ 部分失败');

        return {
            allPassed,
            details: results
        };
    },

    validateStage4Requirements() {
        console.log('\n📋 阶段4验证点检查:');

        const result = this.runAllTests();
        const validation = {
            changeDetection: result.details.test1 && result.details.test2,
            syncMechanism: result.details.test3 && result.details.test4,
            noRecursion: result.details.test6,
            performance: result.details.test5.passed
        };

        Object.entries(validation).forEach(([key, value]) => {
            console.log(`${key}: ${value ? '✅' : '❌'}`);
        });

        const passed = Object.values(validation).every(Boolean);
        console.log(`\n🎯 阶段4验证结果: ${passed ? '✅ 全部通过' : '❌ 需要修复'}`);

        return {
            passed,
            details: validation
        };
    }
};

window.testStage4 = () => window.LinkageStage4Test.runAllTests();
window.validateStage4 = () => window.LinkageStage4Test.validateStage4Requirements();
