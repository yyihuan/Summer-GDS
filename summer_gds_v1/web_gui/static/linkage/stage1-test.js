// 阶段1测试用例和验证流程
window.LinkageStage1Test = {

    // 测试结果存储
    testResults: {},

    // 运行所有阶段1测试
    runAllTests() {
        console.log('=== 开始阶段1联动系统基础架构测试 ===');

        const tests = [
            { name: 'JS文件加载测试', func: this.testJSFileLoading },
            { name: '核心工具函数测试', func: this.testCoreUtilities },
            { name: 'ID管理系统测试', func: this.testIdManager },
            { name: '属性路径工具测试', func: this.testPropertyPath },
            { name: '验证工具测试', func: this.testValidator },
            { name: '集成兼容性测试', func: this.testIntegration }
        ];

        const results = [];

        tests.forEach(test => {
            console.log(`\n--- 运行测试: ${test.name} ---`);
            try {
                const result = test.func.call(this);
                results.push({
                    name: test.name,
                    passed: result.passed,
                    details: result.details,
                    error: null
                });
                console.log(`✅ ${test.name}: ${result.passed ? '通过' : '失败'}`);
                if (result.details) {
                    console.log(`   详情: ${result.details}`);
                }
            } catch (error) {
                results.push({
                    name: test.name,
                    passed: false,
                    details: null,
                    error: error.message
                });
                console.error(`❌ ${test.name}: 异常 - ${error.message}`);
            }
        });

        this.testResults = results;
        this.generateReport();

        return results;
    },

    // 测试1: JS文件加载
    testJSFileLoading() {
        const requiredModules = [
            'LinkageCore',
            'LinkageIdManager',
            'LinkagePropertyPath',
            'LinkageValidator'
        ];

        const missing = requiredModules.filter(module => typeof window[module] === 'undefined');

        return {
            passed: missing.length === 0,
            details: missing.length > 0 ? `缺失模块: ${missing.join(', ')}` : '所有模块已正确加载'
        };
    },

    // 测试2: 核心工具函数
    testCoreUtilities() {
        const tests = [
            // 测试属性访问
            () => {
                const obj = { a: { b: 5 } };
                const result = LinkageCore.getNestedProperty(obj, 'a.b');
                console.assert(result === 5, 'getNestedProperty 失败');
                return result === 5;
            },

            // 测试属性设置
            () => {
                const obj = {};
                LinkageCore.setNestedProperty(obj, 'a.b.c', 10);
                const result = obj.a?.b?.c === 10;
                console.assert(result, 'setNestedProperty 失败');
                return result;
            },

            // 测试深度比较
            () => {
                const obj1 = { x: 1, y: { z: 2 } };
                const obj2 = { x: 1, y: { z: 2 } };
                const obj3 = { x: 1, y: { z: 3 } };

                const test1 = LinkageCore.deepEqual(obj1, obj2);
                const test2 = !LinkageCore.deepEqual(obj1, obj3);

                console.assert(test1, 'deepEqual 相等测试失败');
                console.assert(test2, 'deepEqual 不等测试失败');

                return test1 && test2;
            },

            // 测试日志功能
            () => {
                // 临时捕获控制台输出
                const originalLog = console.info;
                let logCalled = false;
                console.info = (...args) => {
                    logCalled = true;
                    originalLog(...args);
                };

                LinkageCore.log('info', '测试日志消息');
                console.info = originalLog;

                return logCalled;
            }
        ];

        const results = tests.map(test => test());
        const allPassed = results.every(r => r);

        return {
            passed: allPassed,
            details: `${results.filter(r => r).length}/${results.length} 项核心功能测试通过`
        };
    },

    // 测试3: ID管理系统
    testIdManager() {
        const tests = [
            // 测试ID生成
            () => {
                const id1 = LinkageIdManager.generateShapeId();
                const id2 = LinkageIdManager.generateShapeId();

                const test1 = typeof id1 === 'string' && id1.startsWith('shape_');
                const test2 = id1 !== id2; // 确保唯一性

                console.assert(test1, 'ID格式测试失败');
                console.assert(test2, 'ID唯一性测试失败');

                return test1 && test2;
            },

            // 测试ID映射构建
            () => {
                const shapes = [
                    { name: '形状1' },
                    { name: '形状2', id: 'existing-id' },
                    { name: '形状3' }
                ];

                LinkageIdManager.buildIdMap(shapes);

                // 检查是否为所有形状生成了ID
                const hasIds = shapes.every(shape => shape.id);
                // 检查映射表大小
                const mapSize = LinkageIdManager.idMap.size === 3;
                // 检查现有ID是否保持
                const preservedId = shapes[1].id === 'existing-id';

                console.assert(hasIds, 'ID生成测试失败');
                console.assert(mapSize, 'ID映射表大小测试失败');
                console.assert(preservedId, '现有ID保持测试失败');

                return hasIds && mapSize && preservedId;
            },

            // 测试形状查找
            () => {
                const shapes = [
                    { id: 'test-id-1', name: '测试形状1' },
                    { id: 'test-id-2', name: '测试形状2' }
                ];

                LinkageIdManager.buildIdMap(shapes);

                const found1 = LinkageIdManager.findShapeById('test-id-1', shapes);
                const found2 = LinkageIdManager.findShapeById('non-existent', shapes);

                const test1 = found1 && found1.name === '测试形状1';
                const test2 = found2 === null;

                console.assert(test1, '形状查找测试失败');
                console.assert(test2, '不存在形状查找测试失败');

                return test1 && test2;
            },

            // 测试循环依赖检测
            () => {
                const shapes = [
                    { id: 'shape-a', derivation: { base_shape_id: 'shape-b' } },
                    { id: 'shape-b', derivation: { base_shape_id: 'shape-c' } },
                    { id: 'shape-c', derivation: { base_shape_id: 'shape-a' } } // 循环
                ];

                LinkageIdManager.buildIdMap(shapes);

                const hasCycle = LinkageIdManager.detectCircularDependency('shape-a', 'shape-b', shapes);
                const noCycle = LinkageIdManager.detectCircularDependency('shape-a', 'shape-d', shapes);

                console.assert(hasCycle, '循环依赖检测失败');
                console.assert(!noCycle, '无循环依赖检测失败');

                return hasCycle && !noCycle;
            }
        ];

        const results = tests.map(test => test());
        const allPassed = results.every(r => r);

        return {
            passed: allPassed,
            details: `${results.filter(r => r).length}/${results.length} 项ID管理功能测试通过`
        };
    },

    // 测试4: 属性路径工具
    testPropertyPath() {
        const tests = [
            // 测试属性路径验证
            () => {
                const valid = LinkagePropertyPath.validatePropertyPath('fillet.radius');
                const invalid = LinkagePropertyPath.validatePropertyPath('invalid.property');

                const test1 = valid.valid === true;
                const test2 = invalid.valid === false;

                console.assert(test1, '有效属性路径验证失败');
                console.assert(test2, '无效属性路径验证失败');

                return test1 && test2;
            },

            // 测试属性值标准化
            () => {
                const num1 = LinkagePropertyPath.normalizePropertyValue('fillet.radius', '5.5');
                const num2 = LinkagePropertyPath.normalizePropertyValue('fillet.radius', 10);
                const str1 = LinkagePropertyPath.normalizePropertyValue('vertices', '0,0:10,10');

                const test1 = num1 === 5.5;
                const test2 = num2 === 10;
                const test3 = str1 === '0,0:10,10';

                console.assert(test1, '数字字符串标准化失败');
                console.assert(test2, '数字标准化失败');
                console.assert(test3, '字符串标准化失败');

                return test1 && test2 && test3;
            },

            // 测试属性值比较
            () => {
                const same1 = LinkagePropertyPath.comparePropertyValues('fillet.radius', 5, '5');
                const same2 = LinkagePropertyPath.comparePropertyValues('vertices', 'test', 'test');
                const diff = LinkagePropertyPath.comparePropertyValues('fillet.radius', 5, 10);

                console.assert(same1, '相同数值比较失败');
                console.assert(same2, '相同字符串比较失败');
                console.assert(!diff, '不同值比较失败');

                return same1 && same2 && !diff;
            },

            // 测试显示名称获取
            () => {
                const name1 = LinkagePropertyPath.getPropertyDisplayName('fillet.radius');
                const name2 = LinkagePropertyPath.getPropertyDisplayName('unknown.property');

                const test1 = name1 === '倒角半径';
                const test2 = name2 === 'unknown.property';

                console.assert(test1, '已知属性显示名称测试失败');
                console.assert(test2, '未知属性显示名称测试失败');

                return test1 && test2;
            }
        ];

        const results = tests.map(test => test());
        const allPassed = results.every(r => r);

        return {
            passed: allPassed,
            details: `${results.filter(r => r).length}/${results.length} 项属性路径功能测试通过`
        };
    },

    // 测试5: 验证工具
    testValidator() {
        const tests = [
            // 测试形状配置验证
            () => {
                const validShape = {
                    type: 'polygon',
                    name: '测试形状',
                    id: 'test-shape-1'
                };

                const invalidShape = {
                    name: '无类型形状'
                    // 缺少 type
                };

                const result1 = LinkageValidator.validateShapeConfig(validShape);
                const result2 = LinkageValidator.validateShapeConfig(invalidShape);

                const test1 = result1.valid === true;
                const test2 = result2.valid === false && result2.errors.some(e => e.includes('type'));

                console.assert(test1, '有效形状配置验证失败');
                console.assert(test2, '无效形状配置验证失败');

                return test1 && test2;
            },

            // 测试派生关系验证
            () => {
                const validDerivation = {
                    base_shape_id: 'base-1',
                    derive_type: 'offset',
                    derive_params: { zoom: 5 }
                };

                const invalidDerivation = {
                    derive_type: 'invalid_type'
                    // 缺少 base_shape_id
                };

                const result1 = LinkageValidator.validateDerivationConfig(validDerivation);
                const result2 = LinkageValidator.validateDerivationConfig(invalidDerivation);

                const test1 = result1.valid === true;
                const test2 = result2.valid === false;

                console.assert(test1, '有效派生关系验证失败');
                console.assert(test2, '无效派生关系验证失败');

                return test1 && test2;
            },

            // 测试系统兼容性验证
            () => {
                const result = LinkageValidator.validateSystemCompatibility();

                // 在正常环境下应该通过兼容性检查
                console.assert(result.valid, '系统兼容性验证失败');

                return result.valid;
            }
        ];

        const results = tests.map(test => test());
        const allPassed = results.every(r => r);

        return {
            passed: allPassed,
            details: `${results.filter(r => r).length}/${results.length} 项验证功能测试通过`
        };
    },

    // 测试6: 集成兼容性
    testIntegration() {
        const tests = [
            // 测试模块间协作
            () => {
                // 创建测试形状
                const testShape = {
                    type: 'polygon',
                    name: '集成测试形状',
                    fillet: { type: 'arc', radius: 5 }
                };

                // 使用ID管理器生成ID
                testShape.id = LinkageIdManager.generateShapeId();

                // 使用验证器验证
                const validationResult = LinkageValidator.validateShapeConfig(testShape);

                // 使用属性路径工具
                const filletType = LinkageCore.getNestedProperty(testShape, 'fillet.type');

                const test1 = validationResult.valid;
                const test2 = filletType === 'arc';
                const test3 = typeof testShape.id === 'string';

                console.assert(test1, '集成验证测试失败');
                console.assert(test2, '集成属性访问测试失败');
                console.assert(test3, '集成ID生成测试失败');

                return test1 && test2 && test3;
            },

            // 测试现有功能兼容性
            () => {
                // 检查是否影响现有全局变量
                const hasConfig = typeof window.config !== 'undefined';
                const hasAddShape = typeof window.addShape === 'function';

                // 不强制要求这些函数存在，但如果存在应该仍然可用
                if (hasConfig || hasAddShape) {
                    console.log('检测到现有功能，兼容性良好');
                }

                // 检查关键原型是否被修改
                const arrayPrototypeIntact = Array.prototype.hasOwnProperty('map');
                const objectPrototypeIntact = Object.prototype.hasOwnProperty('toString');

                console.assert(arrayPrototypeIntact, 'Array原型被破坏');
                console.assert(objectPrototypeIntact, 'Object原型被破坏');

                return arrayPrototypeIntact && objectPrototypeIntact;
            }
        ];

        const results = tests.map(test => test());
        const allPassed = results.every(r => r);

        return {
            passed: allPassed,
            details: `${results.filter(r => r).length}/${results.length} 项集成测试通过`
        };
    },

    // 生成测试报告
    generateReport() {
        const totalTests = this.testResults.length;
        const passedTests = this.testResults.filter(r => r.passed).length;
        const failedTests = totalTests - passedTests;

        console.log('\n=== 阶段1测试报告 ===');
        console.log(`总测试数: ${totalTests}`);
        console.log(`通过: ${passedTests} ✅`);
        console.log(`失败: ${failedTests} ❌`);
        console.log(`通过率: ${(passedTests / totalTests * 100).toFixed(1)}%`);

        if (failedTests > 0) {
            console.log('\n失败的测试:');
            this.testResults.filter(r => !r.passed).forEach(test => {
                console.log(`- ${test.name}: ${test.error || test.details || '未知错误'}`);
            });
        }

        console.log('\n=== 阶段1验证点检查 ===');
        this.checkStage1ValidationPoints();

        return {
            total: totalTests,
            passed: passedTests,
            failed: failedTests,
            passRate: passedTests / totalTests,
            allPassed: failedTests === 0
        };
    },

    // 检查阶段1验证点
    checkStage1ValidationPoints() {
        const validationPoints = [
            {
                name: '加载新JS文件不影响现有功能',
                check: () => {
                    // 检查全局命名空间污染
                    const linkageGlobals = Object.keys(window).filter(key => key.startsWith('Linkage'));
                    console.log('检测到的Linkage全局对象:', linkageGlobals);
                    // 应该有5个模块：Core, IdManager, PropertyPath, Validator, Stage1Test
                    return linkageGlobals.length <= 6; // 允许一些容错，最多6个
                }
            },
            {
                name: 'ID管理系统能正确为现有形状分配ID',
                check: () => {
                    const testShapes = [{ name: '测试' }, { name: '测试2' }];
                    LinkageIdManager.buildIdMap(testShapes);
                    return testShapes.every(shape => shape.id && typeof shape.id === 'string');
                }
            },
            {
                name: '属性路径工具正确读写嵌套属性',
                check: () => {
                    const obj = {};
                    LinkageCore.setNestedProperty(obj, 'a.b.c', 42);
                    return LinkageCore.getNestedProperty(obj, 'a.b.c') === 42;
                }
            },
            {
                name: '循环依赖检测算法正确性',
                check: () => {
                    const shapes = [
                        { id: 'a', derivation: { base_shape_id: 'b' } },
                        { id: 'b', derivation: { base_shape_id: 'a' } }
                    ];
                    LinkageIdManager.buildIdMap(shapes);
                    return LinkageIdManager.detectCircularDependency('a', 'b', shapes);
                }
            }
        ];

        console.log('\n验证点检查结果:');
        validationPoints.forEach(point => {
            try {
                const passed = point.check();
                console.log(`${passed ? '✅' : '❌'} ${point.name}`);
            } catch (error) {
                console.log(`❌ ${point.name}: 异常 - ${error.message}`);
            }
        });
    }
};

// 控制台快捷测试函数
window.testStage1 = () => LinkageStage1Test.runAllTests();