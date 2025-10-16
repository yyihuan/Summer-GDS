// 变更检测与同步模块
window.LinkageSyncManager = {

    _enhanced: false,

    getConfig() {
        if (window.config) {
            return window.config;
        }
        if (typeof config !== 'undefined') {
            return config;
        }
        window.config = { shapes: [] };
        return window.config;
    },

    // 增强 updateJSONFromForm，增加变更检测流程
    enhanceUpdateJSONFromForm() {
        if (this._enhanced) {
            return;
        }

        const originalUpdate = window.updateJSONFromForm;
        if (typeof originalUpdate !== 'function') {
            LinkageCore.log('warn', '未找到 updateJSONFromForm，暂不启用变更检测');
            return;
        }

        const manager = this;
        window.updateJSONFromForm = function enhancedUpdateJSONFromForm() {
            const activeConfig = manager.getConfig();
            const previousShapes = JSON.parse(JSON.stringify(activeConfig.shapes || []));
            LinkageCore.log('info', '开始表单更新，记录变更前状态');

            originalUpdate.call(this);

            setTimeout(() => {
                const latestConfig = manager.getConfig();
                manager.detectAndSync(previousShapes, latestConfig.shapes || []);
            }, 0);
        };

        this._enhanced = true;
        LinkageCore.log('info', 'updateJSONFromForm 函数已增强');
    },

    // 对比变更并执行同步
    detectAndSync(oldShapes, newShapes) {
        if (!Array.isArray(newShapes) || newShapes.length === 0) {
            return;
        }

        const changes = this.detectChanges(oldShapes || [], newShapes);
        if (changes.length === 0) {
            return;
        }

        changes.forEach(({ shapeId, changedProperties }) => {
            LinkageCore.log('info', `检测到形状变化: ${shapeId}`, changedProperties);
            this.syncDerivedShapes(shapeId, changedProperties);
        });
    },

    // 检测所有形状的差异
    detectChanges(oldShapes, newShapes) {
        const changes = [];
        const snapshot = Array.isArray(newShapes) ? newShapes : [];

        LinkageIdManager.buildIdMap(snapshot);

        snapshot.forEach((newShape) => {
            if (!newShape?.id) {
                return;
            }

            const oldShape = (oldShapes || []).find(item => item?.id === newShape.id);
            if (!oldShape) {
                return;
            }

            const diff = this.detectPropertyChanges(oldShape, newShape);
            if (diff.length > 0) {
                changes.push({
                    shapeId: newShape.id,
                    shapeName: newShape.name,
                    changedProperties: diff
                });
            }
        });

        return changes;
    },

    // 检测单个形状内的属性差异
    detectPropertyChanges(oldShape, newShape) {
        const changed = [];

        LinkageCore.INHERITABLE_PROPERTIES.forEach(propPath => {
            const oldValue = LinkageCore.getNestedProperty(oldShape, propPath);
            const newValue = LinkageCore.getNestedProperty(newShape, propPath);

            if (!LinkageCore.deepEqual(oldValue, newValue)) {
                changed.push(propPath);
                LinkageCore.log('debug', `属性变化检测: ${propPath}`, {
                    old: oldValue,
                    new: newValue
                });
            }
        });

        return changed;
    },

    // 将基础形状变更同步至派生形状
    syncDerivedShapes(baseShapeId, changedProperties) {
        const activeConfig = this.getConfig();
        const shapes = activeConfig.shapes || [];
        if (shapes.length === 0) {
            return;
        }

        const baseShape = shapes.find(shape => shape?.id === baseShapeId);
        if (!baseShape) {
            LinkageCore.log('warn', `同步失败，未找到基础形状: ${baseShapeId}`);
            return;
        }

        LinkageIdManager.buildIdMap(shapes);
        const derivedShapes = LinkageIdManager.findDerivedShapes(baseShapeId, shapes);
        if (derivedShapes.length === 0) {
            LinkageCore.log('debug', `无派生形状需要同步: ${baseShapeId}`);
            return;
        }

        LinkageCore.log('info', `同步 ${derivedShapes.length} 个派生形状`, {
            baseShapeId,
            changedProperties
        });

        derivedShapes.forEach(({ shape, index }) => {
            let needsUpdate = false;

            changedProperties.forEach(propPath => {
                const overridden = LinkagePropertyResolver.isPropertyOverridden(shape, propPath);
                if (overridden) {
                    LinkageCore.log('debug', `跳过已覆盖属性: ${shape.name}.${propPath}`);
                    return;
                }

                needsUpdate = true;
                const baseValue = LinkageCore.getNestedProperty(baseShape, propPath);
                this.normalizeDerivedShapeData(shape, propPath, baseValue);
                this.updateComputedCache(shape, propPath, baseValue);

                const isRingProperty = /^ring_(width|space|num)$/.test(propPath);
                const isCircleMetadata = propPath === '_metadata' && ((baseValue && baseValue.source === 'circle') || (shape._metadata && shape._metadata.source === 'circle'));

                if (isRingProperty) {
                    LinkageCore.setNestedProperty(shape, propPath, baseValue);
                }
                LinkageCore.log('debug', `同步属性: ${shape.name}.${propPath}`);

                if (isRingProperty) {
                    window.__linkageDebugCounters = window.__linkageDebugCounters || {};
                    window.__linkageDebugCounters.ringSync = (window.__linkageDebugCounters.ringSync || 0) + 1;
                    const debugEntry = {
                        phase: 'syncDerivedShapes:ringPreResolve',
                        callId: window.__linkageDebugCounters.ringSync,
                        shapeId: shape.id,
                        shapeName: shape.name,
                        propertyPath: propPath,
                        baseValue,
                        derivedRawValue: LinkageCore.getNestedProperty(shape, propPath),
                        derivedComputedValue: LinkageCore.getNestedProperty(shape._computed || {}, propPath)
                    };
                    window.__linkageDebugLog = window.__linkageDebugLog || [];
                    window.__linkageDebugLog.push(debugEntry);
                    LinkageCore.log('info', '[DEBUG] ring inheritance pre-resolve', debugEntry);
                } else if (isCircleMetadata) {
                    window.__linkageDebugCounters = window.__linkageDebugCounters || {};
                    window.__linkageDebugCounters.circleSync = (window.__linkageDebugCounters.circleSync || 0) + 1;
                    const circleEntry = {
                        phase: 'syncDerivedShapes:circleMetadataPreResolve',
                        callId: window.__linkageDebugCounters.circleSync,
                        shapeId: shape.id,
                        shapeName: shape.name,
                        propertyPath: propPath,
                        baseMetadata: baseValue,
                        derivedMetadata: shape._metadata
                    };
                    window.__linkageDebugLog = window.__linkageDebugLog || [];
                    window.__linkageDebugLog.push(circleEntry);
                    LinkageCore.log('info', '[DEBUG] circle metadata pre-resolve', circleEntry);
                }
            });

            if (!needsUpdate) {
                return;
            }

            const resolved = LinkagePropertyResolver.resolveShapeProperties(shape);
            activeConfig.shapes[index] = resolved;
            this.updateShapeCardDisplay(index, resolved);

            changedProperties.forEach(propPath => {
                const isRingProperty = /^ring_(width|space|num)$/.test(propPath);
                const isCircleMetadata = propPath === '_metadata' && ((resolved._metadata && resolved._metadata.source === 'circle') || (LinkageCore.getNestedProperty(resolved, propPath)?.source === 'circle'));

                if (!isRingProperty && !isCircleMetadata) {
                    return;
                }
                window.__linkageDebugLog = window.__linkageDebugLog || [];

                if (isRingProperty) {
                    const postEntry = {
                        phase: 'syncDerivedShapes:ringPostResolve',
                        callId: window.__linkageDebugCounters?.ringSync,
                        shapeId: resolved.id,
                        shapeName: resolved.name,
                        propertyPath: propPath,
                        resolvedRawValue: LinkageCore.getNestedProperty(resolved, propPath),
                        resolvedComputedValue: LinkageCore.getNestedProperty(resolved._computed || {}, propPath)
                    };
                    window.__linkageDebugLog.push(postEntry);
                    LinkageCore.log('info', '[DEBUG] ring inheritance post-resolve', postEntry);
                }

                if (isCircleMetadata) {
                    const circlePostEntry = {
                        phase: 'syncDerivedShapes:circleMetadataPostResolve',
                        callId: window.__linkageDebugCounters?.circleSync,
                        shapeId: resolved.id,
                        shapeName: resolved.name,
                        propertyPath: propPath,
                        resolvedMetadata: resolved._metadata,
                        resolvedComputedMetadata: LinkageCore.getNestedProperty(resolved._computed || {}, propPath)
                    };
                    window.__linkageDebugLog.push(circlePostEntry);
                    LinkageCore.log('info', '[DEBUG] circle metadata post-resolve', circlePostEntry);
                }
            });
        });

        LinkageIdManager.buildIdMap(activeConfig.shapes);

        this.updateJSONEditorSilently();
    },

    // 当找不到卡片时仍视为成功
    updateShapeCardDisplay(shapeIndex, resolvedShape) {
        const card = document.querySelector(`[data-shape-index="${shapeIndex}"]`);
        if (!card) {
            LinkageCore.log('debug', `形状卡片不存在（可能为测试环境）: 索引${shapeIndex}`);
            LinkageCore.log('debug', `数据层同步完成: ${resolvedShape.name}`);
            return;
        }

        if (resolvedShape.id) {
            card.setAttribute('data-shape-id', resolvedShape.id);
        }

        if (resolvedShape.derivation) {
            card.setAttribute('data-derivation', JSON.stringify(resolvedShape.derivation));
        } else {
            card.removeAttribute('data-derivation');
        }

        const overrideManager = window.LinkageOverrideManager;
        if (overrideManager) {
            overrideManager.isSystemUpdate = true;
        }

        this.updateFormValues(card, resolvedShape, shapeIndex);

        if (overrideManager) {
            overrideManager.isSystemUpdate = false;
            overrideManager.refreshIndicatorsForShape(resolvedShape, shapeIndex);
        }
        LinkageCore.log('debug', `已更新形状卡片显示: ${resolvedShape.name}`);
    },

    // 更新表单控件
    updateFormValues(card, shape, index) {
        const overrideManager = window.LinkageOverrideManager;
        if (overrideManager) {
            overrideManager.isSystemUpdate = true;
        }

        const computed = shape._computed || {};

        if (computed.vertices !== undefined) {
            const input = card.querySelector(`[name="shapes[${index}].vertices"]`);
            if (input) input.value = computed.vertices;
        }

        if (computed.fillet) {
            const typeSelect = card.querySelector(`[name="shapes[${index}].fillet.type"]`);
            if (typeSelect && computed.fillet.type) {
                typeSelect.value = computed.fillet.type;
            }

            const radiusInput = card.querySelector(`[name="shapes[${index}].fillet.radius"]`);
            if (radiusInput && computed.fillet.radius !== undefined) {
                radiusInput.value = computed.fillet.radius;
            }

            const radiiInput = card.querySelector(`[name="shapes[${index}].fillet.radii"]`);
            if (radiiInput && computed.fillet.radii !== undefined) {
                radiiInput.value = Array.isArray(computed.fillet.radii)
                    ? computed.fillet.radii.join(',')
                    : computed.fillet.radii;
            }

            const precisionInput = card.querySelector(`[name="shapes[${index}].fillet.precision"]`);
            if (precisionInput && computed.fillet.precision !== undefined) {
                precisionInput.value = computed.fillet.precision;
            }

            const convexInput = card.querySelector(`[name="shapes[${index}].fillet.convex_radius"]`);
            if (convexInput && computed.fillet.convex_radius !== undefined) {
                convexInput.value = computed.fillet.convex_radius;
            }

            const concaveInput = card.querySelector(`[name="shapes[${index}].fillet.concave_radius"]`);
            if (concaveInput && computed.fillet.concave_radius !== undefined) {
                concaveInput.value = computed.fillet.concave_radius;
            }
        }

        if (computed.zoom !== undefined) {
            const zoomInput = card.querySelector(`[name="shapes[${index}].zoom"]`);
            if (zoomInput) zoomInput.value = computed.zoom;
        }

        if (computed._metadata !== undefined) {
            const metadataInput = card.querySelector(`[name="shapes[${index}]._metadata"]`);
            if (metadataInput) {
                metadataInput.value = typeof computed._metadata === 'object'
                    ? JSON.stringify(computed._metadata)
                    : computed._metadata;
            }
        }

        if (shape.type === 'rings') {
            const overrideWidth = shape.derivation?.overrides?.ring_width?.value;
            const overrideSpace = shape.derivation?.overrides?.ring_space?.value;
            const overrideNum = shape.derivation?.overrides?.ring_num?.value;

            const ringWidthInput = card.querySelector(`[name="shapes[${index}].ring_width"]`);
            if (ringWidthInput) {
                const value = overrideWidth ?? computed.ring_width ?? shape.ring_width;
                if (value !== undefined) {
                    ringWidthInput.value = value.toString();
                }
            }

            const ringSpaceInput = card.querySelector(`[name="shapes[${index}].ring_space"]`);
            if (ringSpaceInput) {
                const value = overrideSpace ?? computed.ring_space ?? shape.ring_space;
                if (value !== undefined) {
                    ringSpaceInput.value = value.toString();
                }
            }

            const ringNumInput = card.querySelector(`[name="shapes[${index}].ring_num"]`);
            if (ringNumInput) {
                const value = overrideNum ?? computed.ring_num ?? shape.ring_num;
                if (value !== undefined) {
                    ringNumInput.value = value;
                }
            }
        }

        const metadata = computed._metadata || shape._metadata;
        if (metadata?.source === 'circle') {
            const geometrySelect = card.querySelector('.geometry-type-select');
            const verticesContainer = card.querySelector('.vertices-container');
            const circleContainer = card.querySelector('.circle-params-container');

            if (geometrySelect) {
                geometrySelect.value = 'circle';
            }
            if (verticesContainer) {
                verticesContainer.style.display = 'none';
            }
            if (circleContainer) {
                circleContainer.style.display = 'block';
            }

            const params = metadata.params || {};
            const centerXInput = card.querySelector(`[name="shapes[${index}].circle.center_x"]`);
            const centerYInput = card.querySelector(`[name="shapes[${index}].circle.center_y"]`);
            const radiusInput = card.querySelector(`[name="shapes[${index}].circle.radius"]`);
            const segmentsInput = card.querySelector(`[name="shapes[${index}].circle.segments"]`);

            if (centerXInput) centerXInput.value = params.center_x ?? 0;
            if (centerYInput) centerYInput.value = params.center_y ?? 0;
            if (radiusInput) radiusInput.value = params.radius ?? 0;
            if (segmentsInput) segmentsInput.value = params.segments ?? 64;
        } else {
            const geometrySelect = card.querySelector('.geometry-type-select');
            const verticesContainer = card.querySelector('.vertices-container');
            const circleContainer = card.querySelector('.circle-params-container');

            if (geometrySelect) {
                geometrySelect.value = 'vertices';
            }
            if (verticesContainer) {
                verticesContainer.style.display = 'block';
            }
            if (circleContainer) {
                circleContainer.style.display = 'none';
            }
        }

        if (overrideManager) {
            overrideManager.isSystemUpdate = false;
        }
    },

    // 静默刷新 JSON 编辑器与 YAML 预览
    updateJSONEditorSilently() {
        if (typeof jsonEditor !== 'undefined' && jsonEditor && typeof jsonEditor.set === 'function') {
            const options = jsonEditor.options || {};
            const originalOnChange = options.onChangeJSON;
            if (jsonEditor.options) {
                jsonEditor.options.onChangeJSON = null;
            }

            try {
                jsonEditor.set(this.getConfig());
            } catch (error) {
                LinkageCore.log('error', 'JSON 编辑器更新失败', error);
            }

            if (jsonEditor.options) {
                jsonEditor.options.onChangeJSON = originalOnChange;
            }
        }

        if (typeof updateYAMLPreview === 'function') {
            try {
                updateYAMLPreview();
            } catch (error) {
                LinkageCore.log('error', 'YAML 预览更新失败', error);
            }
        }
    },

    // 调整派生参数，避免旧值覆盖继承
    normalizeDerivedShapeData(shape, propertyPath, baseValue) {
        const derivation = shape?.derivation;
        if (!derivation) {
            return;
        }

        const deriveParams = derivation.derive_params;
        if (!deriveParams || typeof deriveParams !== 'object') {
            return;
        }

        const rootKey = propertyPath.split('.')[0];
        if (!Object.prototype.hasOwnProperty.call(deriveParams, rootKey)) {
            return;
        }

        window.__linkageDebugCounters = window.__linkageDebugCounters || {};
        window.__linkageDebugCounters.normalizeDerivedShapeData = (window.__linkageDebugCounters.normalizeDerivedShapeData || 0) + 1;
        const normalizeCallId = window.__linkageDebugCounters.normalizeDerivedShapeData;

        const normalizeEntry = {
            phase: 'normalizeDerivedShapeData',
            callId: normalizeCallId,
            shapeId: shape.id,
            shapeName: shape.name,
            propertyPath,
            incomingBaseValue: baseValue,
            currentDeriveValue: deriveParams[rootKey]
        };
        window.__linkageDebugLog = window.__linkageDebugLog || [];

        if (baseValue === undefined) {
            delete deriveParams[rootKey];
            normalizeEntry.action = 'delete';
            LinkageCore.log('debug', `移除派生参数: ${shape.name}.${rootKey}`);
        } else {
            deriveParams[rootKey] = baseValue;
            normalizeEntry.action = 'sync';
            LinkageCore.log('debug', `同步派生参数: ${shape.name}.${rootKey} = ${JSON.stringify(baseValue)}`);
        }

        window.__linkageDebugLog.push(normalizeEntry);
        LinkageCore.log('info', '[DEBUG] normalizeDerivedShapeData', normalizeEntry);
    },

    // 维护 _computed 缓存，便于测试读取
    updateComputedCache(shape, propertyPath, baseValue) {
        shape._computed = shape._computed || {};

        if (baseValue === undefined) {
            const keys = propertyPath.split('.');
            const last = keys.pop();
            const target = keys.reduce((current, key) => current?.[key], shape._computed);
            if (target && Object.prototype.hasOwnProperty.call(target, last)) {
                delete target[last];
            }
            return;
        }

        LinkageCore.setNestedProperty(shape._computed, propertyPath, baseValue);
    },

    // 批量同步所有派生形状（供需要时使用）
    syncAllDerivedShapes() {
        const activeConfig = this.getConfig();
        const shapes = activeConfig.shapes || [];
        LinkageIdManager.buildIdMap(shapes);

        shapes.forEach((shape, index) => {
            if (!shape?.derivation) {
                return;
            }

            const resolved = LinkagePropertyResolver.resolveShapeProperties(shape);
            activeConfig.shapes[index] = resolved;
            this.updateShapeCardDisplay(index, resolved);
        });

        this.updateJSONEditorSilently();
    },

    // 强制刷新某个派生形状
    forceRecalculateShape(shapeIndex) {
        const activeConfig = this.getConfig();
        const shapes = activeConfig.shapes || [];
        const shape = shapes[shapeIndex];
        if (!shape) {
            LinkageCore.log('warn', `形状不存在: 索引${shapeIndex}`);
            return;
        }

        if (!shape.derivation) {
            LinkageCore.log('debug', `形状不是派生形状: ${shape.name}`);
            return;
        }

        const resolved = LinkagePropertyResolver.resolveShapeProperties(shape);
        activeConfig.shapes[shapeIndex] = resolved;
        this.updateShapeCardDisplay(shapeIndex, resolved);
        this.updateJSONEditorSilently();
    }
};
