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
        zoom: [0, 0]
    };
    
    // 环阵列特有属性
    if (shapeType === 'rings') {
        newShape.ring_width = 1;
        newShape.ring_space = 1;
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
    const templateId = shape.type === 'polygon' ? 'polygonShapeTemplate' : 'ringsShapeTemplate';
    const template = document.getElementById(templateId).innerHTML;
    
    // 替换模板中的索引占位符
    const cardHtml = template.replace(/{index}/g, index);
    
    // 创建临时元素以插入HTML
    const tempDiv = document.createElement('div');
    tempDiv.innerHTML = cardHtml;
    const cardElement = tempDiv.firstElementChild;
    
    // 填充表单值
    fillShapeFormValues(cardElement, shape, index);
    
    // 添加到容器
    container.appendChild(cardElement);
    console.log(`形状卡片已添加到DOM: 索引=${index}`);
    
    // 绑定删除按钮事件
    const removeBtn = cardElement.querySelector('.remove-shape-btn');
    if (removeBtn) {
        removeBtn.addEventListener('click', function() {
            removeShape(index);
        });
        console.log(`删除按钮事件已绑定: 索引=${index}`);
    }
    
    // 绑定倒角半径切换按钮事件
    const toggleToListBtn = cardElement.querySelector('.toggle-radius-list-btn');
    if (toggleToListBtn) {
        toggleToListBtn.addEventListener('click', function(event) {
            console.log(`点击切换到半径列表按钮: 索引=${index}`);
            toggleToRadiusList(event);
        });
        console.log(`切换到半径列表按钮事件已绑定: 索引=${index}`);
    } else {
        console.warn(`未找到切换到半径列表按钮: 索引=${index}`);
    }
    
    const toggleToSingleBtn = cardElement.querySelector('.toggle-single-radius-btn');
    if (toggleToSingleBtn) {
        toggleToSingleBtn.addEventListener('click', function(event) {
            console.log(`点击切换到单一半径按钮: 索引=${index}`);
            toggleToSingleRadius(event);
        });
        console.log(`切换到单一半径按钮事件已绑定: 索引=${index}`);
    } else {
        console.warn(`未找到切换到单一半径按钮: 索引=${index}`);
    }
}

// 填充形状表单值
function fillShapeFormValues(cardElement, shape, index) {
    // 设置名称
    cardElement.querySelector(`[name="shapes[${index}].name"]`).value = shape.name;
    
    // 设置图层
    if (shape.layer && Array.isArray(shape.layer)) {
        cardElement.querySelector(`[name="shapes[${index}].layer[0]"]`).value = shape.layer[0];
        cardElement.querySelector(`[name="shapes[${index}].layer[1]"]`).value = shape.layer[1];
    }
    
    // 设置顶点
    if (shape.vertices) {
        cardElement.querySelector(`[name="shapes[${index}].vertices"]`).value = shape.vertices;
    }
    
    // 设置缩放
    if (shape.zoom && Array.isArray(shape.zoom)) {
        cardElement.querySelector(`[name="shapes[${index}].zoom[0]"]`).value = shape.zoom[0];
        cardElement.querySelector(`[name="shapes[${index}].zoom[1]"]`).value = shape.zoom[1];
    }
    
    // 设置倒角
    if (shape.fillet) {
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
    }
    
    // 环阵列特有属性
    if (shape.type === 'rings') {
        const ringWidthInput = cardElement.querySelector(`[name="shapes[${index}].ring_width"]`);
        const ringSpaceInput = cardElement.querySelector(`[name="shapes[${index}].ring_space"]`);
        const ringNumInput = cardElement.querySelector(`[name="shapes[${index}].ring_num"]`);
        
        if (ringWidthInput && shape.ring_width !== undefined) {
            ringWidthInput.value = shape.ring_width;
        }
        
        if (ringSpaceInput && shape.ring_space !== undefined) {
            ringSpaceInput.value = shape.ring_space;
        }
        
        if (ringNumInput && shape.ring_num !== undefined) {
            ringNumInput.value = shape.ring_num;
        }
    }
}

// 移除形状
function removeShape(index) {
    // 移除配置中的形状
    config.shapes.splice(index, 1);
    
    // 更新JSON编辑器
    jsonEditor.set(config);
    
    // 更新YAML预览
    updateYAMLPreview();
    
    // 重新渲染所有形状卡片
    refreshShapesContainer();
}

// 刷新形状容器
function refreshShapesContainer() {
    const container = document.getElementById('shapesContainer');
    container.innerHTML = '';
    
    // 重新渲染所有形状
    config.shapes.forEach((shape, index) => {
        renderShapeCard(shape, index);
    });
    
    // 重新绑定倒角半径切换按钮事件
    bindRadiusListToggleEvents();
}

// 从表单更新JSON
function updateJSONFromForm() {
    // 获取全局配置
    config.global.dbu = parseFloat(document.getElementById('dbu').value);
    config.global.fillet.precision = parseFloat(document.getElementById('filletPrecision').value);
    config.global.fillet.interactive = document.getElementById('filletInteractive').checked;
    config.global.fillet.default_action = document.getElementById('filletDefaultAction').value;
    
    // 获取GDS配置
    config.gds.output_file = document.getElementById('outputFile').value;
    config.gds.cell_name = document.getElementById('cellName').value;
    config.gds.default_layer[0] = parseInt(document.getElementById('defaultLayerNum').value);
    config.gds.default_layer[1] = parseInt(document.getElementById('defaultDatatype').value);
    
    // 获取形状配置
    const shapeCards = document.querySelectorAll('.shape-card');
    config.shapes = [];
    
    shapeCards.forEach(card => {
        const index = parseInt(card.getAttribute('data-shape-index'));
        const type = card.querySelector(`[name="shapes[${index}].type"]`).value;
        
        const shape = {
            type: type,
            name: card.querySelector(`[name="shapes[${index}].name"]`).value,
            layer: [
                parseInt(card.querySelector(`[name="shapes[${index}].layer[0]"]`).value),
                parseInt(card.querySelector(`[name="shapes[${index}].layer[1]"]`).value)
            ],
            vertices: card.querySelector(`[name="shapes[${index}].vertices"]`).value,
            fillet: {
                type: card.querySelector(`[name="shapes[${index}].fillet.type"]`).value,
                radius: parseFloat(card.querySelector(`[name="shapes[${index}].fillet.radius"]`).value)
            },
            zoom: [
                parseFloat(card.querySelector(`[name="shapes[${index}].zoom[0]"]`).value),
                parseFloat(card.querySelector(`[name="shapes[${index}].zoom[1]"]`).value)
            ]
        };
        
        // 检查是否有半径列表
        const radiusListContainer = card.querySelector(`.radius-list-container[data-shape-index="${index}"]`);
        if (radiusListContainer && radiusListContainer.style.display !== 'none') {
            const radiiInput = card.querySelector(`[name="shapes[${index}].fillet.radii"]`);
            if (radiiInput && radiiInput.value) {
                // 解析半径列表
                const radiiValues = radiiInput.value.split(',').map(r => parseFloat(r.trim())).filter(r => !isNaN(r));
                if (radiiValues.length > 0) {
                    shape.fillet.radii = radiiValues;
                }
            }
        }
        
        // 环阵列特有属性
        if (type === 'rings') {
            shape.ring_width = parseFloat(card.querySelector(`[name="shapes[${index}].ring_width"]`).value);
            shape.ring_space = parseFloat(card.querySelector(`[name="shapes[${index}].ring_space"]`).value);
            shape.ring_num = parseInt(card.querySelector(`[name="shapes[${index}].ring_num"]`).value);
        }
        
        config.shapes.push(shape);
    });
    
    // 更新JSON编辑器
    jsonEditor.set(config);
    
    // 更新YAML预览
    updateYAMLPreview();
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