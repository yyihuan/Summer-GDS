// 阶段3：属性解析引擎测试套件
window.Stage3Test = {

    // 测试结果存储
    testResults: [],

    // 运行所有测试
    runAllTests() {
        console.log('========================================');
        console.log('开始阶段3属性解析引擎测试');
        console.log('========================================');

        this.testResults = [];

        // 执行所有测试用例
        this.testBasicPropertyExtraction();
        this.testInheritanceResolution();
        this.testOverrideHandling();
        this.testDeriveParamsApplication();
        this.testBatchShapeResolution();
        this.testPerformanceBenchmark();
        this.testEdgeCases();

        // 输出测试结果
        this.printTestSummary();

        return this.testResults;
    },

    // 测试基础属性提取
    testBasicPropertyExtraction() {
        const testShape = {
            id: 'test-basic',
            type: 'polygon',
            name: '基础形状',
            vertices: '0,0:10,0:10,10:0,10',
            fillet: {
                type: 'arc',
                radius: 5,
                precision: 0.01
            },
            zoom: 2,
            layer: [1, 0]
        };

        const resolved = LinkagePropertyResolver.resolveShapeProperties(testShape);

        // 验证非派生形状的处理
        const passed =
            resolved.id === 'test-basic' &&
            resolved._computed.vertices === '0,0:10,0:10,10:0,10' &&
            resolved._computed.fillet.type === 'arc' &&
            resolved._computed.fillet.radius === 5 &&
            resolved._computed.zoom === 2;

        this.recordTest('基础属性提取', passed, {
            expected: '正确提取所有可继承属性到_computed',
            actual: resolved._computed
        });
    },

    // 测试继承解析
    testInheritanceResolution() {
        // 创建基础形状
        const baseShape = {
            id: 'base-shape-inheritance',
            type: 'polygon',
            name: '基础形状',
            vertices: '0,0:20,0:20,20:0,20',
            fillet: {
                type: 'arc',
                radius: 8,
                precision: 0.02
            },
            zoom: 1,
            layer: [1, 0]
        };

        // 创建派生形状
        const derivedShape = {
            id: 'derived-inheritance',
            type: 'polygon',
            name: '派生形状',
            layer: [2, 0],
            derivation: {
                base_shape_id: 'base-shape-inheritance',
                derive_type: 'offset',
                derive_params: {
                    zoom: 3  // 这个会覆盖继承的zoom值
                },
                created_at: new Date().toISOString(),
                overrides: {}
            }
        };

        // 保存原始配置
        const originalShapes = window.config ? [...(window.config.shapes || [])] : [];
        const originalConfig = window.config;

        try {
            // 设置临时配置
            if (!window.config) window.config = {};
            window.config.shapes = [baseShape, derivedShape];

            // 重建ID映射表
            LinkageIdManager.buildIdMap(window.config.shapes);

            // 解析派生形状
            const resolved = LinkagePropertyResolver.resolveShapeProperties(derivedShape);

            // 验证继承和派生参数
            const passed =
                resolved._computed &&
                resolved._computed.vertices === '0,0:20,0:20,20:0,20' &&  // 继承
                resolved._computed.fillet &&
                resolved._computed.fillet.type === 'arc' &&               // 继承
                resolved._computed.fillet.radius === 8 &&                 // 继承
                resolved._computed.zoom === 3;                             // 派生参数覆盖

            this.recordTest('继承解析', passed, {
                expected: '正确继承基础形状属性并应用派生参数',
                actual: resolved._computed || '解析失败',
                baseShape: baseShape,
                derivedShape: derivedShape
            });
        } catch (error) {
            this.recordTest('继承解析', false, {
                expected: '正确继承基础形状属性并应用派生参数',
                actual: `测试异常: ${error.message}`,
                error: error
            });
        } finally {
            // 恢复原始配置
            if (originalConfig) {
                window.config = originalConfig;
                window.config.shapes = originalShapes;
            } else {
                window.config = { shapes: originalShapes };
            }
        }
    },

    // 测试覆盖处理
    testOverrideHandling() {
        const baseShape = {
            id: 'base-override',
            vertices: '0,0:15,0:15,15:0,15',
            fillet: { type: 'arc', radius: 6 },
            zoom: 0
        };

        const derivedShape = {
            id: 'derived-override',
            derivation: {
                base_shape_id: 'base-override',
                derive_type: 'offset',
                overrides: {
                    'fillet.radius': {
                        value: 12,
                        overridden: true,
                        overridden_at: new Date().toISOString(),
                        reason: 'user_manual_edit'
                    },
                    'vertices': {
                        value: '5,5:25,5:25,25:5,25',
                        overridden: true,
                        overridden_at: new Date().toISOString(),
                        reason: 'user_manual_edit'
                    }
                }
            }
        };

        // 保存原始配置
        const originalShapes = window.config ? [...(window.config.shapes || [])] : [];
        const originalConfig = window.config;

        try {
            // 设置临时配置
            if (!window.config) window.config = {};
            window.config.shapes = [baseShape, derivedShape];

            // 重建ID映射表
            LinkageIdManager.buildIdMap(window.config.shapes);

            const resolved = LinkagePropertyResolver.resolveShapeProperties(derivedShape);

            // 验证覆盖值和继承值
            const passed =
                resolved._computed &&
                resolved._computed.fillet &&
                resolved._computed.fillet.radius === 12 &&                    // 覆盖值
                resolved._computed.vertices === '5,5:25,5:25,25:5,25' &&      // 覆盖值
                resolved._computed.fillet.type === 'arc' &&                   // 继承值
                resolved._computed.zoom === 0;                                 // 继承值

            this.recordTest('覆盖处理', passed, {
                expected: '正确应用覆盖值，保持未覆盖属性的继承',
                actual: resolved._computed || '解析失败'
            });
        } catch (error) {
            this.recordTest('覆盖处理', false, {
                expected: '正确应用覆盖值，保持未覆盖属性的继承',
                actual: `测试异常: ${error.message}`,
                error: error
            });
        } finally {
            // 恢复原始配置
            if (originalConfig) {
                window.config = originalConfig;
                window.config.shapes = originalShapes;
            } else {
                window.config = { shapes: originalShapes };
            }
        }
    },

    // 测试派生参数应用
    testDeriveParamsApplication() {
        const baseShape = {
            id: 'base-params',
            vertices: '0,0:10,0:10,10:0,10',
            zoom: 1,
            fillet: { radius: 3 }
        };

        const derivedShape = {
            id: 'derived-params',
            derivation: {
                base_shape_id: 'base-params',
                derive_type: 'offset',
                derive_params: {
                    zoom: 5,  // 派生参数
                    custom_param: 'test_value'
                },
                overrides: {
                    'fillet.radius': {
                        value: 8,
                        overridden: true
                    }
                }
            }
        };

        // 保存原始配置
        const originalShapes = window.config ? [...(window.config.shapes || [])] : [];
        const originalConfig = window.config;

        try {
            if (!window.config) window.config = {};
            window.config.shapes = [baseShape, derivedShape];

            // 重建ID映射表
            LinkageIdManager.buildIdMap(window.config.shapes);

            const resolved = LinkagePropertyResolver.resolveShapeProperties(derivedShape);

            // 验证派生参数优先级：派生参数 > 覆盖值 > 继承值
            const passed =
                resolved._computed &&
                resolved._computed.zoom === 5 &&                    // 派生参数
                resolved._computed.fillet &&
                resolved._computed.fillet.radius === 8 &&           // 覆盖值
                resolved._computed.vertices === '0,0:10,0:10,10:0,10' && // 继承值
                resolved._computed.custom_param === 'test_value';   // 自定义派生参数

            this.recordTest('派生参数应用', passed, {
                expected: '派生参数正确覆盖继承值和覆盖值',
                actual: resolved._computed || '解析失败'
            });
        } catch (error) {
            this.recordTest('派生参数应用', false, {
                expected: '派生参数正确覆盖继承值和覆盖值',
                actual: `测试异常: ${error.message}`,
                error: error
            });
        } finally {
            // 恢复原始配置
            if (originalConfig) {
                window.config = originalConfig;
                window.config.shapes = originalShapes;
            } else {
                window.config = { shapes: originalShapes };
            }
        }
    },

    // 测试批量解析
    testBatchShapeResolution() {
        const shapes = [
            {
                id: 'batch-base-1',
                vertices: '0,0:10,0:10,10:0,10',
                fillet: { radius: 2 }
            },
            {
                id: 'batch-base-2',
                vertices: '0,0:20,0:20,20:0,20',
                fillet: { radius: 4 }
            },
            {
                id: 'batch-derived-1',
                derivation: {
                    base_shape_id: 'batch-base-1',
                    derive_params: { zoom: 2 }
                }
            },
            {
                id: 'batch-derived-2',
                derivation: {
                    base_shape_id: 'batch-base-2',
                    overrides: {
                        'fillet.radius': { value: 6, overridden: true }
                    }
                }
            }
        ];

        // 保存原始配置
        const originalShapes = window.config ? [...(window.config.shapes || [])] : [];
        const originalConfig = window.config;

        try {
            // 临时设置配置用于批量解析
            if (!window.config) window.config = {};
            window.config.shapes = shapes;

            const resolved = LinkagePropertyResolver.resolveAllShapes(shapes);

            const passed =
                resolved.length === 4 &&
                resolved[0]._computed &&
                resolved[0]._computed.fillet &&
                resolved[0]._computed.fillet.radius === 2 &&      // 基础形状1
                resolved[1]._computed &&
                resolved[1]._computed.fillet &&
                resolved[1]._computed.fillet.radius === 4 &&      // 基础形状2
                resolved[2]._computed &&
                resolved[2]._computed.fillet &&
                resolved[2]._computed.fillet.radius === 2 &&      // 派生1继承
                resolved[2]._computed.zoom === 2 &&                // 派生1参数
                resolved[3]._computed &&
                resolved[3]._computed.fillet &&
                resolved[3]._computed.fillet.radius === 6 &&      // 派生2覆盖
                resolved[3]._computed.vertices === '0,0:20,0:20,20:0,20'; // 派生2继承

            this.recordTest('批量解析', passed, {
                expected: '正确批量解析所有形状',
                actual: resolved.map(s => ({ id: s.id, computed: s._computed || '解析失败' }))
            });
        } catch (error) {
            this.recordTest('批量解析', false, {
                expected: '正确批量解析所有形状',
                actual: `测试异常: ${error.message}`,
                error: error
            });
        } finally {
            // 恢复原始配置
            if (originalConfig) {
                window.config = originalConfig;
                window.config.shapes = originalShapes;
            } else {
                window.config = { shapes: originalShapes };
            }
        }
    },

    // 性能基准测试
    testPerformanceBenchmark() {
        // 创建大量测试数据
        const shapes = [];
        const baseCount = 10;
        const derivedPerBase = 5;

        // 创建基础形状
        for (let i = 0; i < baseCount; i++) {
            shapes.push({
                id: `perf-base-${i}`,
                vertices: `${i},${i}:${i+10},${i}:${i+10},${i+10}:${i},${i+10}`,
                fillet: { type: 'arc', radius: i + 1 },
                zoom: i
            });
        }

        // 创建派生形状
        for (let i = 0; i < baseCount; i++) {
            for (let j = 0; j < derivedPerBase; j++) {
                shapes.push({
                    id: `perf-derived-${i}-${j}`,
                    derivation: {
                        base_shape_id: `perf-base-${i}`,
                        derive_params: { zoom: i + j + 1 },
                        overrides: j % 2 === 0 ? {
                            'fillet.radius': {
                                value: (i + j) * 2,
                                overridden: true
                            }
                        } : {}
                    }
                });
            }
        }

        console.log(`性能测试：${shapes.length}个形状 (${baseCount}基础 + ${baseCount * derivedPerBase}派生)`);

        // 执行性能测试
        const startTime = performance.now();
        const resolved = LinkagePropertyResolver.resolveAllShapes(shapes);
        const endTime = performance.now();

        const duration = endTime - startTime;
        const averagePerShape = duration / shapes.length;
        const passed = duration < 100; // 100ms阈值

        this.recordTest('性能基准', passed, {
            expected: '50个形状解析时间 < 100ms',
            actual: {
                totalShapes: shapes.length,
                duration: `${duration.toFixed(2)}ms`,
                averagePerShape: `${averagePerShape.toFixed(2)}ms/形状`,
                threshold: '100ms'
            }
        });

        console.log(`性能结果: ${duration.toFixed(2)}ms 总计, ${averagePerShape.toFixed(2)}ms/形状`);
    },

    // 边界情况测试
    testEdgeCases() {
        // 保存原始配置
        const originalShapes = window.config ? [...(window.config.shapes || [])] : [];
        const originalConfig = window.config;

        const edgeCases = [
            {
                name: '缺失基础形状',
                shape: {
                    id: 'missing-base',
                    derivation: { base_shape_id: 'non-existent' }
                },
                expected: '返回原形状，记录错误日志'
            },
            {
                name: '空的覆盖配置',
                shape: {
                    id: 'empty-overrides',
                    derivation: {
                        base_shape_id: 'test-base',
                        overrides: {}
                    }
                },
                expected: '正常处理空覆盖'
            },
            {
                name: '无效属性路径',
                shape: {
                    id: 'invalid-path',
                    derivation: {
                        base_shape_id: 'test-base',
                        overrides: {
                            'invalid.deep.path': { value: 'test', overridden: true }
                        }
                    }
                },
                expected: '安全处理无效路径'
            }
        ];

        let passedCount = 0;

        try {
            // 创建一个基础形状用于测试
            if (!window.config) window.config = {};
            window.config.shapes = [{
                id: 'test-base',
                vertices: '0,0:5,0:5,5:0,5',
                fillet: { radius: 1 }
            }];

            // 重建ID映射表
            LinkageIdManager.buildIdMap(window.config.shapes);

            edgeCases.forEach(testCase => {
                try {
                    const resolved = LinkagePropertyResolver.resolveShapeProperties(testCase.shape);
                    // 如果没有抛出异常，认为测试通过
                    passedCount++;
                    console.log(`✓ 边界情况测试通过: ${testCase.name}`);
                } catch (error) {
                    console.log(`✗ 边界情况测试失败: ${testCase.name} - ${error.message}`);
                }
            });

            const passed = passedCount === edgeCases.length;

            this.recordTest('边界情况处理', passed, {
                expected: '所有边界情况都能安全处理',
                actual: `${passedCount}/${edgeCases.length} 通过`
            });
        } catch (error) {
            this.recordTest('边界情况处理', false, {
                expected: '所有边界情况都能安全处理',
                actual: `测试异常: ${error.message}`,
                error: error
            });
        } finally {
            // 恢复原始配置
            if (originalConfig) {
                window.config = originalConfig;
                window.config.shapes = originalShapes;
            } else {
                window.config = { shapes: originalShapes };
            }
        }
    },

    // 记录测试结果
    recordTest(testName, passed, details) {
        const result = {
            name: testName,
            passed: passed,
            details: details,
            timestamp: new Date().toISOString()
        };

        this.testResults.push(result);

        const status = passed ? '✓ 通过' : '✗ 失败';
        const color = passed ? 'color: green' : 'color: red';

        console.log(`%c${status}: ${testName}`, color);
        if (!passed || LinkageCore.debug) {
            console.log('  详情:', details);
        }
    },

    // 打印测试总结
    printTestSummary() {
        const totalTests = this.testResults.length;
        const passedTests = this.testResults.filter(r => r.passed).length;
        const failedTests = totalTests - passedTests;

        console.log('========================================');
        console.log('阶段3测试总结');
        console.log('========================================');
        console.log(`总测试数: ${totalTests}`);
        console.log(`通过: ${passedTests}`);
        console.log(`失败: ${failedTests}`);
        console.log(`成功率: ${((passedTests / totalTests) * 100).toFixed(1)}%`);

        if (failedTests > 0) {
            console.log('\n失败的测试:');
            this.testResults
                .filter(r => !r.passed)
                .forEach(r => {
                    console.log(`- ${r.name}: ${JSON.stringify(r.details)}`);
                });
        }

        console.log('========================================');

        return {
            total: totalTests,
            passed: passedTests,
            failed: failedTests,
            successRate: (passedTests / totalTests) * 100
        };
    },

    // 辅助函数：检查必需模块
    checkRequiredModules() {
        const requiredModules = ['LinkageCore', 'LinkageIdManager', 'LinkagePropertyResolver'];
        const missing = requiredModules.filter(module => typeof window[module] === 'undefined');

        if (missing.length > 0) {
            console.error('缺少必需模块:', missing);
            return false;
        }

        console.log('所有必需模块已加载');
        return true;
    }
};

// 自动检查模块并提供运行提示
document.addEventListener('DOMContentLoaded', () => {
    setTimeout(() => {
        if (Stage3Test.checkRequiredModules()) {
            console.log('阶段3测试已准备就绪。运行 Stage3Test.runAllTests() 开始测试。');
        }
    }, 1000);
});