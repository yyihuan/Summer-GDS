// 全局变量
let jsonEditor;
let currentShapeIndex = 0;
let config = {
    global: {
        dbu: 0.001,
        fillet: {
            interactive: false,
            default_action: "auto",
            precision: 0.01
        },
        layer_mapping: {
            save: true,
            file: "layer_mapping.txt"
        }
    },
    gds: {
        input_file: null,
        output_file: "output.gds",
        cell_name: "TOP",
        default_layer: [1, 0]
    },
    shapes: []
};

// 在页面加载完成后执行
document.addEventListener('DOMContentLoaded', function() {
    console.log('页面加载完成，初始化应用...');
    
    // 初始化JSON编辑器
    const container = document.getElementById('jsonEditor');
    const options = {
        mode: 'tree',
        modes: ['tree', 'view', 'form', 'code', 'text'],
        onChangeJSON: function(newJSON) {
            config = newJSON;
            updateFormFromJSON();
            updateYAMLPreview();
        }
    };
    jsonEditor = new JSONEditor(container, options, config);
    console.log('JSON编辑器初始化完成');

    // 绑定事件处理函数
    document.getElementById('addShapeBtn').addEventListener('click', showShapeTypeModal);
    document.getElementById('saveConfigBtn').addEventListener('click', saveConfig);
    document.getElementById('loadConfigBtn').addEventListener('click', loadConfig);
    document.getElementById('validateBtn').addEventListener('click', validateConfig);
    document.getElementById('generateBtn').addEventListener('click', generateGDS);
    document.getElementById('configFileInput').addEventListener('change', handleFileUpload);
    console.log('按钮事件绑定完成');

    // 绑定表单变化事件
    document.getElementById('configForm').addEventListener('change', updateJSONFromForm);
    
    // 绑定形状类型选择按钮
    document.querySelectorAll('#shapeTypeModal button[data-shape-type]').forEach(button => {
        button.addEventListener('click', function() {
            const shapeType = this.getAttribute('data-shape-type');
            addShape(shapeType);
            hideModal('shapeTypeModal');
        });
    });
    
    // 初始化显示
    updateYAMLPreview();
    
    // 初始绑定倒角半径切换按钮事件
    console.log('开始绑定倒角半径切换按钮事件...');
    setTimeout(() => {
        bindRadiusListToggleEvents();
        console.log('倒角半径切换按钮事件绑定完成（延迟执行）');
    }, 500);
    
    // 重新绑定"确认添加Via"按钮事件
    const confirmAddViaBtn = document.getElementById('confirmAddViaBtn');
    if (confirmAddViaBtn) {
        console.log('找到确认添加Via按钮，正在绑定事件...');
        confirmAddViaBtn.addEventListener('click', function(e) {
            console.log('确认添加Via按钮被点击');
            confirmAddVia();
        });
    } else {
        console.error('未找到确认添加Via按钮！');
    }
    
    console.log('确认添加Via按钮事件绑定完成');
    
    console.log('应用初始化完成');
});

// 显示形状类型选择模态框
function showShapeTypeModal() {
    const modal = new bootstrap.Modal(document.getElementById('shapeTypeModal'));
    modal.show();
}

// 隐藏模态框
function hideModal(modalId) {
    const modalElement = document.getElementById(modalId);
    const modal = bootstrap.Modal.getInstance(modalElement);
    modal.hide();
}

// 添加新形状
function addShape(shapeType) {
    // 创建新形状配置
    const newShape = {
        type: shapeType,
        name: shapeType === 'polygon' ? `多边形${currentShapeIndex}` : `环阵列${currentShapeIndex}`,
        layer: JSON.parse(JSON.stringify(config.gds.default_layer)),
        vertices: "",
        fillet: {
            type: "arc",
            radius: 1
        },
        zoom: 0
    };
    
    // 环阵列特有属性
    if (shapeType === 'rings') {
        // 保持为字符串，方便后端灵活解析
        newShape.ring_width = "1";
        newShape.ring_space = "1";
        newShape.ring_num = 3;
    }
    
    // 添加到配置中
    config.shapes.push(newShape);
    
    // 渲染形状卡片
    renderShapeCard(newShape, config.shapes.length - 1);
    
    // 更新JSON编辑器和YAML预览
    jsonEditor.set(config);
    updateYAMLPreview();
    
    // 增加索引计数
    currentShapeIndex++;
    
    // 绑定倒角半径列表切换按钮事件
    bindRadiusListToggleEvents();
}

// 渲染形状卡片
function renderShapeCard(shape, index) {
    console.log(`渲染形状卡片: 索引=${index}, 类型=${shape.type}, 名称=${shape.name}`);
    
    const container = document.getElementById('shapesContainer');
    let templateId;
    if (shape.type === 'polygon') {
        templateId = 'polygonShapeTemplate';
    } else if (shape.type === 'rings') {
        templateId = 'ringsShapeTemplate';
    } else if (shape.type === 'via') { // 新增对 via 类型的处理
        templateId = 'viaShapeTemplate';
    } else {
        console.error('未知的形状类型:', shape.type);
        return;
    }
    
    const template = document.getElementById(templateId).innerHTML;
    let cardHtml = template.replace(/{index}/g, index);

    // 如果是 via 类型，需要填充额外的模板变量
    if (shape.type === 'via' && shape.base_shape_info) {
        cardHtml = cardHtml.replace(/{base_shape_name}/g, shape.base_shape_info.name || '未知基础图形')
                          .replace(/{base_vertices}/g, shape.base_shape_info.vertices || '无顶点信息')
                          .replace(/{base_fillet_type}/g, shape.base_shape_info.fillet_type || 'none')
                          .replace(/{base_fillet_radius}/g, shape.base_shape_info.fillet_radius || '')
                          .replace(/{base_fillet_precision}/g, shape.base_shape_info.fillet_precision || '')
                          .replace(/{base_fillet_convex_radius}/g, shape.base_shape_info.fillet_convex_radius || '')
                          .replace(/{base_fillet_concave_radius}/g, shape.base_shape_info.fillet_concave_radius || '');
        
        let filletTypeDisplay = 'N/A';
        let filletParamsDisplay = 'N/A';
        if (shape.base_shape_info.fillet_type) {
            filletTypeDisplay = shape.base_shape_info.fillet_type;
            if (shape.base_shape_info.fillet_type === 'arc' && shape.base_shape_info.fillet_radius !== undefined) {
                filletParamsDisplay = `半径: ${shape.base_shape_info.fillet_radius}`;
            } else if (shape.base_shape_info.fillet_type === 'adaptive' && shape.base_shape_info.fillet_convex_radius !== undefined) {
                filletParamsDisplay = `凸角半径: ${shape.base_shape_info.fillet_convex_radius}, 凹角半径: ${shape.base_shape_info.fillet_concave_radius}`;
            } else if (shape.base_shape_info.fillet_type === 'chamfer') {
                filletParamsDisplay = `距离: ${shape.base_shape_info.fillet_distance || '未知'}`;
            }
        }
        cardHtml = cardHtml.replace(/{base_fillet_type_display}/g, filletTypeDisplay)
                          .replace(/{base_fillet_params_display}/g, filletParamsDisplay);
    }
    
    const tempDiv = document.createElement('div');
    tempDiv.innerHTML = cardHtml;
    const cardElement = tempDiv.firstElementChild;
    
    // 如果是 via 类型，添加数据属性以存储基础形状信息
    if (shape.type === 'via' && shape.base_shape_info) {
        const nameInput = cardElement.querySelector(`[name="shapes[${index}].name"]`);
        if (nameInput) {
            nameInput.setAttribute('data-base-shape-name', shape.base_shape_info.name);
        }
        const verticesInput = cardElement.querySelector(`[name="shapes[${index}].vertices"]`);
        if (verticesInput) {
            verticesInput.setAttribute('data-base-vertices', shape.base_shape_info.vertices);
        }
    }
    
    fillShapeFormValues(cardElement, shape, index);
    
    container.appendChild(cardElement);
    console.log(`形状卡片已添加到DOM: 索引=${index}, 类型=${shape.type}`);
    
    // 绑定事件处理程序
    bindShapeCardEvents(cardElement, shape, index);
}

// 新增函数：绑定形状卡片事件
function bindShapeCardEvents(cardElement, shape, index) {
    // 绑定删除按钮事件
    const removeBtn = cardElement.querySelector('.remove-shape-btn');
    if (removeBtn) {
        removeBtn.addEventListener('click', function() {
            removeShape(index);
        });
    }
    
    // 绑定扩大/缩小按钮事件
    const offsetBtn = cardElement.querySelector('.offset-shape-btn');
    if (offsetBtn) {
        offsetBtn.addEventListener('click', function() {
            offsetShape(index);
        });
    }

    // 为 "刻孔/溅铝" 按钮绑定事件 (仅对 polygon 类型的卡片)
    if (shape.type === 'polygon') {
        const viaBtn = cardElement.querySelector('.via-shape-btn');
        if (viaBtn) {
            viaBtn.addEventListener('click', function() {
                handleViaButtonClick(index);
            });
            console.log(`刻孔/溅铝按钮事件已绑定: 索引=${index}`);
        }
    }
    
    // 绑定倒角半径列表切换按钮事件
    const toggleToListBtn = cardElement.querySelector('.toggle-radius-list-btn');
    if (toggleToListBtn) {
        toggleToListBtn.addEventListener('click', function(event) {
            console.log(`点击切换到半径列表按钮: 索引=${index}`);
            toggleToRadiusList(event);
        });
    }
    
    const toggleToSingleBtn = cardElement.querySelector('.toggle-single-radius-btn');
    if (toggleToSingleBtn) {
        toggleToSingleBtn.addEventListener('click', function(event) {
            console.log(`点击切换到单一半径按钮: 索引=${index}`);
            toggleToSingleRadius(event);
        });
    }
    
    // 为所有输入框添加 change 事件监听器
    cardElement.querySelectorAll('input, select, textarea').forEach(input => {
        input.addEventListener('change', function() {
            console.log(`输入框值改变: ${input.name}`);
            updateJSONFromForm();
        });
    });

    // 绑定几何类型切换事件
    const geometrySelect = cardElement.querySelector('.geometry-type-select');
    if (geometrySelect) {
        geometrySelect.addEventListener('change', function(e) {
            const geometryType = e.target.value;
            console.log(`几何类型切换到: ${geometryType}, 形状索引: ${index}`);
            toggleGeometryInputs(index, geometryType);
        });
    }

    // 绑定圆形参数输入事件
    const circleInputs = cardElement.querySelectorAll('.circle-params-container input');
    circleInputs.forEach(input => {
        input.addEventListener('input', function() {
            console.log('圆形参数变更:', input.name, input.value);
            // 实时更新顶点（防抖处理）
            clearTimeout(input.updateTimeout);
            input.updateTimeout = setTimeout(() => {
                updateVerticesFromCircle(index);
            }, 300);
        });
    });
}

// 填充形状表单值
function fillShapeFormValues(cardElement, shape, index) {
    // 设置名称
    cardElement.querySelector(`[name="shapes[${index}].name"]`).value = shape.name || '';
    
    // 设置图层
    if (shape.layer && Array.isArray(shape.layer)) {
        const layer0Input = cardElement.querySelector(`[name="shapes[${index}].layer[0]"]`);
        if(layer0Input) layer0Input.value = shape.layer[0];
        const layer1Input = cardElement.querySelector(`[name="shapes[${index}].layer[1]"]`);
        if(layer1Input) layer1Input.value = shape.layer[1];
    }
    
    // 设置顶点
    if (shape.type === 'polygon' || shape.type === 'rings') {
        if (shape.vertices) {
            const verticesInput = cardElement.querySelector(`[name="shapes[${index}].vertices"]`);
            if(verticesInput) verticesInput.value = shape.vertices;
        }
        if (shape.zoom !== undefined) {
            const zoomInput = cardElement.querySelector(`[name="shapes[${index}].zoom"]`);
            if(zoomInput) zoomInput.value = shape.zoom;
        }
    } else if (shape.type === 'via') { // via 类型的顶点是只读的，从 base_vertices 填充
        const verticesTextarea = cardElement.querySelector(`[name="shapes[${index}].vertices"]`);
        if (verticesTextarea && shape.base_shape_info && shape.base_shape_info.vertices) {
            verticesTextarea.value = shape.base_shape_info.vertices;
        }
    }
    
    // 设置倒角
    if (shape.fillet && (shape.type === 'polygon' || shape.type === 'rings')) {
        const filletTypeSelect = cardElement.querySelector(`[name="shapes[${index}].fillet.type"]`);
        if (filletTypeSelect && shape.fillet.type) {
            filletTypeSelect.value = shape.fillet.type;
        }
        
        const radiusInput = cardElement.querySelector(`[name="shapes[${index}].fillet.radius"]`);
        if (radiusInput && shape.fillet.radius !== undefined) {
            radiusInput.value = shape.fillet.radius;
        }
        
        // 设置半径列表
        if (shape.fillet.radii) {
            const radiusListContainer = cardElement.querySelector(`.radius-list-container[data-shape-index="${index}"]`);
            const radiiInput = cardElement.querySelector(`[name="shapes[${index}].fillet.radii"]`);
            if (radiusListContainer && radiiInput) {
                // 显示半径列表容器，隐藏单一半径输入框
                radiusListContainer.style.display = 'flex';
                const singleRadiusRow = radiusListContainer.previousElementSibling;
                if (singleRadiusRow) {
                    singleRadiusRow.style.display = 'none';
                }
                
                // 设置半径列表值
                radiiInput.value = Array.isArray(shape.fillet.radii) ? 
                    shape.fillet.radii.join(',') : 
                    shape.fillet.radii;
            }
        }
    } else if (shape.type === 'via' && shape.base_shape_info) { // via 的倒角信息通过 hidden input 填充
        const filletTypeInput = cardElement.querySelector(`[name="shapes[${index}].fillet.type"]`);
        if(filletTypeInput) filletTypeInput.value = shape.base_shape_info.fillet_type || 'none';
        
        const radiusInput = cardElement.querySelector(`[name="shapes[${index}].fillet.radius"]`);
        if(radiusInput) radiusInput.value = shape.base_shape_info.fillet_radius || '';

        const precisionInput = cardElement.querySelector(`[name="shapes[${index}].fillet.precision"]`);
        if(precisionInput) precisionInput.value = shape.base_shape_info.fillet_precision || '0.01';

        const convexRadiusInput = cardElement.querySelector(`[name="shapes[${index}].fillet.convex_radius"]`);
        if(convexRadiusInput) convexRadiusInput.value = shape.base_shape_info.fillet_convex_radius || '';

        const concaveRadiusInput = cardElement.querySelector(`[name="shapes[${index}].fillet.concave_radius"]`);
        if(concaveRadiusInput) concaveRadiusInput.value = shape.base_shape_info.fillet_concave_radius || '';
    }
    
    // 环阵列特有属性
    if (shape.type === 'rings') {
        const ringWidthInput = cardElement.querySelector(`[name="shapes[${index}].ring_width"]`);
        const ringSpaceInput = cardElement.querySelector(`[name="shapes[${index}].ring_space"]`);
        const ringNumInput = cardElement.querySelector(`[name="shapes[${index}].ring_num"]`);

        if (ringWidthInput && shape.ring_width !== undefined) {
            // 直接显示字符串
            ringWidthInput.value = shape.ring_width.toString();
        }

        if (ringSpaceInput && shape.ring_space !== undefined) {
            // 直接显示字符串
            ringSpaceInput.value = shape.ring_space.toString();
        }

        if (ringNumInput && shape.ring_num !== undefined) {
            ringNumInput.value = shape.ring_num;
        }
    } else if (shape.type === 'via') {
        const innerZoomInput = cardElement.querySelector(`[name="shapes[${index}].inner_zoom"]`);
        if(innerZoomInput && shape.inner_zoom !== undefined) innerZoomInput.value = shape.inner_zoom;

        const outerZoomInput = cardElement.querySelector(`[name="shapes[${index}].outer_zoom"]`);
        if(outerZoomInput && shape.outer_zoom !== undefined) outerZoomInput.value = shape.outer_zoom;
    }

    // 恢复几何类型和圆形参数（基于元数据）
    if (shape.type === 'polygon' || shape.type === 'rings') {
        const geometrySelect = cardElement.querySelector('.geometry-type-select');
        if (geometrySelect && shape._metadata) {
            if (shape._metadata.source === 'circle') {
                console.log(`恢复圆形状态: 形状${index}, 元数据:`, shape._metadata);

                // 设置为圆形模式
                geometrySelect.value = 'circle';

                // 恢复圆形参数
                const params = shape._metadata.params;
                if (params) {
                    const centerXInput = cardElement.querySelector('[name*="center_x"]');
                    const centerYInput = cardElement.querySelector('[name*="center_y"]');
                    const radiusInput = cardElement.querySelector('[name*="radius"]');
                    const segmentsInput = cardElement.querySelector('[name*="segments"]');

                    if (centerXInput) centerXInput.value = params.center_x !== undefined ? params.center_x : 0;
                    if (centerYInput) centerYInput.value = params.center_y !== undefined ? params.center_y : 0;
                    if (radiusInput) radiusInput.value = params.radius || 10;
                    if (segmentsInput) segmentsInput.value = params.segments || 64;
                }

                // 切换UI显示到圆形模式
                setTimeout(() => toggleGeometryInputs(index, 'circle'), 100);
            } else {
                // 默认为顶点模式
                geometrySelect.value = 'vertices';
                setTimeout(() => toggleGeometryInputs(index, 'vertices'), 100);
            }
        } else {
            // 没有元数据，默认为顶点模式
            if (geometrySelect) {
                geometrySelect.value = 'vertices';
                setTimeout(() => toggleGeometryInputs(index, 'vertices'), 100);
            }
        }
    }
}

// 移除形状
function removeShape(indexToRemove) {
    console.log('尝试删除形状，索引:', indexToRemove);
    if (indexToRemove >= 0 && indexToRemove < config.shapes.length) {
        config.shapes.splice(indexToRemove, 1);
        console.log('形状已从配置中删除:', config.shapes);
        
        // 重新渲染所有卡片
        refreshShapesContainer();
        
        jsonEditor.set(config);
        updateYAMLPreview();
        showAlert('形状已删除', 'info');
    } else {
        console.error('删除形状失败：无效的索引', indexToRemove);
        showAlert('删除形状失败：无效的索引', 'danger');
    }
}

// 刷新形状容器
function refreshShapesContainer() {
    const container = document.getElementById('shapesContainer');
    container.innerHTML = '';
    currentShapeIndex = 0; // 重置全局索引计数器，因为我们要重新生成所有卡片
    config.shapes.forEach((shape, index) => {
        // 临时将 currentShapeIndex 设置为当前卡片的索引，以便 renderShapeCard 和 fillShapeFormValues 正确工作
        // 注意：这种方式依赖于 renderShapeCard 不会异步修改 currentShapeIndex
        // 一个更健壮的方法是让 renderShapeCard 直接接受并使用传入的 index
        // currentShapeIndex = index; // 这行可能不需要了，因为 addShape 已经管理了 currentShapeIndex
                                 // 并且 renderShapeCard 现在直接使用传入的 index
        renderShapeCard(shape, index); // 使用正确的当前索引
        // 在 addShape 和其他地方，确保 currentShapeIndex 是 config.shapes.length
    });
     // 确保 currentShapeIndex 是下一个新图形的正确索引
    currentShapeIndex = config.shapes.length;
}

// 从表单更新JSON
function updateJSONFromForm() {
    console.log('从表单更新JSON...');
    
    // 更新全局设置
    config.global.dbu = parseFloat(document.getElementById('dbu').value);
    config.global.fillet.precision = parseFloat(document.getElementById('filletPrecision').value);
    config.global.fillet.interactive = document.getElementById('filletInteractive').checked;
    config.global.fillet.default_action = document.getElementById('filletDefaultAction').value;
    
    // 更新GDS设置
    config.gds.output_file = document.getElementById('outputFile').value;
    config.gds.cell_name = document.getElementById('cellName').value;
    config.gds.default_layer = [
        parseInt(document.getElementById('defaultLayerNum').value),
        parseInt(document.getElementById('defaultDatatype').value)
    ];
    
    // 更新形状列表
    const shapesContainer = document.getElementById('shapesContainer');
    const shapeCards = shapesContainer.querySelectorAll('.shape-card');
    config.shapes = [];
    
    shapeCards.forEach((card, index) => {
        const shapeIndex = card.getAttribute('data-shape-index');
        const shapeType = card.querySelector(`[name="shapes[${shapeIndex}].type"]`).value;
        
        const shape = {
            type: shapeType,
            name: card.querySelector(`[name="shapes[${shapeIndex}].name"]`).value,
            layer: [
                parseInt(card.querySelector(`[name="shapes[${shapeIndex}].layer[0]"]`).value),
                parseInt(card.querySelector(`[name="shapes[${shapeIndex}].layer[1]"]`).value)
            ]
        };

        // 处理不同类型形状的特定属性
        if (shapeType === 'polygon' || shapeType === 'rings') {
            shape.vertices = card.querySelector(`[name="shapes[${shapeIndex}].vertices"]`).value;
            shape.zoom = parseFloat(card.querySelector(`[name="shapes[${shapeIndex}].zoom"]`).value || 0);
            shape.fillet = {
                type: card.querySelector(`[name="shapes[${shapeIndex}].fillet.type"]`).value
            };

            // 处理倒角半径
            const radiusListContainer = card.querySelector(`.radius-list-container[data-shape-index="${shapeIndex}"]`);
            if (radiusListContainer && radiusListContainer.style.display !== 'none') {
                // 使用半径列表
                const radiiStr = card.querySelector(`[name="shapes[${shapeIndex}].fillet.radii"]`).value;
                shape.fillet.radii = radiiStr.split(',').map(r => parseFloat(r.trim()));
            } else {
                // 使用单一半径
                shape.fillet.radius = parseFloat(card.querySelector(`[name="shapes[${shapeIndex}].fillet.radius"]`).value || 0);
            }

            // 检查是否为圆形生成的形状，保存元数据
            const geometrySelect = card.querySelector('.geometry-type-select');
            if (geometrySelect && geometrySelect.value === 'circle') {
                // 获取圆形参数，确保圆心坐标默认为0
                const centerXInput = card.querySelector(`[name*="center_x"]`);
                const centerYInput = card.querySelector(`[name*="center_y"]`);
                const radiusInput = card.querySelector(`[name*="radius"]`);
                const segmentsInput = card.querySelector(`[name*="segments"]`);

                const centerX = centerXInput ? (parseFloat(centerXInput.value) || 0) : 0;
                const centerY = centerYInput ? (parseFloat(centerYInput.value) || 0) : 0;
                const radius = radiusInput ? parseFloat(radiusInput.value) : 0;
                const segments = segmentsInput ? (parseInt(segmentsInput.value) || 64) : 64;

                console.log(`保存圆形元数据: 索引=${shapeIndex}, 中心(${centerX}, ${centerY}), 半径=${radius}, 精度=${segments}`);

                // 保存元数据
                shape._metadata = {
                    source: 'circle',
                    params: {
                        center_x: centerX,
                        center_y: centerY,
                        radius: radius,
                        segments: segments
                    },
                    generated_at: new Date().toISOString(),
                    version: '1.0'
                };
            } else {
                // 如果不是圆形，标记为顶点源
                shape._metadata = {
                    source: 'vertices',
                    generated_at: new Date().toISOString(),
                    version: '1.0'
                };
            }
            
            // 环阵列特有属性
            if (shapeType === 'rings') {
                // 直接将字符串保存到配置中，保持原貌，方便后端解析
                const ringWidthStr = card.querySelector(`[name="shapes[${shapeIndex}].ring_width"]`).value;
                shape.ring_width = ringWidthStr;

                const ringSpaceStr = card.querySelector(`[name="shapes[${shapeIndex}].ring_space"]`).value;
                shape.ring_space = ringSpaceStr;
                
                shape.ring_num = parseInt(card.querySelector(`[name="shapes[${shapeIndex}].ring_num"]`).value);
            }
        } else if (shapeType === 'via') {
            // Via 特有属性
            shape.vertices = card.querySelector(`[name="shapes[${shapeIndex}].vertices"]`).value;
            shape.inner_zoom = parseFloat(card.querySelector(`[name="shapes[${shapeIndex}].inner_zoom"]`).value);
            shape.outer_zoom = parseFloat(card.querySelector(`[name="shapes[${shapeIndex}].outer_zoom"]`).value);
            
            // 保存基础形状信息
            shape.base_shape_info = {
                name: card.querySelector(`[data-base-shape-name]`)?.getAttribute('data-base-shape-name') || '未知基础图形',
                vertices: card.querySelector(`[data-base-vertices]`)?.getAttribute('data-base-vertices') || '',
                fillet_type: card.querySelector(`[name="shapes[${shapeIndex}].fillet.type"]`).value,
                fillet_radius: parseFloat(card.querySelector(`[name="shapes[${shapeIndex}].fillet.radius"]`).value || '0'),
                fillet_precision: parseFloat(card.querySelector(`[name="shapes[${shapeIndex}].fillet.precision"]`).value || '0.01'),
                fillet_convex_radius: parseFloat(card.querySelector(`[name="shapes[${shapeIndex}].fillet.convex_radius"]`).value || '0'),
                fillet_concave_radius: parseFloat(card.querySelector(`[name="shapes[${shapeIndex}].fillet.concave_radius"]`).value || '0')
            };
            
            // 复制倒角配置
            shape.fillet = {
                type: shape.base_shape_info.fillet_type,
                radius: shape.base_shape_info.fillet_radius,
                precision: shape.base_shape_info.fillet_precision
            };
            
            if (shape.base_shape_info.fillet_type === 'adaptive') {
                shape.fillet.convex_radius = shape.base_shape_info.fillet_convex_radius;
                shape.fillet.concave_radius = shape.base_shape_info.fillet_concave_radius;
            }
        }
        
        config.shapes.push(shape);
    });
    
    // 更新JSON编辑器和YAML预览
    jsonEditor.set(config);
    updateYAMLPreview();
    console.log('JSON更新完成');
}

// 从JSON更新表单
function updateFormFromJSON() {
    // 设置全局配置
    document.getElementById('dbu').value = config.global.dbu;
    document.getElementById('filletPrecision').value = config.global.fillet.precision;
    document.getElementById('filletInteractive').checked = config.global.fillet.interactive;
    document.getElementById('filletDefaultAction').value = config.global.fillet.default_action;
    
    // 设置GDS配置
    document.getElementById('outputFile').value = config.gds.output_file;
    document.getElementById('cellName').value = config.gds.cell_name;
    document.getElementById('defaultLayerNum').value = config.gds.default_layer[0];
    document.getElementById('defaultDatatype').value = config.gds.default_layer[1];
    
    // 刷新形状容器
    refreshShapesContainer();
}

// 更新YAML预览
function updateYAMLPreview() {
    const yamlText = jsyaml.dump(config);
    document.getElementById('previewContainer').textContent = yamlText;
}

// 保存配置
function saveConfig() {
    // 弹出提示框，获取文件名
    const filename = prompt('请输入配置文件名', 'config.yaml');
    if (!filename) return;
    
    // 发送请求保存配置
    fetch('/api/save-config', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            filename: filename,
            config: config
        })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            // 创建下载链接
            const downloadLink = document.createElement('a');
            downloadLink.href = data.file_path;
            downloadLink.download = filename;
            document.body.appendChild(downloadLink);
            downloadLink.click();
            document.body.removeChild(downloadLink);
            
            showAlert('保存成功', 'success');
        } else {
            showAlert(`保存失败: ${data.error}`, 'danger');
        }
    })
    .catch(error => {
        showAlert(`保存失败: ${error}`, 'danger');
    });
}

// 加载配置
function loadConfig() {
    // 触发文件选择
    document.getElementById('configFileInput').click();
}

// 处理文件上传
function handleFileUpload(event) {
    const file = event.target.files[0];
    if (!file) return;
    
    // 创建表单数据
    const formData = new FormData();
    formData.append('file', file);
    
    // 发送请求加载配置
    fetch('/api/load-config', {
        method: 'POST',
        body: formData
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            // 更新配置
            config = data.config;
            
            // 更新JSON编辑器
            jsonEditor.set(config);
            
            // 更新表单和YAML预览
            updateFormFromJSON();
            updateYAMLPreview();
            
            showAlert('配置加载成功', 'success');
        } else {
            showAlert(`配置加载失败: ${data.error}`, 'danger');
        }
    })
    .catch(error => {
        showAlert(`配置加载失败: ${error}`, 'danger');
    });
}

// 验证配置
function validateConfig() {
    // 显示加载提示
    showAlert('正在验证配置...', 'info', false);
    
    // 发送请求验证配置
    fetch('/api/validate-config', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify(config)
    })
    .then(response => response.json())
    .then(data => {
        if (data.valid) {
            showAlert('配置验证通过', 'success');
        } else {
            showAlert(`配置验证失败: ${data.errors.join(', ')}`, 'danger');
        }
    })
    .catch(error => {
        showAlert(`配置验证失败: ${error}`, 'danger');
    });
}

// 生成GDS文件
function generateGDS() {
    // 显示加载提示
    showAlert('正在生成GDS文件...', 'info', false);
    
    // 发送请求生成GDS
    fetch('/api/generate-gds', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify(config)
    })
    .then(response => {
        // 检查响应状态
        if (!response.ok) {
            return response.json().then(data => {
                throw new Error(data.error || '生成GDS文件失败');
            });
        }
        
        // 获取文件名
        const contentDisposition = response.headers.get('Content-Disposition');
        let filename = 'output.gds';
        if (contentDisposition) {
            const matches = /filename[^;=\n]*=((['"]).*?\2|[^;\n]*)/.exec(contentDisposition);
            if (matches && matches[1]) {
                filename = matches[1].replace(/['"]/g, '');
            }
        }
        
        // 下载文件
        return response.blob().then(blob => {
            const url = window.URL.createObjectURL(blob);
            const downloadLink = document.createElement('a');
            downloadLink.href = url;
            downloadLink.download = filename;
            document.body.appendChild(downloadLink);
            downloadLink.click();
            window.URL.revokeObjectURL(url);
            document.body.removeChild(downloadLink);
            
            showAlert('GDS文件生成成功', 'success');
        });
    })
    .catch(error => {
        showAlert(`GDS文件生成失败: ${error}`, 'danger');
    });
}

// 绑定倒角半径列表切换按钮事件
function bindRadiusListToggleEvents() {
    // 获取所有切换按钮
    const listButtons = document.querySelectorAll('.toggle-radius-list-btn');
    const singleButtons = document.querySelectorAll('.toggle-single-radius-btn');
    
    console.log(`找到 ${listButtons.length} 个切换到列表按钮和 ${singleButtons.length} 个切换到单一半径按钮`);
    
    // 绑定切换到半径列表按钮
    listButtons.forEach(button => {
        button.removeEventListener('click', toggleToRadiusList);
        button.addEventListener('click', toggleToRadiusList);
        console.log(`绑定切换到列表按钮: ${button.getAttribute('data-shape-index')}`);
    });
    
    // 绑定切换到单一半径按钮
    singleButtons.forEach(button => {
        button.removeEventListener('click', toggleToSingleRadius);
        button.addEventListener('click', toggleToSingleRadius);
        console.log(`绑定切换到单一半径按钮: ${button.getAttribute('data-shape-index')}`);
    });
}

// 切换到半径列表显示
function toggleToRadiusList(event) {
    const shapeIndex = event.currentTarget.getAttribute('data-shape-index');
    console.log(`切换到半径列表: 形状索引 ${shapeIndex}`);
    
    const singleRadiusRow = event.currentTarget.closest('.row');
    const radiusListContainer = document.querySelector(`.radius-list-container[data-shape-index="${shapeIndex}"]`);
    
    if (!radiusListContainer) {
        console.error(`未找到半径列表容器: [data-shape-index="${shapeIndex}"]`);
        return;
    }
    
    // 隐藏单一半径输入框，显示半径列表输入框
    singleRadiusRow.style.display = 'none';
    radiusListContainer.style.display = 'flex';
    console.log('显示切换成功');
    
    // 从单一半径生成初始半径列表
    const singleRadius = document.querySelector(`[name="shapes[${shapeIndex}].fillet.radius"]`).value;
    const verticesInput = document.querySelector(`[name="shapes[${shapeIndex}].vertices"]`);
    let vertexCount = 0;
    
    if (verticesInput && verticesInput.value) {
        // 计算顶点数量
        vertexCount = verticesInput.value.split(':').length;
    }
    
    // 生成相同数量的半径值
    if (vertexCount > 0) {
        const radiusList = Array(vertexCount).fill(singleRadius).join(',');
        document.querySelector(`[name="shapes[${shapeIndex}].fillet.radii"]`).value = radiusList;
        console.log(`生成半径列表: ${radiusList}`);
    }
    
    // 更新JSON
    updateJSONFromForm();
}

// 切换到单一半径显示
function toggleToSingleRadius(event) {
    const shapeIndex = event.currentTarget.getAttribute('data-shape-index');
    console.log(`切换到单一半径: 形状索引 ${shapeIndex}`);
    
    const radiusListContainer = event.currentTarget.closest('.radius-list-container');
    const singleRadiusRow = radiusListContainer.previousElementSibling;
    
    if (!singleRadiusRow) {
        console.error(`未找到单一半径行: 形状索引 ${shapeIndex}`);
        return;
    }
    
    // 隐藏半径列表输入框，显示单一半径输入框
    radiusListContainer.style.display = 'none';
    singleRadiusRow.style.display = 'flex';
    console.log('显示切换成功');
    
    // 从半径列表计算平均值作为单一半径
    const radiiInput = document.querySelector(`[name="shapes[${shapeIndex}].fillet.radii"]`);
    if (radiiInput && radiiInput.value) {
        const radiiValues = radiiInput.value.split(',').map(r => parseFloat(r.trim())).filter(r => !isNaN(r));
        if (radiiValues.length > 0) {
            const avgRadius = radiiValues.reduce((sum, r) => sum + r, 0) / radiiValues.length;
            document.querySelector(`[name="shapes[${shapeIndex}].fillet.radius"]`).value = avgRadius.toFixed(2);
            console.log(`计算平均半径: ${avgRadius.toFixed(2)}`);
        }
    }
    
    // 更新JSON
    updateJSONFromForm();
}

// 扩大/缩小形状
function offsetShape(sourceIndex) {
    console.log(`开始扩大/缩小形状: 源索引=${sourceIndex}`);
    
    // 获取源形状
    const sourceShape = config.shapes[sourceIndex];
    if (!sourceShape) {
        console.error('源形状不存在');
        showAlert('源形状不存在', 'danger');
        return;
    }
    
    // 创建新形状配置，深拷贝源形状
    const newShape = JSON.parse(JSON.stringify(sourceShape));
    
    // 修改名称
    newShape.name = `${sourceShape.name}_扩大缩小`;
    
    // 修改图层索引（默认加1）
    if (Array.isArray(newShape.layer) && newShape.layer.length > 0) {
        newShape.layer[0] = newShape.layer[0] + 1;
    }
    
    // 添加到配置中
    config.shapes.push(newShape);
    
    // 渲染形状卡片
    renderShapeCard(newShape, config.shapes.length - 1);
    
    // 更新JSON编辑器和YAML预览
    jsonEditor.set(config);
    updateYAMLPreview();
    
    // 增加索引计数
    currentShapeIndex++;
    
    // 绑定倒角半径列表切换按钮事件
    bindRadiusListToggleEvents();
    
    console.log(`形状扩大/缩小完成: 新索引=${config.shapes.length - 1}`);
    showAlert('形状扩大/缩小成功', 'success', true);
}

// 显示提示框
function showAlert(message, type, dismissible = true) {
    const alertContainer = document.getElementById('alertContainer');
    alertContainer.innerHTML = '';
    
    let alertHTML = `<div class="alert alert-${type}`;
    if (dismissible) {
        alertHTML += ' alert-dismissible fade show';
    }
    alertHTML += '" role="alert">';
    
    alertHTML += message;
    
    if (dismissible) {
        alertHTML += `<button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>`;
    }
    
    alertHTML += '</div>';
    
    alertContainer.innerHTML = alertHTML;
    alertContainer.style.display = 'block';
    
    // 自动关闭成功提示
    if (type === 'success' && dismissible) {
        setTimeout(() => {
            const alertElement = alertContainer.querySelector('.alert');
            if (alertElement) {
                const alert = bootstrap.Alert.getOrCreateInstance(alertElement);
                alert.close();
            }
        }, 3000);
    }
}

// 新增函数：处理 "刻孔/溅铝" 按钮点击
function handleViaButtonClick(baseShapeIndex) {
    console.log('刻孔/溅铝按钮点击，基础图形索引:', baseShapeIndex);
    document.getElementById('baseShapeIndexForVia').value = baseShapeIndex;
    
    const baseShape = config.shapes[baseShapeIndex];
    if (baseShape && baseShape.layer) {
        document.getElementById('viaLayerNum').value = baseShape.layer[0] || 1;
        document.getElementById('viaLayerDatatype').value = baseShape.layer[1] || 0;
    } else { // 使用GDS默认图层
        document.getElementById('viaLayerNum').value = config.gds.default_layer[0] || 1;
        document.getElementById('viaLayerDatatype').value = config.gds.default_layer[1] || 0;
    }
    // 设置默认的 zoom 值
    document.getElementById('viaInnerZoom').value = -1;
    document.getElementById('viaOuterZoom').value = 1;

    const viaModal = new bootstrap.Modal(document.getElementById('viaParamsModal'));
    viaModal.show();
}

// 新增函数：确认添加 Via 形状
function confirmAddVia() {
    console.log('confirmAddVia 函数被调用');
    const baseShapeIndex = parseInt(document.getElementById('baseShapeIndexForVia').value);
    console.log('基础图形索引:', baseShapeIndex);
    const baseShape = config.shapes[baseShapeIndex];
    console.log('基础图形:', baseShape);

    if (baseShape && baseShape.type === 'polygon') { // 确保基础图形是多边形
        const innerZoom = parseFloat(document.getElementById('viaInnerZoom').value);
        const outerZoom = parseFloat(document.getElementById('viaOuterZoom').value);
        const layerNum = parseInt(document.getElementById('viaLayerNum').value);
        const layerDatatype = parseInt(document.getElementById('viaLayerDatatype').value);

        console.log('参数值:', {
            innerZoom,
            outerZoom,
            layerNum,
            layerDatatype
        });

        if (isNaN(innerZoom) || isNaN(outerZoom) || isNaN(layerNum) || isNaN(layerDatatype)) {
            showAlert('请输入有效的缩放和图层参数!', 'danger');
            return;
        }

        const newViaShape = {
            type: "via",
            name: (baseShape.name || `多边形${baseShapeIndex}`) + "_via",
            inner_zoom: innerZoom,
            outer_zoom: outerZoom,
            layer: [layerNum, layerDatatype],
            // 深拷贝基础图形的倒角信息
            fillet: JSON.parse(JSON.stringify(baseShape.fillet || { type: 'none' })),
            // 复制顶点或顶点生成配置
        };

        if (baseShape.vertices_gen) {
            newViaShape.vertices_gen = JSON.parse(JSON.stringify(baseShape.vertices_gen));
        } else if (baseShape.vertices) {
            newViaShape.vertices = baseShape.vertices; // 顶点字符串是原始类型，直接复制
        } else {
            showAlert('基础图形缺少顶点或顶点生成信息!', 'danger');
            return; // 如果没有顶点信息，则不创建
        }
        
        // 存储用于模板渲染的基础图形信息
        newViaShape.base_shape_info = {
            name: baseShape.name || `多边形${baseShapeIndex}`,
            vertices: baseShape.vertices || (baseShape.vertices_gen ? '由配置生成' : '无顶点信息'),
            fillet_type: baseShape.fillet ? baseShape.fillet.type : 'none',
            fillet_radius: baseShape.fillet ? baseShape.fillet.radius : undefined,
            fillet_precision: baseShape.fillet ? baseShape.fillet.precision : (config.global.fillet.precision || 0.01),
            fillet_convex_radius: baseShape.fillet ? baseShape.fillet.convex_radius : undefined,
            fillet_concave_radius: baseShape.fillet ? baseShape.fillet.concave_radius : undefined,
        };

        config.shapes.push(newViaShape);
        currentShapeIndex++; // 确保下一个图形的索引是新的

        refreshShapesContainer(); // 重新渲染所有图形
        
        jsonEditor.set(config); // 更新JSON编辑器
        updateYAMLPreview(); // 更新YAML预览

        // 关闭模态框
        const viaModalElement = document.getElementById('viaParamsModal');
        const viaModal = bootstrap.Modal.getInstance(viaModalElement);
        if (viaModal) {
            viaModal.hide();
        }

        showAlert('刻孔/溅铝环已添加!', 'success');
    } else {
        showAlert('找不到有效的基础多边形图形!', 'danger');
    }
}

// ==================== 圆形支持功能 ====================

// 圆形顶点生成算法
function generateCircleVertices(centerX, centerY, radius, segments = 64) {
    console.log(`生成圆形顶点: 中心(${centerX}, ${centerY}), 半径=${radius}, 精度=${segments}`);

    if (!radius || radius <= 0) {
        throw new Error('半径必须大于0');
    }

    if (segments < 8 || segments > 256) {
        console.warn(`精度值${segments}超出范围，使用默认值64`);
        segments = 64; // 使用默认值
    }

    const vertices = [];
    for (let i = 0; i < segments; i++) {
        const angle = (2 * Math.PI * i) / segments;
        const x = centerX + radius * Math.cos(angle);
        const y = centerY + radius * Math.sin(angle);
        vertices.push(`${x.toFixed(3)},${y.toFixed(3)}`);
    }

    const result = vertices.join(':');
    console.log(`生成的顶点: ${result.substring(0, 50)}...`);
    return result;
}

// 动态表单切换逻辑
function toggleGeometryInputs(shapeIndex, geometryType) {
    console.log(`切换几何类型: 形状索引=${shapeIndex}, 类型=${geometryType}`);

    const container = document.querySelector(`[data-shape-index="${shapeIndex}"]`);
    if (!container) {
        console.error(`未找到形状容器: data-shape-index="${shapeIndex}"`);
        return;
    }

    const verticesContainer = container.querySelector('.vertices-container');
    const circleContainer = container.querySelector('.circle-params-container');

    if (!verticesContainer || !circleContainer) {
        console.error('未找到顶点容器或圆形参数容器');
        return;
    }

    if (geometryType === 'circle') {
        verticesContainer.style.display = 'none';
        circleContainer.style.display = 'block';
        console.log('已切换到圆形模式');

        // 如果圆形参数不为空，立即生成顶点
        setTimeout(() => updateVerticesFromCircle(shapeIndex), 100);
    } else {
        verticesContainer.style.display = 'block';
        circleContainer.style.display = 'none';
        console.log('已切换到顶点模式');
    }
}

// 从圆形参数更新顶点
function updateVerticesFromCircle(shapeIndex) {
    console.log(`从圆形参数更新顶点: 形状索引=${shapeIndex}`);

    const container = document.querySelector(`[data-shape-index="${shapeIndex}"]`);
    if (!container) {
        console.error(`未找到形状容器: data-shape-index="${shapeIndex}"`);
        return;
    }

    try {
        const centerXInput = container.querySelector('[name*="center_x"]');
        const centerYInput = container.querySelector('[name*="center_y"]');
        const radiusInput = container.querySelector('[name*="radius"]');
        const segmentsInput = container.querySelector('[name*="segments"]');

        const centerX = centerXInput ? (parseFloat(centerXInput.value) || 0) : 0;
        const centerY = centerYInput ? (parseFloat(centerYInput.value) || 0) : 0;
        const radius = radiusInput ? parseFloat(radiusInput.value) : 0;
        const segments = segmentsInput ? (parseInt(segmentsInput.value) || 64) : 64;

        console.log(`圆形参数: 中心(${centerX}, ${centerY}), 半径=${radius}, 精度=${segments}`);

        if (radius > 0) {
            const vertices = generateCircleVertices(centerX, centerY, radius, segments);
            const verticesInput = container.querySelector('[name*="vertices"]');
            if (verticesInput) {
                verticesInput.value = vertices;
                console.log('顶点已更新到输入框');
                updateJSONFromForm(); // 触发配置更新
            }
        }
    } catch (error) {
        console.error('圆形顶点生成失败:', error);
        showAlert(`圆形参数错误: ${error.message}`, 'danger');
    }
}

// 参数验证
function validateCircleParams(centerX, centerY, radius, segments) {
    const errors = [];

    if (isNaN(centerX) || isNaN(centerY)) {
        errors.push('圆心坐标必须是有效数字');
    }

    if (!radius || radius <= 0) {
        errors.push('半径必须大于0');
    }

    if (segments && (segments < 8 || segments > 256)) {
        errors.push('精度必须在8-256之间');
    }

    return errors;
}