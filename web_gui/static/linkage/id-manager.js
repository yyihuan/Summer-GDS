// ID管理系统
window.LinkageIdManager = {
    idMap: new Map(),

    // 生成唯一ID
    generateShapeId() {
        return `shape_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
    },

    // 构建ID映射表
    buildIdMap(shapes) {
        this.idMap.clear();
        shapes.forEach((shape, index) => {
            if (!shape.id) {
                shape.id = this.generateShapeId();
                LinkageCore.log('info', `为形状生成ID: ${shape.name} -> ${shape.id}`);
            }
            this.idMap.set(shape.id, index);
        });
        LinkageCore.log('info', `ID映射表构建完成，包含${this.idMap.size}个形状`);
    },

    // 根据ID查找形状
    findShapeById(id, shapes) {
        const index = this.idMap.get(id);
        return index !== undefined ? shapes[index] : null;
    },

    // 查找派生形状
    findDerivedShapes(baseShapeId, shapes) {
        return shapes
            .map((shape, index) => ({ shape, index }))
            .filter(({ shape }) => shape.derivation?.base_shape_id === baseShapeId);
    },

    // 检测循环依赖
    detectCircularDependency(fromShapeId, toShapeId, shapes) {
        const visited = new Set();
        const stack = [toShapeId];

        while (stack.length > 0) {
            const currentId = stack.pop();
            if (visited.has(currentId)) continue;
            if (currentId === fromShapeId) return true;

            visited.add(currentId);
            const shape = this.findShapeById(currentId, shapes);
            if (shape?.derivation?.base_shape_id) {
                stack.push(shape.derivation.base_shape_id);
            }
        }
        return false;
    }
};