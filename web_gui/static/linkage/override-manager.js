// 用户覆盖管理器
window.LinkageOverrideManager = {
    isSystemUpdate: false,
    _enhanced: false,

    enhanceFormEventBinding() {
        if (this._enhanced) {
            return;
        }

        const originalBind = window.bindShapeCardEvents;
        if (typeof originalBind !== 'function') {
            LinkageCore.log('warn', '无法增强表单事件绑定：bindShapeCardEvents 不存在');
            return;
        }

        const manager = this;
        window.bindShapeCardEvents = function enhancedBind(cardElement, shape, index) {
            originalBind.call(this, cardElement, shape, index);
            manager.addOverrideDetection(cardElement, shape, index);
        };

        this._enhanced = true;
        LinkageCore.log('info', '表单事件绑定已增强，覆盖检测启用');
    },

    addOverrideDetection(cardElement, shape, index) {
        if (!shape?.derivation) {
            return;
        }

        LinkageCore.INHERITABLE_PROPERTIES.forEach(propPath => {
            const selectors = this.getInputSelectorsForProperty(propPath, index);
            selectors.forEach(selector => {
                const input = cardElement.querySelector(selector);
                if (!input) return;

                if (input.dataset.linkageOverrideBound === 'true') {
                    return;
                }

                this.bindOverrideDetection(input, shape, propPath, index);
                input.dataset.linkageOverrideBound = 'true';
            });
        });
    },

    getInputSelectorsForProperty(propPath, index) {
        const base = `shapes[${index}]`;
        switch (propPath) {
            case 'vertices':
                return [`[name="${base}.vertices"]`];
            case 'fillet.type':
                return [`[name="${base}.fillet.type"]`];
            case 'fillet.radius':
                return [`[name="${base}.fillet.radius"]`];
            case 'fillet.radii':
                return [`[name="${base}.fillet.radii"]`];
            case 'fillet.precision':
                return [`[name="${base}.fillet.precision"]`];
            case 'fillet.convex_radius':
                return [`[name="${base}.fillet.convex_radius"]`];
            case 'fillet.concave_radius':
                return [`[name="${base}.fillet.concave_radius"]`];
            case 'zoom':
                return [`[name="${base}.zoom"]`];
            case 'ring_width':
                return [`[name="${base}.ring_width"]`];
            case 'ring_space':
                return [`[name="${base}.ring_space"]`];
            case 'ring_num':
                return [`[name="${base}.ring_num"]`];
            default:
                return [];
        }
    },

    bindOverrideDetection(input, shape, propertyPath, shapeIndex) {
        input.addEventListener('change', event => {
            if (this.isSystemUpdate) {
                LinkageCore.log('debug', `系统更新变更，跳过覆盖检测: ${propertyPath}`);
                return;
            }

            const newValue = this.parseInputValue(event.target, propertyPath);
            this.handleUserOverride(shape, propertyPath, newValue, shapeIndex);
        });

        input.addEventListener('focus', () => {
            this.lastFocusedInput = { shapeIndex, propertyPath };
        });
    },

    parseInputValue(input, propertyPath) {
        const value = input.value;

        if (propertyPath === 'zoom' || input.type === 'number') {
            return parseFloat(value) || 0;
        }

        if (propertyPath === 'fillet.radii') {
            if (!value.trim()) return [];
            return value
                .split(',')
                .map(item => parseFloat(item.trim()))
                .filter(item => !Number.isNaN(item));
        }

        return value;
    },

    handleUserOverride(shape, propertyPath, newValue, shapeIndex) {
        if (!shape?.derivation) {
            return;
        }

        const inheritedValue = LinkagePropertyResolver.getInheritedValue(shape, propertyPath);

        if (!LinkageCore.deepEqual(newValue, inheritedValue)) {
            this.createOverride(shape, propertyPath, newValue, inheritedValue, shapeIndex);
            this.updateInheritanceIndicator(shapeIndex, propertyPath, 'overridden');
            LinkageCore.log('info', `用户覆盖属性: ${shape.name}.${propertyPath}`, {
                newValue,
                inheritedValue
            });
            showAlert(`属性 ${propertyPath} 已覆盖，不再跟随基础形状`, 'info');
        } else {
            this.removeOverride(shape, propertyPath, shapeIndex);
            this.updateInheritanceIndicator(shapeIndex, propertyPath, 'inherited');
            LinkageCore.log('info', `恢复属性继承: ${shape.name}.${propertyPath}`);
            showAlert(`属性 ${propertyPath} 已恢复继承`, 'success');
        }

        this.isSystemUpdate = true;
        updateJSONFromForm();
        this.isSystemUpdate = false;
    },

    createOverride(shape, propertyPath, value, previousInheritedValue, shapeIndex) {
        if (!shape.derivation.overrides) {
            shape.derivation.overrides = {};
        }

        shape.derivation.overrides[propertyPath] = {
            value,
            overridden: true,
            overridden_at: new Date().toISOString(),
            reason: 'user_manual_edit',
            previous_inherited_value: previousInheritedValue
        };

        this.syncCardDerivation(shapeIndex, shape);
    },

    removeOverride(shape, propertyPath, shapeIndex) {
        if (shape.derivation?.overrides?.[propertyPath]) {
            delete shape.derivation.overrides[propertyPath];
            this.syncCardDerivation(shapeIndex, shape);
        }
    },

    syncCardDerivation(shapeIndex, shape) {
        const card = document.querySelector(`[data-shape-index="${shapeIndex}"]`);
        if (!card || !shape.derivation) {
            return;
        }
        card.setAttribute('data-derivation', JSON.stringify(shape.derivation));
    },

    updateInheritanceIndicator(shapeIndex, propertyPath, status) {
        const card = document.querySelector(`[data-shape-index="${shapeIndex}"]`);
        if (!card) {
            return;
        }

        const indicator = card.querySelector(`[data-inheritance-indicator="${propertyPath}"]`);
        if (!indicator) {
            return;
        }

        if (status === 'overridden') {
            indicator.textContent = '已覆盖';
            indicator.classList.remove('badge-secondary');
            indicator.classList.add('badge-warning');
        } else {
            indicator.textContent = '继承中';
            indicator.classList.remove('badge-warning');
            indicator.classList.add('badge-success');
        }
    },

    refreshIndicatorsForShape(shape, shapeIndex) {
        const hasDerivation = !!shape?.derivation;
        if (!hasDerivation) {
            return;
        }

        LinkageCore.INHERITABLE_PROPERTIES.forEach(propPath => {
            const status = LinkagePropertyResolver.isPropertyOverridden(shape, propPath)
                ? 'overridden'
                : 'inherited';
            this.updateInheritanceIndicator(shapeIndex, propPath, status);
        });
    }
};
