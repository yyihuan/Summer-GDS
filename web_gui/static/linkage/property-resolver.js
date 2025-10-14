// 属性解析引擎
window.LinkagePropertyResolver = {

    // 解析单个形状的属性
    resolveShapeProperties(shape) {
        if (!shape.derivation) {
            // 非派生形状，直接返回
            return { ...shape, _computed: this.extractComputedProps(shape) };
        }

        const shapes = window.config ? window.config.shapes : (typeof config !== 'undefined' ? config.shapes : []);
        const baseShape = LinkageIdManager.findShapeById(
            shape.derivation.base_shape_id,
            shapes
        );

        if (!baseShape) {
            LinkageCore.log('error', `基础形状未找到: ${shape.derivation.base_shape_id}`);
            return shape;
        }

        const computed = {};

        // 解析所有可继承属性
        LinkageCore.INHERITABLE_PROPERTIES.forEach(propPath => {
            const override = shape.derivation.overrides?.[propPath];

            if (override?.overridden) {
                // 使用覆盖值
                LinkageCore.setNestedProperty(computed, propPath, override.value);
                LinkageCore.log('debug', `属性覆盖: ${shape.name}.${propPath} = ${JSON.stringify(override.value)}`);
            } else {
                // 使用继承值
                const inheritedValue = LinkageCore.getNestedProperty(baseShape, propPath);
                if (inheritedValue !== undefined) {
                    LinkageCore.setNestedProperty(computed, propPath, inheritedValue);
                    LinkageCore.log('debug', `属性继承: ${shape.name}.${propPath} = ${JSON.stringify(inheritedValue)}`);
                }
            }
        });

        // 应用派生参数（覆盖继承值）
        if (shape.derivation.derive_params) {
            Object.assign(computed, shape.derivation.derive_params);
            LinkageCore.log('debug', `应用派生参数: ${shape.name}`, shape.derivation.derive_params);
        }

        return {
            ...shape,
            _computed: computed
        };
    },

    // 提取计算属性
    extractComputedProps(shape) {
        const computed = {};
        LinkageCore.INHERITABLE_PROPERTIES.forEach(propPath => {
            const value = LinkageCore.getNestedProperty(shape, propPath);
            if (value !== undefined) {
                LinkageCore.setNestedProperty(computed, propPath, value);
            }
        });
        return computed;
    },

    // 批量解析所有形状
    resolveAllShapes(shapes) {
        LinkageIdManager.buildIdMap(shapes);
        return shapes.map(shape => this.resolveShapeProperties(shape));
    },

    // 检查属性是否被覆盖
    isPropertyOverridden(shape, propertyPath) {
        return shape.derivation?.overrides?.[propertyPath]?.overridden === true;
    },

    // 检查属性是否继承
    isPropertyInherited(shape, propertyPath) {
        if (!shape.derivation) return false;
        const override = shape.derivation.overrides?.[propertyPath];
        return !override?.overridden;
    },

    // 获取继承值
    getInheritedValue(shape, propertyPath) {
        if (!shape.derivation) return undefined;
        const shapes = window.config ? window.config.shapes : (typeof config !== 'undefined' ? config.shapes : []);
        const baseShape = LinkageIdManager.findShapeById(
            shape.derivation.base_shape_id,
            shapes
        );
        return baseShape ? LinkageCore.getNestedProperty(baseShape, propertyPath) : undefined;
    }
};