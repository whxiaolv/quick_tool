document.addEventListener('DOMContentLoaded', function() {
    checkKubectl();
    loadScripts();
    setupEventListeners();
});

let currentScriptPath = null;
let currentParameters = [];

function checkKubectl() {
    fetch('api/check-kubectl')
        .then(response => response.json())
        .then(data => {
            if (!data.installed) {
                document.getElementById('kubectl-warning').classList.remove('hidden');
            }
        })
        .catch(error => {
            console.error('检查 kubectl 失败:', error);
        });
}

function loadScripts() {
    showLoading('scripts-loading');
    
    fetch('api/scripts')
        .then(response => response.json())
        .then(data => {
            hideLoading('scripts-loading');
            renderScripts(data.scripts);
        })
        .catch(error => {
            hideLoading('scripts-loading');
            showError('加载脚本列表失败: ' + error.message);
        });
}

function renderScripts(scripts) {
    const scriptsList = document.getElementById('scripts-list');
    scriptsList.innerHTML = '';
    
    if (scripts.length === 0) {
        scriptsList.innerHTML = '<div class="empty-state">暂无脚本，点击"添加脚本"按钮创建新脚本</div>';
        return;
    }
    
    scripts.forEach(script => {
        const scriptCard = document.createElement('div');
        scriptCard.className = 'script-card';
        
        const statusIcon = script.valid ? '✅' : '⚠️';
        const statusClass = script.valid ? 'valid' : 'invalid';
        
        scriptCard.innerHTML = `
            <div class="script-header">
                <span class="script-status ${statusClass}">${statusIcon}</span>
                <h3 class="script-title">${script.title}</h3>
            </div>
             <div class="script-info">
            <p class="script-name"><strong>文件名：</strong>${script.name}</p>
            <p class="script-desc">${script.description || '暂无描述'}</p>
        </div>
            <div class="script-actions">
                <button class="btn btn-small btn-primary" onclick="openEditor('${script.path}')">
                    <span class="btn-icon">✏️</span>
                    编辑
                </button>
                <button class="btn btn-small btn-success" onclick="openExecuteModal('${script.path}', '${script.name}')">
                    <span class="btn-icon">▶️</span>
                    执行
                </button>
                <button class="btn btn-small btn-danger" onclick="deleteScript('${script.path}')">
                    <span class="btn-icon">🗑️</span>
                    删除
                </button>
            </div>
            ${!script.valid ? `<div class="script-errors">
                ${script.errors.map(err => `<div class="error-item">第 ${err.line} 行: ${err.reason}</div>`).join('')}
            </div>` : ''}
        `;
        
        scriptsList.appendChild(scriptCard);
    });
}

function openEditor(scriptPath) {
  
    if (!scriptPath) {
        currentScriptPath = null;  // 新建必须是 null
    } else {
        currentScriptPath = scriptPath;  // 编辑才赋值
    }
    currentParameters = [];
    
    const modal = document.getElementById('script-editor-modal');
    const title = document.getElementById('editor-title');
    const scriptTitle = document.getElementById('script-title');
    const scriptDescription = document.getElementById('script-description');
    const scriptEditor = document.getElementById('script-editor');
    const parametersList = document.getElementById('parameters-list');
    
    if (scriptPath) {
        title.textContent = '编辑脚本';
        
        fetch(`api/script/content?path=${encodeURIComponent(scriptPath)}`)
            .then(response => response.json())
            .then(data => {
                if (data.error) {
                    showError(data.error);
                    return;
                }
                
                scriptEditor.value = data.content;
                parseScriptMetadata(data.content);
            })
            .catch(error => {
                showError('加载脚本内容失败: ' + error.message);
            });
    } else {
        title.textContent = '添加脚本';
        scriptTitle.value = '';
        scriptDescription.value = '';
        scriptEditor.value = '';
    }
    
    parametersList.innerHTML = '';
    renderParameters();
    
    modal.classList.remove('hidden');
}

function parseScriptMetadata(content) {
    const lines = content.split('\n');
    
    for (let i = 0; i < lines.length; i++) {
        const line = lines[i].trim();
        
        if (line.startsWith('# TITLE:')) {
            document.getElementById('script-title').value = line.substring(8).trim();
        } else if (line.startsWith('# DESCRIPTION:')) {
            document.getElementById('script-description').value = line.substring(14).trim();
        } else if (line.startsWith('# PARAM:')) {
            // 匹配参数描述、参数 Key、默认参数值(不能为空，否则不解析)
            //const paramMatch = line.match(/# PARAM:\s*(.+?)\s*-\s*(.+?)\s*-\s*(.+)/);
            // 匹配参数描述、参数 Key、默认参数值(可以为空)
            const paramMatch = line.match(/# PARAM:\s*(.+?)\s*-\s*(.+?)\s*-\s*(.*)/); 
            if (paramMatch) {
                currentParameters.push({
                    description: paramMatch[1].trim(),
                    key: paramMatch[2].trim(),
                    value: paramMatch[3].trim()
                });
            }
        }
    }
    
    renderParameters();
}

function renderParameters() {
    const parametersList = document.getElementById('parameters-list');
    parametersList.innerHTML = '';
    
    currentParameters.forEach((param, index) => {
        const paramDiv = document.createElement('div');
        paramDiv.className = 'parameter-item';
        paramDiv.innerHTML = `
            <div class="parameter-row">
                <input type="text" class="form-input param-desc" placeholder="参数描述" 
                       value="${param.description}" data-index="${index}" onchange="updateParameter(${index}, 'description', this.value)">
                <input type="text" class="form-input param-key" placeholder="参数 Key" 
                       value="${param.key}" data-index="${index}" onchange="updateParameter(${index}, 'key', this.value)">
                <input type="text" class="form-input param-value" placeholder="默认参数值" 
                       value="${param.value}" data-index="${index}" onchange="updateParameter(${index}, 'value', this.value)">
                <button class="btn btn-small btn-danger" onclick="removeParameter(${index})">
                    <span class="btn-icon">✕</span>
                </button>
            </div>
        `;
        parametersList.appendChild(paramDiv);
    });
}

function addParameter() {
    currentParameters.push({
        description: '',
        key: '',
        value: ''
    });
    renderParameters();
}

function updateParameter(index, field, value) {
    currentParameters[index][field] = value;
}

function removeParameter(index) {
    currentParameters.splice(index, 1);
    renderParameters();
}

function saveScript() {
    let title = document.getElementById('script-title').value.trim();
    let description = document.getElementById('script-description').value.trim();
    let content = document.getElementById('script-editor').value.trim();
    
    if (!title) {
        showValidation('请输入脚本标题');
        return;
    }
    
    if (!content) {
        showValidation('请输入脚本代码');
        return;
    }  

    // 自动区分 新建 / 编辑
    const isNew = currentScriptPath === null ? 1 : 0;

    // 彻底清理代码里的旧头部（#! / TITLE / DESCRIPTION / PARAM）
    let cleanCode = content
        .replace(/^#!\/usr\/bin\/env python3\s*\n?/i, '')          // 移除解释器行
        .replace(/^#\s*TITLE:.*\n?/gim, '')                       // 移除旧标题
        .replace(/^#\s*DESCRIPTION:.*\n?/gim, '')                  // 移除旧描述
        .replace(/^#\s*PARAM:.*\n?/gim, '')                        // 移除旧参数
        .trim();    
        
    let scriptContent = `#!/usr/bin/env python3
# TITLE: ${title}
# DESCRIPTION: ${description}
`;
    
    currentParameters.forEach(param => {
        if (param.key) {
            scriptContent += `# PARAM: ${param.description} - ${param.key} - ${param.value}\n`;
        }
    });
    
    scriptContent += '\n' + cleanCode;
    
    const scriptPath = currentScriptPath || `script/${title.replace(/\s+/g, '_')}.py`;
    
    fetch('api/script/save', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            path: scriptPath,
            content: scriptContent,
            create: isNew 
        })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            closeEditor();
            loadScripts();
            showSuccess('脚本保存成功');
        } else {
            showValidation(data.error);
            if (data.details) {
                data.details.forEach(err => {
                    showValidation(`第 ${err.line} 行: ${err.reason}`);
                });
            }
        }
    })
    .catch(error => {
        showError('保存脚本失败: ' + error.message);
    });
}

function deleteScript(scriptPath) {
    if (!confirm('确定要删除这个脚本吗？')) {
        return;
    }
    
    fetch('api/script/delete', {
        method: 'DELETE',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            path: scriptPath
        })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            loadScripts();
            showSuccess('脚本删除成功');
        } else {
            showError(data.error);
        }
    })
    .catch(error => {
        showError('删除脚本失败: ' + error.message);
    });
}

function openExecuteModal(scriptPath, scriptName) {
    currentParameters = [];
    currentScriptPath = scriptPath;
    
    fetch(`api/script/content?path=${encodeURIComponent(scriptPath)}`)
        .then(response => response.json())
        .then(data => {
            if (data.error) {
                showError(data.error);
                return;
            }
            
            parseScriptMetadata(data.content);
            
            document.getElementById('execute-script-name').textContent = scriptName;
            renderExecuteParameters();
            
            document.getElementById('execute-modal').classList.remove('hidden');
        })
        .catch(error => {
            showError('加载脚本内容失败: ' + error.message);
        });
}

function renderExecuteParameters() {
    const parametersList = document.getElementById('execute-parameters-list');
    parametersList.innerHTML = '';
    
    if (currentParameters.length === 0) {
        parametersList.innerHTML = '<div class="empty-state">此脚本无需参数</div>';
        return;
    }
    
    currentParameters.forEach((param, index) => {
        const paramDiv = document.createElement('div');
        paramDiv.className = 'parameter-item';
        paramDiv.innerHTML = `
            <div class="parameter-row">
                <label class="param-label">${param.description || param.key}</label>
                <input type="text" class="form-input param-value" 
                       placeholder="${param.value}" 
                       data-index="${index}" 
                       onchange="updateParameter(${index}, 'value', this.value)">
            </div>
        `;
        parametersList.appendChild(paramDiv);
    });
}

function executeScript() {
    const parameters = {};
    
    currentParameters.forEach((param, index) => {
        if (param.key) {
            parameters[param.key] = document.querySelector(`.param-value[data-index="${index}"]`).value;
        }
    });
    
    fetch('api/execute', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            scriptPath: currentScriptPath,
            parameters: parameters
        })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            closeExecuteModal();
            showResult(data.output);
        } else {
            showError(data.error);
            if (data.stdout) {
                showError('脚本输出: ' + data.stdout);
            }
        }
    })
    .catch(error => {
        showError('执行脚本失败: ' + error.message);
    });
}

function showResult(output) {
    const resultContainer = document.getElementById('result-container');
    const resultOutput = document.getElementById('result-output');
    
    try {
        const formattedOutput = typeof output === 'string' ? JSON.stringify(JSON.parse(output), null, 2) : JSON.stringify(output, null, 2);
        resultOutput.textContent = formattedOutput;
    } catch (e) {
        resultOutput.textContent = output;
    }
    
    resultContainer.classList.remove('hidden');
}

function closeEditor() {
    document.getElementById('script-editor-modal').classList.add('hidden');
    document.getElementById('script-validation').innerHTML = '';
}

function closeExecuteModal() {
    document.getElementById('execute-modal').classList.add('hidden');
}

function closeResult() {
    document.getElementById('result-container').classList.add('hidden');
}

function showValidation(message) {
    const validationDiv = document.getElementById('script-validation');
    validationDiv.innerHTML = `<div class="error-message">${message}</div>`;
}

function showError(message) {
    const errorContainer = document.getElementById('error-container');
    const errorContent = document.getElementById('error-content');
    errorContent.textContent = message;
    errorContainer.classList.remove('hidden');
}

function showSuccess(message) {
    alert(message);
}

function showLoading(loadingId) {
    document.getElementById(loadingId).classList.remove('hidden');
}

function hideLoading(loadingId) {
    document.getElementById(loadingId).classList.add('hidden');
}

function setupEventListeners() {
    document.getElementById('add-script-btn').addEventListener('click', () => openEditor());
    document.getElementById('refresh-scripts-btn').addEventListener('click', loadScripts);
    document.getElementById('close-editor').addEventListener('click', closeEditor);
    document.getElementById('cancel-edit-btn').addEventListener('click', closeEditor);
    document.getElementById('save-script-btn').addEventListener('click', saveScript);
    document.getElementById('add-parameter-btn').addEventListener('click', addParameter);
    document.getElementById('close-result').addEventListener('click', closeResult);
    document.getElementById('close-execute').addEventListener('click', closeExecuteModal);
    document.getElementById('cancel-execute-btn').addEventListener('click', closeExecuteModal);
    document.getElementById('confirm-execute-btn').addEventListener('click', executeScript);
    
    document.getElementById('script-editor').addEventListener('input', function() {
        document.getElementById('script-validation').innerHTML = '';
    });
}
