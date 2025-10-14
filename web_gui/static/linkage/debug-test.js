// 简单调试测试
console.log('=== 调试开始 ===');

// 创建测试数据
const baseShape = {
    id: 'debug-base',
    vertices: '0,0:10,0:10,10:0,10',
    fillet: { radius: 5 }
};

const derivedShape = {
    id: 'debug-derived',
    derivation: {
        base_shape_id: 'debug-base',
        derive_params: { zoom: 2 }
    }
};

// 设置配置
window.config = {
    shapes: [baseShape, derivedShape]
};

console.log('1. 设置config.shapes:', window.config.shapes);

// 构建ID映射表
LinkageIdManager.buildIdMap(window.config.shapes);
console.log('2. ID映射表:', LinkageIdManager.idMap);

// 测试查找基础形状
console.log('3. 查找基础形状:', LinkageIdManager.findShapeById('debug-base', window.config.shapes));

// 检查全局config变量
console.log('4. 全局config是否存在:', typeof config !== 'undefined');
console.log('5. window.config === config:', window.config === (typeof config !== 'undefined' ? config : undefined));

// 测试解析
try {
    const resolved = LinkagePropertyResolver.resolveShapeProperties(derivedShape);
    console.log('6. 解析结果:', resolved);
} catch (error) {
    console.error('6. 解析错误:', error);
}

console.log('=== 调试结束 ===');