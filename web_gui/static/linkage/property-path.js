// 属性路径工具模块
window.LinkagePropertyPath = {

    // 验证属性路径格式
    validatePropertyPath(path) {
        if (!path || typeof path !== 'string') {
            return { valid: false, error: '属性路径必须是非空字符串' };
        }

        // 检查是否在可继承属性列表中
        if (!LinkageCore.INHERITABLE_PROPERTIES.includes(path)) {
            return {
                valid: false,
                error: `属性路径 "${path}" 不在可继承属性列表中`,
                suggestions: LinkageCore.INHERITABLE_PROPERTIES.filter(p => p.includes(path.split('.')[0]))
            };
        }

        return { valid: true };
    },

    // 获取属性路径的类型信息
    getPropertyTypeInfo(path) {
        const typeMap = {
            'vertices': { type: 'string', description: '形状顶点坐标字符串' },
            'fillet.type': { type: 'string', description: '倒角类型 (arc/adaptive)' },
            'fillet.radius': { type: 'number', description: '倒角半径' },
            'fillet.radii': { type: 'array', description: '每个顶点的倒角半径数组' },
            'fillet.precision': { type: 'number', description: '倒角精度' },
            'fillet.convex_radius': { type: 'number', description: '凸角倒角半径' },
            'fillet.concave_radius': { type: 'number', description: '凹角倒角半径' },
            'zoom': { type: 'number', description: '形状缩放值' },
            '_metadata': { type: 'object', description: '形状元数据' }
        };

        return typeMap[path] || { type: 'unknown', description: '未知属性类型' };
    },

    // 标准化属性值
    normalizePropertyValue(path, value) {
        const typeInfo = this.getPropertyTypeInfo(path);

        try {
            switch (typeInfo.type) {
                case 'number':
                    if (value === null || value === undefined || value === '') return undefined;
                    const numValue = parseFloat(value);
                    return isNaN(numValue) ? undefined : numValue;

                case 'string':
                    return value === null || value === undefined ? undefined : String(value);

                case 'array':
                    if (Array.isArray(value)) return value;
                    if (typeof value === 'string') {
                        try {
                            return JSON.parse(value);
                        } catch {
                            return value.split(',').map(v => parseFloat(v.trim())).filter(v => !isNaN(v));
                        }
                    }
                    return undefined;

                case 'object':
                    if (typeof value === 'object') return value;
                    if (typeof value === 'string') {
                        try {
                            return JSON.parse(value);
                        } catch {
                            return undefined;
                        }
                    }
                    return undefined;

                default:
                    return value;
            }
        } catch (error) {
            LinkageCore.log('warn', `属性值标准化失败: ${path}`, { value, error: error.message });
            return undefined;
        }
    },

    // 比较属性值是否相等
    comparePropertyValues(path, value1, value2) {
        const normalized1 = this.normalizePropertyValue(path, value1);
        const normalized2 = this.normalizePropertyValue(path, value2);

        return LinkageCore.deepEqual(normalized1, normalized2);
    },

    // 获取属性路径的显示名称
    getPropertyDisplayName(path) {
        const displayNames = {
            'vertices': '顶点坐标',
            'fillet.type': '倒角类型',
            'fillet.radius': '倒角半径',
            'fillet.radii': '顶点倒角半径',
            'fillet.precision': '倒角精度',
            'fillet.convex_radius': '凸角半径',
            'fillet.concave_radius': '凹角半径',
            'zoom': '缩放值',
            '_metadata': '元数据'
        };

        return displayNames[path] || path;
    },

    // 检查属性路径是否为嵌套属性
    isNestedProperty(path) {
        return path.includes('.');
    },

    // 获取属性路径的父级路径
    getParentPath(path) {
        const parts = path.split('.');
        return parts.length > 1 ? parts.slice(0, -1).join('.') : null;
    },

    // 获取属性路径的最后一个键
    getLastKey(path) {
        const parts = path.split('.');
        return parts[parts.length - 1];
    },

    // 构建完整的属性访问路径
    buildAccessPath(basePath, propertyPath) {
        if (!basePath) return propertyPath;
        return `${basePath}.${propertyPath}`;
    }
};