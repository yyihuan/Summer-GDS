// 阶段2测试：派生关系创建机制测试
// 测试说明：在浏览器开发者控制台中运行这些测试

console.log('=== 阶段2 派生关系创建机制测试 ===');

// 测试1：验证联动系统模块加载
function testModuleLoading() {
    console.log('\n测试1：验证联动系统模块加载');

    const requiredModules = [
        'LinkageCore',
        'LinkageIdManager',
        'LinkagePropertyResolver'
    ];

    const results = requiredModules.map(module => {
        const loaded = typeof window[module] !== 'undefined';
        console.log(`${module}: ${loaded ? '✓ 已加载' : '✗ 未加载'}`);
        return loaded;
    });

    const allLoaded = results.every(Boolean);
    console.log(`结果: ${allLoaded ? '✓ 所有模块已加载' : '✗ 部分模块未加载'}`);
    return allLoaded;
}

// 测试2：验证ID生成和映射
function testIdManagement() {
    console.log('\n测试2：验证ID生成和映射');

    try {
        // 测试ID生成
        const id1 = LinkageIdManager.generateShapeId();
        const id2 = LinkageIdManager.generateShapeId();

        console.log(`生成ID1: ${id1}`);
        console.log(`生成ID2: ${id2}`);
        console.log(`ID唯一性: ${id1 !== id2 ? '✓ 通过' : '✗ 失败'}`);

        // 测试ID映射构建
        const testShapes = [
            { id: id1, name: '测试形状1', type: 'polygon' },
            { id: id2, name: '测试形状2', type: 'polygon' }
        ];

        LinkageIdManager.buildIdMap(testShapes);

        const found1 = LinkageIdManager.findShapeById(id1, testShapes);
        const found2 = LinkageIdManager.findShapeById(id2, testShapes);

        console.log(`ID映射测试: ${found1 && found2 ? '✓ 通过' : '✗ 失败'}`);

        return true;
    } catch (error) {
        console.error('ID管理测试失败:', error);
        return false;
    }
}

// 测试3：验证属性解析引擎
function testPropertyResolver() {
    console.log('\n测试3：验证属性解析引擎');

    try {
        // 创建测试基础形状
        const baseShape = {
            id: 'test-base',
            name: '基础形状',
            type: 'polygon',
            vertices: '0,0:10,0:10,10:0,10',
            fillet: { type: 'arc', radius: 5 },
            zoom: 0
        };

        // 创建测试派生形状
        const derivedShape = {
            id: 'test-derived',
            name: '派生形状',
            type: 'polygon',
            derivation: {
                base_shape_id: 'test-base',
                derive_type: 'offset',
                derive_params: { zoom: 2 },
                overrides: {}
            }
        };

        const testShapes = [baseShape, derivedShape];

        // 关键：需要先构建ID映射表，这样解析器才能找到基础形状
        LinkageIdManager.buildIdMap(testShapes);

        // 临时设置config.shapes以供解析器使用
        const originalShapes = config.shapes;
        config.shapes = testShapes;

        // 测试属性解析
        const resolved = LinkagePropertyResolver.resolveShapeProperties(derivedShape);

        console.log('解析后的形状:', resolved);
        console.log(`继承顶点: ${resolved._computed.vertices === baseShape.vertices ? '✓ 通过' : '✗ 失败'}`);
        console.log(`继承倒角类型: ${resolved._computed.fillet.type === baseShape.fillet.type ? '✓ 通过' : '✗ 失败'}`);
        console.log(`派生参数: ${resolved._computed.zoom === 2 ? '✓ 通过' : '✗ 失败'}`);

        // 恢复原始配置
        config.shapes = originalShapes;

        return resolved._computed.vertices === baseShape.vertices && resolved._computed.zoom === 2;
    } catch (error) {
        console.error('属性解析测试失败:', error);
        return false;
    }
}

// 测试4：验证offsetShape函数增强
function testOffsetShapeEnhancement() {
    console.log('\n测试4：验证offsetShape函数增强');

    try {
        // 清空现有配置
        const originalShapes = [...config.shapes];
        config.shapes = [{
            name: '测试多边形',
            type: 'polygon',
            vertices: '0,0:10,0:10,10:0,10',
            fillet: { type: 'arc', radius: 1 },
            zoom: 0,
            layer: [1, 0]
        }];

        const originalCount = config.shapes.length;
        console.log(`原始形状数量: ${originalCount}`);

        // 测试offsetShape
        offsetShape(0);

        const newCount = config.shapes.length;
        console.log(`新形状数量: ${newCount}`);
        console.log(`形状创建: ${newCount === originalCount + 1 ? '✓ 通过' : '✗ 失败'}`);

        // 检查新形状的派生关系
        const newShape = config.shapes[config.shapes.length - 1];
        console.log('新创建的形状:', newShape);

        const hasDerivation = newShape.derivation && newShape.derivation.base_shape_id;
        console.log(`派生关系: ${hasDerivation ? '✓ 通过' : '✗ 失败'}`);

        // 恢复原始配置
        config.shapes = originalShapes;

        return hasDerivation;
    } catch (error) {
        console.error('offsetShape增强测试失败:', error);
        return false;
    }
}

// 测试5：验证YAML输出包含派生关系
function testYAMLOutput() {
    console.log('\n测试5：验证YAML输出包含派生关系');

    try {
        // 创建包含派生关系的测试配置
        const testConfig = {
            global: config.global,
            gds: config.gds,
            shapes: [
                {
                    id: 'base-1',
                    name: '基础形状',
                    type: 'polygon',
                    vertices: '0,0:10,0:10,10:0,10',
                    fillet: { type: 'arc', radius: 1 },
                    zoom: 0,
                    layer: [1, 0]
                },
                {
                    id: 'derived-1',
                    name: '派生形状',
                    type: 'polygon',
                    layer: [2, 0],
                    derivation: {
                        base_shape_id: 'base-1',
                        derive_type: 'offset',
                        derive_params: { zoom: 2 },
                        created_at: new Date().toISOString(),
                        overrides: {}
                    }
                }
            ]
        };

        // 生成YAML
        const yamlText = jsyaml.dump(testConfig);
        console.log('生成的YAML片段:');
        console.log(yamlText.substring(0, 500) + '...');

        // 检查关键字段
        const hasDerivation = yamlText.includes('derivation:');
        const hasBaseShapeId = yamlText.includes('base_shape_id:');
        const hasDeriveType = yamlText.includes('derive_type:');

        console.log(`包含derivation: ${hasDerivation ? '✓ 通过' : '✗ 失败'}`);
        console.log(`包含base_shape_id: ${hasBaseShapeId ? '✓ 通过' : '✗ 失败'}`);
        console.log(`包含derive_type: ${hasDeriveType ? '✓ 通过' : '✗ 失败'}`);

        return hasDerivation && hasBaseShapeId && hasDeriveType;
    } catch (error) {
        console.error('YAML输出测试失败:', error);
        return false;
    }
}

// 执行所有测试
function runStage2Tests() {
    console.log('开始执行阶段2测试...\n');

    const tests = [
        { name: '模块加载测试', fn: testModuleLoading },
        { name: 'ID管理测试', fn: testIdManagement },
        { name: '属性解析测试', fn: testPropertyResolver },
        { name: 'offsetShape增强测试', fn: testOffsetShapeEnhancement },
        { name: 'YAML输出测试', fn: testYAMLOutput }
    ];

    const results = tests.map(test => {
        try {
            const result = test.fn();
            return { name: test.name, passed: result };
        } catch (error) {
            console.error(`${test.name}执行失败:`, error);
            return { name: test.name, passed: false };
        }
    });

    console.log('\n=== 测试结果汇总 ===');
    results.forEach(result => {
        console.log(`${result.name}: ${result.passed ? '✓ 通过' : '✗ 失败'}`);
    });

    const passedCount = results.filter(r => r.passed).length;
    const totalCount = results.length;

    console.log(`\n总计: ${passedCount}/${totalCount} 通过`);
    console.log(`阶段2完成度: ${passedCount === totalCount ? '✓ 全部通过' : '△ 部分通过'}`);

    return { passedCount, totalCount, results };
}

// 暴露测试函数到全局
window.Stage2Tests = {
    runAll: runStage2Tests,
    testModuleLoading,
    testIdManagement,
    testPropertyResolver,
    testOffsetShapeEnhancement,
    testYAMLOutput
};

console.log('阶段2测试脚本已加载');
console.log('运行测试: Stage2Tests.runAll()');
console.log('运行单个测试: Stage2Tests.testModuleLoading() 等');