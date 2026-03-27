class TKEManager {
  constructor() {
    this.selectedCluster = null;
    this.selectedNamespace = null;
    this.selectedDeployment = null;
    this.selectedPod = null;
    this.selectedAction = null;
    this.selectedScript = null;
    this.scripts = [];
    this.allDeployments = [];
    
    this.initElements();
    this.bindEvents();
    this.checkKubectl();
    this.loadClusters();
  }

  initElements() {
    this.kubectlWarning = document.getElementById('kubectl-warning');
    this.mainContent = document.getElementById('main-content');
    
    this.clusterSelect = document.getElementById('cluster-select');
    this.namespaceStep = document.getElementById('namespace-step');
    this.namespaceSelect = document.getElementById('namespace-select');
    
    this.deploymentStep = document.getElementById('deployment-step');
    this.deploymentSearch = document.getElementById('deployment-search');
    this.searchDeploymentBtn = document.getElementById('search-deployment-btn');
    this.deploymentSelect = document.getElementById('deployment-select');
    this.deploymentLoading = document.getElementById('deployment-loading');
    
    this.podStep = document.getElementById('pod-step');
    this.podSelect = document.getElementById('pod-select');
    this.podLoading = document.getElementById('pod-loading');
    
    this.actionStep = document.getElementById('action-step');
    this.actionSelect = document.getElementById('action-select');
    
    this.scriptStep = document.getElementById('script-step');
    this.scriptList = document.getElementById('script-list');
    this.scriptLoading = document.getElementById('script-loading');
    this.refreshScriptsBtn = document.getElementById('refresh-scripts-btn');
    
    this.commandStep = document.getElementById('command-step');
    this.commandInput = document.getElementById('command-input');
    this.commandValidation = document.getElementById('command-validation');
    
    this.actionBar = document.getElementById('action-bar');
    this.executeBtn = document.getElementById('execute-btn');
    this.abortBtn = document.getElementById('abort-btn');
    
    this.resultContainer = document.getElementById('result-container');
    this.resultCommand = document.getElementById('result-command');
    this.resultOutput = document.getElementById('result-output');
    this.closeResultBtn = document.getElementById('close-result');
    
    this.errorContainer = document.getElementById('error-container');
    this.errorContent = document.getElementById('error-content');
  }

  bindEvents() {
    this.clusterSelect.addEventListener('change', () => this.onClusterChange());
    this.namespaceSelect.addEventListener('change', () => this.onNamespaceChange());
    this.searchDeploymentBtn.addEventListener('click', () => this.filterDeployments());
    this.deploymentSearch.addEventListener('keypress', (e) => {
      if (e.key === 'Enter') this.filterDeployments();
    });
    this.deploymentSelect.addEventListener('change', () => this.onDeploymentChange());
    this.podSelect.addEventListener('change', () => this.onPodChange());
    this.actionSelect.addEventListener('change', () => this.onActionChange());
    this.executeBtn.addEventListener('click', () => this.executeAction());
    this.abortBtn.addEventListener('click', () => this.abortExecution());
    this.closeResultBtn.addEventListener('click', () => this.hideResult());
    if (this.refreshScriptsBtn) {
      this.refreshScriptsBtn.addEventListener('click', () => this.loadScripts());
    }
    
    const closeEditorBtn = document.getElementById('close-editor');
    const saveScriptBtn = document.getElementById('save-script-btn');
    const cancelEditBtn = document.getElementById('cancel-edit-btn');
    
    if (closeEditorBtn) {
      closeEditorBtn.addEventListener('click', () => this.closeScriptEditor());
    }
    if (saveScriptBtn) {
      saveScriptBtn.addEventListener('click', () => this.saveScript());
    }
    if (cancelEditBtn) {
      cancelEditBtn.addEventListener('click', () => this.closeScriptEditor());
    }
    
    if (this.commandInput) {
      this.commandInput.addEventListener('input', () => this.validateCommand());
    }
  }

  async checkKubectl() {
    try {
      const response = await fetch('api/check-kubectl');
      const data = await response.json();
      
      if (!data.installed) {
        this.kubectlWarning.classList.remove('hidden');
        this.mainContent.style.opacity = '0.5';
        this.mainContent.style.pointerEvents = 'none';
      } else {
        this.kubectlWarning.classList.add('hidden');
        this.mainContent.style.opacity = '1';
        this.mainContent.style.pointerEvents = 'auto';
      }
    } catch (error) {
      console.error('检查 kubectl 失败:', error);
    }
  }

  async loadClusters() {
    try {
      const response = await fetch('api/clusters');
      const data = await response.json();
      
      this.clusterSelect.innerHTML = '<option value="">-- 请选择集群 --</option>';
      data.clusters.forEach(cluster => {
        const option = document.createElement('option');
        option.value = cluster.id;
        option.textContent = cluster.name;
        this.clusterSelect.appendChild(option);
      });
    } catch (error) {
      this.showError('加载集群列表失败: ' + error.message);
    }
  }

  async onClusterChange() {
    this.selectedCluster = this.clusterSelect.value;
    
    if (this.selectedCluster) {
      this.namespaceStep.style.display = 'block';
      await this.loadNamespaces();
    } else {
      this.namespaceStep.style.display = 'none';
      this.deploymentStep.style.display = 'none';
      this.podStep.style.display = 'none';
      this.actionStep.style.display = 'none';
      this.scriptStep.style.display = 'none';
      this.actionBar.style.display = 'none';
    }
    
    this.resetFromStep('namespace');
  }

  async loadNamespaces() {
    try {
      const clusterId = this.selectedCluster;
      const url = clusterId ? `api/namespaces?clusterId=${clusterId}` : 'api/namespaces';
      const response = await fetch(url);
      const data = await response.json();
      
      this.namespaceSelect.innerHTML = '<option value="">-- 请选择命名空间 --</option>';
      data.namespaces.forEach(ns => {
        const option = document.createElement('option');
        option.value = ns;
        option.textContent = ns;
        this.namespaceSelect.appendChild(option);
      });
    } catch (error) {
      this.showError('加载命名空间列表失败: ' + error.message);
    }
  }

  async onNamespaceChange() {
    this.selectedNamespace = this.namespaceSelect.value;
    console.log('selectedNamespace:', this.selectedNamespace);

    this.resetFromStep('deployment');
    
    if (this.selectedNamespace) {
      this.deploymentStep.style.display = 'block';
      await this.loadDeployments();
    } else {
      this.deploymentStep.style.display = 'none';
      this.podStep.style.display = 'none';
      this.actionStep.style.display = 'none';
      this.scriptStep.style.display = 'none';
      this.actionBar.style.display = 'none';
    }
  }

  async loadDeployments() {
    if (!this.selectedNamespace) return;
    
    this.deploymentLoading.classList.remove('hidden');
    this.deploymentSelect.innerHTML = '<option value="">-- 请选择部署 --</option>';
    this.deploymentSearch.value = '';
    
    try {
      const response = await fetch(`api/deployments?namespace=${this.selectedNamespace}`);
      const data = await response.json();
      
      console.log('API 返回数据:', data);
      console.log('deployments 数量:', data.deployments ? data.deployments.length : 0);
      
      if (data.error) {
        this.showError(data.error);
        return;
      }
      
      this.allDeployments = data.deployments || [];
      console.log('allDeployments:', this.allDeployments);
      this.renderDeployments(this.allDeployments);
    } catch (error) {
      console.error('加载部署失败:', error);
      this.showError('加载部署列表失败: ' + error.message);
    } finally {
      this.deploymentLoading.classList.add('hidden');
    }
  }

  filterDeployments() {
    const keyword = this.deploymentSearch.value.trim().toLowerCase();
    
    if (!keyword) {
      this.renderDeployments(this.allDeployments);
      return;
    }
    
    const filtered = this.allDeployments.filter(d => 
      d.name.toLowerCase().includes(keyword)
    );
    this.renderDeployments(filtered);
  }

  renderDeployments(deployments) {
    const select = document.getElementById('deployment-select');
    select.innerHTML = '';
    
    if (!deployments || deployments.length === 0) {
      const option = document.createElement('option');
      option.value = '';
      option.textContent = '-- 请选择部署 --';
      select.appendChild(option);
      return;
    }
    
    const countOption = document.createElement('option');
    countOption.value = '';
    countOption.textContent = `搜索到部署 ${deployments.length} 条 ， 请选择对应部署`;
    countOption.disabled = true;
    select.appendChild(countOption);
    
    deployments.forEach(deploy => {
      const option = document.createElement('option');
      option.value = deploy.name;
      option.textContent = deploy.name + ' (Ready: ' + deploy.ready + ')';
      select.appendChild(option);
    });
    
    select.selectedIndex = 0;
  }

  async onDeploymentChange() {
    this.selectedDeployment = this.deploymentSelect.value;
    
    if (this.selectedDeployment) {
      this.podStep.style.display = 'block';
      await this.loadPods();
    } else {
      this.podStep.style.display = 'none';
      this.actionStep.style.display = 'none';
      this.scriptStep.style.display = 'none';
      this.actionBar.style.display = 'none';
    }
  }

  async loadPods() {
    if (!this.selectedNamespace || !this.selectedDeployment) return;
    
    this.podLoading.classList.remove('hidden');
    this.podSelect.innerHTML = '';
    
    try {
      const response = await fetch(`api/pods?namespace=${this.selectedNamespace}&deployment=${this.selectedDeployment}`);
      const data = await response.json();
      
      if (data.error) {
        this.showError(data.error);
        return;
      }  

      console.log('allPods:', data.pods);
    
      if (data.pods.length === 0) {
        const option = document.createElement('option');
        option.value = '';
        option.textContent = '-- 请选择Pod --';
        this.podSelect.appendChild(option);
      } else {

        const countOption = document.createElement('option');
        countOption.value = '';
        countOption.textContent = `搜索到Pod ${data.pods.length} 条 ， 请选择对应部署`;
        countOption.disabled = true;
        this.podSelect.appendChild(countOption);

        data.pods.forEach(pod => {
          const option = document.createElement('option');
          option.value = pod.name;
          option.textContent = `${pod.name} (${pod.status})`;
          this.podSelect.appendChild(option);
        });

        this.podSelect.selectedIndex = 0;
      }
    } catch (error) {
      this.showError('加载 Pod 列表失败: ' + error.message);
    } finally {
      this.podLoading.classList.add('hidden');
    }
  }

  async onPodChange() {
    this.selectedPod = this.podSelect.value;
    
    if (this.selectedPod) {
      this.actionStep.style.display = 'block';
    } else {
      this.actionStep.style.display = 'none';
      this.scriptStep.style.display = 'none';
      this.actionBar.style.display = 'none';
    }
    
    this.resetFromStep('action');
  }

  async onActionChange() {
    this.selectedAction = this.actionSelect.value;
    
    this.scriptStep.style.display = 'none';
    this.commandStep.style.display = 'none';
    this.actionBar.style.display = 'none';
    
    if (this.selectedAction === 'script') {
      this.scriptStep.style.display = 'block';
      await this.loadScripts();
    } else if (this.selectedAction === 'command') {
      this.commandStep.style.display = 'block';
      this.commandInput.value = '';
      this.commandValidation.className = 'command-validation';
      this.commandValidation.textContent = '';
    }
    
    this.selectedScript = null;
  }

  async validateCommand() {
    const command = this.commandInput.value.trim();
    
    if (!command) {
      this.commandValidation.className = 'command-validation';
      this.commandValidation.textContent = '';
      this.actionBar.style.display = 'none';
      return;
    }
    
    try {
      const response = await fetch('api/command/validate', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ command: command })
      });
      
      const data = await response.json();
      
      if (data.valid) {
        this.commandValidation.className = 'command-validation valid';
        this.commandValidation.textContent = '✅ 命令安全，可以执行';
        this.actionBar.style.display = 'block';
      } else {
        this.commandValidation.className = 'command-validation invalid';
        this.commandValidation.innerHTML = '❌ 包含禁止命令：<br>' + data.errors.map(e => `行 ${e.line}: ${e.reason}`).join('<br>');
        this.actionBar.style.display = 'none';
      }
    } catch (error) {
      this.showError('验证命令失败: ' + error.message);
    }
  }

  async loadScripts() {
    this.scriptLoading.classList.remove('hidden');
    this.scriptList.innerHTML = '';
    
    try {
      const response = await fetch('api/scripts');
      const data = await response.json();
      
      this.scripts = data.scripts;
      
      if (this.scripts.length === 0) {
        this.scriptList.innerHTML = '<div class="script-item">没有可用的脚本，请在 script 目录下添加 .sh 文件</div>';
      } else {
        this.scripts.forEach(script => {
          const item = document.createElement('div');
          item.className = `script-item ${script.valid ? '' : 'invalid'}`;
          item.dataset.path = script.path;
          
          const statusHtml = !script.valid 
            ? `<span class="script-status invalid">❌ 包含禁止命令</span>`
            : `<span class="script-status valid">✅ 安全</span>`;
          
          item.innerHTML = `
            <span class="script-name">📜 ${script.name}</span>
            <div class="script-actions">
              ${statusHtml}
              <button class="btn btn-small btn-edit" data-path="${script.path}" data-name="${script.name}">编辑</button>
            </div>
          `;
          
          if (!script.valid) {
            item.title = script.errors.map(e => `行 ${e.line}: ${e.reason}`).join('\n');
          }
          
          if (script.valid) {
            item.addEventListener('click', (e) => {
              if (!e.target.classList.contains('btn-edit')) {
                this.selectScript(script, item);
              }
            });
          }
          
          const editBtn = item.querySelector('.btn-edit');
          editBtn.addEventListener('click', (e) => {
            e.stopPropagation();
            this.openScriptEditor(script);
          });
          
          this.scriptList.appendChild(item);
        });
      }
    } catch (error) {
      this.showError('加载脚本列表失败: ' + error.message);
    } finally {
      this.scriptLoading.classList.add('hidden');
    }
  }

  async openScriptEditor(script) {
    this.currentEditingScript = script;
    
    document.getElementById('editor-script-name').textContent = script.name;
    document.getElementById('script-editor-modal').classList.remove('hidden');
    
    try {
      const response = await fetch(`api/script/content?path=${encodeURIComponent(script.path)}`);
      const data = await response.json();
      
      if (data.error) {
        this.showError(data.error);
        return;
      }
      
      document.getElementById('script-editor').value = data.content;
    } catch (error) {
      this.showError('加载脚本内容失败: ' + error.message);
    }
  }

  closeScriptEditor() {
    document.getElementById('script-editor-modal').classList.add('hidden');
    this.currentEditingScript = null;
  }

  async saveScript() {
    if (!this.currentEditingScript) return;
    
    const content = document.getElementById('script-editor').value;
    
    try {
      const response = await fetch('api/script/save', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          path: this.currentEditingScript.path,
          content: content
        })
      });
      
      const data = await response.json();
      
      if (data.error) {
        this.showError(data.error);
        return;
      }
      
      this.closeScriptEditor();
      await this.loadScripts();
    } catch (error) {
      this.showError('保存脚本失败: ' + error.message);
    }
  }

  selectScript(script, element) {
    document.querySelectorAll('.script-item').forEach(item => {
      item.classList.remove('selected');
    });
    
    element.classList.add('selected');
    this.selectedScript = script;
    this.actionBar.style.display = 'block';
  }

  async executeAction() {
    if (!this.selectedPod || !this.selectedNamespace) {
      this.showError('请完成所有选择步骤');
      return;
    }
    
    if (this.selectedAction === 'script' && !this.selectedScript) {
      this.showError('请选择要执行的脚本');
      return;
    }
    
    if (this.selectedAction === 'command' && !this.commandInput.value.trim()) {
      this.showError('请输入要执行的命令');
      return;
    }
    
    this.executeBtn.disabled = true;
    this.executeBtn.innerHTML = '<span class="spinner"></span> 执行中...';
    this.abortBtn.style.display = 'inline-flex';
    this.currentExecutionId = null;
    this.isExecuting = true;
    
    try {
      let response;
      
      if (this.selectedAction === 'script') {
        response = await fetch('api/execute/start', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json'
          },
          body: JSON.stringify({
            pod: this.selectedPod,
            namespace: this.selectedNamespace,
            scriptPath: this.selectedScript.path
          })
        });
      } else if (this.selectedAction === 'command') {
        response = await fetch('api/execute/start', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json'
          },
          body: JSON.stringify({
            pod: this.selectedPod,
            namespace: this.selectedNamespace,
            command: this.commandInput.value.trim()
          })
        });
      }
      
      const data = await response.json();
      
      if (data.error) {
        this.showError(data.error, data.details);
        this.resetExecuteButton();
      } else {
        this.currentExecutionId = data.executionId;
        this.pollExecutionStatus(data.executionId, data.command);
      }
    } catch (error) {
      this.showError('执行失败: ' + error.message);
      this.resetExecuteButton();
    }
  }

  async pollExecutionStatus(executionId, command) {
    const pollInterval = 500;
    const maxAttempts = 120;
    let attempts = 0;
    
    const poll = async () => {
      if (!this.isExecuting) {
        return;
      }
      
      attempts++;
      
      try {
        const response = await fetch(`api/execute/status?executionId=${executionId}`);
        const data = await response.json();
        
        if (data.status === 'running') {
          if (attempts < maxAttempts) {
            setTimeout(poll, pollInterval);
          } else {
            this.showError('执行超时');
            this.resetExecuteButton();
          }
        } else if (data.status === 'completed') {
          if (data.returncode === 0) {
            this.showResult(command, data.stdout);
          } else {
            this.showError(data.stderr || '执行失败');
          }
          this.resetExecuteButton();
        } else if (data.status === 'timeout') {
          this.showError(data.stderr || '执行超时');
          this.resetExecuteButton();
        } else if (data.status === 'aborted') {
          this.showError('执行已被中止');
          this.resetExecuteButton();
        }
      } catch (error) {
        this.showError('查询状态失败: ' + error.message);
        this.resetExecuteButton();
      }
    };
    
    poll();
  }

  resetExecuteButton() {
    this.executeBtn.disabled = false;
    this.executeBtn.innerHTML = '<span class="btn-icon">▶️</span> 执行操作';
    this.abortBtn.style.display = 'none';
    this.currentExecutionId = null;
    this.isExecuting = false;
  }

  async abortExecution() {
    if (!this.currentExecutionId) {
      this.showError('没有正在执行的任务');
      return;
    }
    
    try {
      const response = await fetch('api/execute/abort', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          executionId: this.currentExecutionId
        })
      });
      
      const data = await response.json();
      
      if (data.success) {
        this.isExecuting = false;
        this.showError('执行已中止');
        this.resetExecuteButton();
      } else {
        this.showError(data.error || '中止失败');
      }
    } catch (error) {
      this.showError('中止请求失败: ' + error.message);
    }
  }

  showResult(command, output) {
    this.resultCommand.textContent = command;
    this.resultOutput.textContent = output;
    this.resultContainer.classList.remove('hidden');
    this.errorContainer.classList.add('hidden');
    
    this.resultContainer.scrollIntoView({ behavior: 'smooth' });
  }

  hideResult() {
    this.resultContainer.classList.add('hidden');
  }

  showError(message, details = null) {
    let html = `<p>${message}</p>`;
    
    if (details && Array.isArray(details)) {
      html += '<ul>';
      details.forEach(detail => {
        html += `<li>行 ${detail.line}: ${detail.reason}</li>`;
      });
      html += '</ul>';
    }
    
    this.errorContent.innerHTML = html;
    this.errorContainer.classList.remove('hidden');
    this.resultContainer.classList.add('hidden');
    
    this.errorContainer.scrollIntoView({ behavior: 'smooth' });
  }

  resetFromStep(step) {
    if (step === 'namespace') {
      this.selectedNamespace = null;
      this.namespaceSelect.value = '';
    }
    
    if (step === 'namespace' || step === 'deployment') {
      this.selectedDeployment = null;
      this.deploymentSearch.value = '';
      this.deploymentSelect.innerHTML = '<option value="">-- 请选择部署 --</option>';
      this.allDeployments = [];
    }
    
    if (step === 'namespace' || step === 'deployment' || step === 'pod') {
      this.selectedPod = null;
      this.podSelect.innerHTML = '<option value="">-- 请选择 Pod --</option>';
    }
    
    if (step === 'namespace' || step === 'deployment' || step === 'pod' || step === 'action') {
      this.selectedAction = null;
      this.actionSelect.value = '';
    }
    
    if (step === 'namespace' || step === 'deployment' || step === 'pod' || step === 'action' || step === 'script') {
      this.selectedScript = null;
      this.scriptList.innerHTML = '';
    }
    
    this.actionBar.style.display = 'none';
    this.hideResult();
    this.errorContainer.classList.add('hidden');
  }
}

document.addEventListener('DOMContentLoaded', () => {
  window.tkeManager = new TKEManager();
});
