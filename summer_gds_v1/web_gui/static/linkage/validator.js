// 验证工具模块
window.LinkageValidator = {

    // 验证形状配置
    validateShapeConfig(shape) {
        const errors = [];
        const warnings = [];

        // 基本结构验证
        if (!shape || typeof shape !== 'object') {
            errors.push('形状配置必须是对象');
            return { valid: false, errors, warnings };
        }

        // 必需字段验证
        if (!shape.type) {
            errors.push('缺少 type 字段');
        }

        if (!shape.name) {
            warnings.push('缺少 name 字段，建议添加形状名称');
        }

        // ID验证
        if (shape.id && typeof shape.id !== 'string') {
            errors.push('id 字段必须是字符串');
        }

        // 派生关系验证
        if (shape.derivation) {
            const derivationResult = this.validateDerivationConfig(shape.derivation);
            errors.push(...derivationResult.errors);
            warnings.push(...derivationResult.warnings);
        }

        return {
            valid: errors.length === 0,
            errors,
            warnings
        };
    },

    // 验证派生关系配置
    validateDerivationConfig(derivation) {
        const errors = [];
        const warnings = [];

        if (!derivation || typeof derivation !== 'object') {
            errors.push('派生关系配置必须是对象');
            return { valid: false, errors, warnings };
        }

        // 必需字段验证
        if (!derivation.base_shape_id) {
            errors.push('派生关系缺少 base_shape_id 字段');
        }

        if (!derivation.derive_type) {
            errors.push('派生关系缺少 derive_type 字段');
        }

        // 派生类型验证
        const validDeriveTypes = ['offset', 'copy', 'transform'];
        if (derivation.derive_type && !validDeriveTypes.includes(derivation.derive_type)) {
            errors.push(`无效的派生类型: ${derivation.derive_type}，支持的类型: ${validDeriveTypes.join(', ')}`);
        }

        // 覆盖配置验证
        if (derivation.overrides) {
            const overrideResult = this.validateOverrideConfig(derivation.overrides);
            errors.push(...overrideResult.errors);
            warnings.push(...overrideResult.warnings);
        }

        return {
            valid: errors.length === 0,
            errors,
            warnings
        };
    },

    // 验证覆盖配置
    validateOverrideConfig(overrides) {
        const errors = [];
        const warnings = [];

        if (!overrides || typeof overrides !== 'object') {
            warnings.push('覆盖配置应该是对象');
            return { valid: true, errors, warnings };
        }

        Object.keys(overrides).forEach(propertyPath => {
            // 验证属性路径
            const pathValidation = LinkagePropertyPath.validatePropertyPath(propertyPath);
            if (!pathValidation.valid) {
                errors.push(`无效的属性路径 "${propertyPath}": ${pathValidation.error}`);
                return;
            }

            const override = overrides[propertyPath];

            // 验证覆盖记录结构
            if (!override || typeof override !== 'object') {
                errors.push(`属性 "${propertyPath}" 的覆盖配置必须是对象`);
                return;
            }

            // 验证必需字段
            if (typeof override.overridden !== 'boolean') {
                errors.push(`属性 "${propertyPath}" 的覆盖配置缺少 overridden 布尔字段`);
            }

            if (override.overridden && override.value === undefined) {
                errors.push(`属性 "${propertyPath}" 标记为已覆盖但缺少 value 字段`);
            }

            // 验证值类型
            if (override.value !== undefined) {
                const typeInfo = LinkagePropertyPath.getPropertyTypeInfo(propertyPath);
                const normalizedValue = LinkagePropertyPath.normalizePropertyValue(propertyPath, override.value);

                if (normalizedValue === undefined && override.value !== undefined) {
                    warnings.push(`属性 "${propertyPath}" 的值类型可能不正确，期望类型: ${typeInfo.type}`);
                }
            }
        });

        return {
            valid: errors.length === 0,
            errors,
            warnings
        };
    },

    // 验证形状数组配置
    validateShapesConfig(shapes) {
        const errors = [];
        const warnings = [];
        const shapeIds = new Set();

        if (!Array.isArray(shapes)) {
            errors.push('shapes 配置必须是数组');
            return { valid: false, errors, warnings };
        }

        shapes.forEach((shape, index) => {
            // 验证单个形状
            const shapeResult = this.validateShapeConfig(shape);

            shapeResult.errors.forEach(error => {
                errors.push(`形状 [${index}] ${shape.name || '无名称'}: ${error}`);
            });

            shapeResult.warnings.forEach(warning => {
                warnings.push(`形状 [${index}] ${shape.name || '无名称'}: ${warning}`);
            });

            // 检查ID重复
            if (shape.id) {
                if (shapeIds.has(shape.id)) {
                    errors.push(`形状 [${index}] 的ID "${shape.id}" 重复`);
                } else {
                    shapeIds.add(shape.id);
                }
            }
        });

        // 验证派生关系的引用完整性
        const referenceResult = this.validateReferenceIntegrity(shapes);
        errors.push(...referenceResult.errors);
        warnings.push(...referenceResult.warnings);

        return {
            valid: errors.length === 0,
            errors,
            warnings
        };
    },

    // 验证引用完整性
    validateReferenceIntegrity(shapes) {
        const errors = [];
        const warnings = [];
        const shapeIdSet = new Set(shapes.map(shape => shape.id).filter(Boolean));

        shapes.forEach((shape, index) => {
            if (shape.derivation?.base_shape_id) {
                // 检查基础形状是否存在
                if (!shapeIdSet.has(shape.derivation.base_shape_id)) {
                    errors.push(`形状 [${index}] ${shape.name || '无名称'}: 引用的基础形状ID "${shape.derivation.base_shape_id}" 不存在`);
                }

                // 检查循环依赖
                if (LinkageIdManager.detectCircularDependency(shape.id, shape.derivation.base_shape_id, shapes)) {
                    errors.push(`形状 [${index}] ${shape.name || '无名称'}: 检测到循环依赖`);
                }
            }
        });

        return {
            valid: errors.length === 0,
            errors,
            warnings
        };
    },

    // 验证系统兼容性
    validateSystemCompatibility() {
        const errors = [];
        const warnings = [];

        // 检查必需的全局对象
        const requiredGlobals = ['LinkageCore', 'LinkageIdManager', 'LinkagePropertyPath'];
        requiredGlobals.forEach(globalName => {
            if (typeof window[globalName] === 'undefined') {
                errors.push(`缺少必需的全局对象: ${globalName}`);
            }
        });

        // 检查浏览器兼容性
        if (typeof Map === 'undefined') {
            errors.push('浏览器不支持 Map 对象，需要更新浏览器');
        }

        if (typeof Set === 'undefined') {
            errors.push('浏览器不支持 Set 对象，需要更新浏览器');
        }

        // 检查现有配置
        if (typeof window.config !== 'undefined' && window.config.shapes) {
            const shapesResult = this.validateShapesConfig(window.config.shapes);
            if (!shapesResult.valid) {
                warnings.push('现有形状配置存在问题，联动功能可能受限');
            }
        }

        return {
            valid: errors.length === 0,
            errors,
            warnings
        };
    },

    // 生成验证报告
    generateValidationReport(validationResult) {
        const report = {
            timestamp: new Date().toISOString(),
            valid: validationResult.valid,
            summary: {
                errors: validationResult.errors.length,
                warnings: validationResult.warnings.length
            },
            details: {
                errors: validationResult.errors,
                warnings: validationResult.warnings
            }
        };

        // 添加建议
        if (!validationResult.valid) {
            report.suggestions = this.generateSuggestions(validationResult.errors);
        }

        return report;
    },

    // 生成修复建议
    generateSuggestions(errors) {
        const suggestions = [];

        errors.forEach(error => {
            if (error.includes('缺少 type 字段')) {
                suggestions.push('为每个形状添加 type 字段，如 "polygon", "rings", "via"');
            }

            if (error.includes('ID') && error.includes('重复')) {
                suggestions.push('确保每个形状的ID唯一，或移除ID让系统自动生成');
            }

            if (error.includes('循环依赖')) {
                suggestions.push('检查派生关系链，确保没有形状直接或间接引用自己');
            }

            if (error.includes('属性路径')) {
                suggestions.push('检查覆盖配置中的属性路径是否正确，参考可继承属性列表');
            }
        });

        // 去重
        return [...new Set(suggestions)];
    }
};