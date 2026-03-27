class MySQLDiffTool {
    constructor() {
        this.leftConfig = {
            type: 'database',
            config: null,
            table: null,
            files: []
        };
        
        this.rightConfig = {
            type: 'database',
            config: null,
            table: null,
            files: []
        };
        
        this.currentTaskId = null;
        this.reportUrl = null;
        
        this.initElements();
        this.bindEvents();
        this.loadReports();
    }
    
    initElements() {
        this.leftTestBtn = document.getElementById('left-test-btn');
        this.rightTestBtn = document.getElementById('right-test-btn');
        this.leftTableSelect = document.getElementById('left-table-select');
        this.rightTableSelect = document.getElementById('right-table-select');
        
        this.leftImportBtn = document.getElementById('left-import-btn');
        this.rightImportBtn = document.getElementById('right-import-btn');
        this.leftConfigFile = document.getElementById('left-config-file');
        this.rightConfigFile = document.getElementById('right-config-file');
        
        this.leftConfigText = document.getElementById('left-config-text');
        this.rightConfigText = document.getElementById('right-config-text');
        this.leftParseBtn = document.getElementById('left-parse-btn');
        this.rightParseBtn = document.getElementById('right-parse-btn');
        
        this.compareBtn = document.getElementById('compare-btn');
        this.compareDatabaseBtn = document.getElementById('compare-database-btn');
        this.progressContainer = document.getElementById('progress-container');
        this.progressFill = document.getElementById('progress-fill');
        this.progressText = document.getElementById('progress-text');
        
        this.resultContainer = document.getElementById('result-container');
        this.resultStats = document.getElementById('result-stats');
        this.viewReportBtn = document.getElementById('view-report-btn');
        
        this.errorContainer = document.getElementById('error-container');
        this.errorContent = document.getElementById('error-content');
        
        this.fileAssociation = document.getElementById('file-association');
        this.associationList = document.getElementById('association-list');
        
        this.historyList = document.getElementById('history-list');
        this.refreshReportsBtn = document.getElementById('refresh-reports-btn');
        this.batchDeleteBtn = document.getElementById('batch-delete-btn');
    }
    
    bindEvents() {
        document.querySelectorAll('.toggle-btn').forEach(btn => {
            btn.addEventListener('click', (e) => this.handleSourceToggle(e));
        });
        
        this.leftTestBtn.addEventListener('click', () => this.testConnection('left'));
        this.rightTestBtn.addEventListener('click', () => this.testConnection('right'));
        
        this.leftImportBtn.addEventListener('click', () => this.leftConfigFile.click());
        this.rightImportBtn.addEventListener('click', () => this.rightConfigFile.click());
        
        this.leftConfigFile.addEventListener('change', (e) => this.handleConfigImport(e, 'left'));
        this.rightConfigFile.addEventListener('change', (e) => this.handleConfigImport(e, 'right'));
        
        this.leftParseBtn.addEventListener('click', () => this.handleConfigTextParse('left'));
        this.rightParseBtn.addEventListener('click', () => this.handleConfigTextParse('right'));
        
        this.leftTableSelect.addEventListener('change', () => {
            this.leftConfig.table = this.leftTableSelect.value;
        });
        
        this.rightTableSelect.addEventListener('change', () => {
            this.rightConfig.table = this.rightTableSelect.value;
        });
        
        this.setupFileUpload('left');
        this.setupFileUpload('right');
        
        this.compareBtn.addEventListener('click', () => this.startComparison());
        this.compareDatabaseBtn.addEventListener('click', () => this.startDatabaseComparison());
        
        this.viewReportBtn.addEventListener('click', () => {
            if (this.reportUrl) {
                window.open(this.reportUrl, '_blank');
            }
        });
        
        this.refreshReportsBtn.addEventListener('click', () => this.loadReports());
    }
    
    handleSourceToggle(e) {
        const btn = e.target;
        const side = btn.dataset.side;
        const type = btn.dataset.type;
        
        btn.parentElement.querySelectorAll('.toggle-btn').forEach(b => {
            b.classList.remove('active');
        });
        btn.classList.add('active');
        
        const dbForm = document.getElementById(`${side}-database-form`);
        const fileForm = document.getElementById(`${side}-file-form`);
        
        if (type === 'database') {
            dbForm.classList.remove('hidden');
            fileForm.classList.add('hidden');
            this[`${side}Config`].type = 'database';
        } else {
            dbForm.classList.add('hidden');
            fileForm.classList.remove('hidden');
            this[`${side}Config`].type = 'file';
        }
        
        this.checkFileAssociation();
    }
    
    async testConnection(side) {
        const host = document.getElementById(`${side}-host`).value;
        const port = parseInt(document.getElementById(`${side}-port`).value) || 3306;
        const database = document.getElementById(`${side}-database`).value;
        const user = document.getElementById(`${side}-user`).value;
        const password = document.getElementById(`${side}-password`).value;
        
        if (!host || !database || !user) {
            this.showError('请填写完整的数据库连接信息');
            return;
        }
        
        const btn = document.getElementById(`${side}-test-btn`);
        const originalText = btn.textContent;
        btn.textContent = '测试中...';
        btn.disabled = true;
        
        try {
            const response = await fetch('api/test-connection', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    host, port, database, user, password
                })
            });
            
            const data = await response.json();
            
            if (data.success) {
                this[`${side}Config`].config = { host, port, database, user, password };
                
                await this.loadTables(side);
                
                this.showSuccess(`${side === 'left' ? '左侧' : '右侧'}数据库连接成功`);
            } else {
                this.showError(data.message);
            }
        } catch (error) {
            this.showError('连接测试失败: ' + error.message);
        } finally {
            btn.textContent = originalText;
            btn.disabled = false;
        }
    }
    
    async loadTables(side) {
        const config = this[`${side}Config`].config;
        
        try {
            const response = await fetch('api/tables', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(config)
            });
            
            const data = await response.json();
            
            if (data.success) {
                const select = document.getElementById(`${side}-table-select`);
                select.innerHTML = '<option value="">-- 请选择表 --</option>';
                select.disabled = false;
                
                data.tables.forEach(table => {
                    const option = document.createElement('option');
                    option.value = table;
                    option.textContent = table;
                    select.appendChild(option);
                });
            } else {
                this.showError(data.message);
            }
        } catch (error) {
            this.showError('获取表列表失败: ' + error.message);
        }
    }
    
    setupFileUpload(side) {
        const uploadArea = document.getElementById(`${side}-upload-area`);
        const fileInput = document.getElementById(`${side}-file-input`);
        const uploadedFiles = document.getElementById(`${side}-uploaded-files`);
        
        uploadArea.addEventListener('click', () => fileInput.click());
        
        uploadArea.addEventListener('dragover', (e) => {
            e.preventDefault();
            uploadArea.classList.add('dragover');
        });
        
        uploadArea.addEventListener('dragleave', () => {
            uploadArea.classList.remove('dragover');
        });
        
        uploadArea.addEventListener('drop', (e) => {
            e.preventDefault();
            uploadArea.classList.remove('dragover');
            this.handleFiles(side, e.dataTransfer.files);
        });
        
        fileInput.addEventListener('change', (e) => {
            this.handleFiles(side, e.target.files);
        });
    }
    
    async handleFiles(side, files) {
        if (files.length === 0) return;
        
        const formData = new FormData();
        for (let file of files) {
            formData.append('files', file);
        }
        
        try {
            const response = await fetch('api/upload', {
                method: 'POST',
                body: formData
            });
            
            const data = await response.json();
            
            if (data.success) {
                this[`${side}Config`].files = data.files;
                this.displayUploadedFiles(side, data.files);
                this.checkFileAssociation();
            } else {
                this.showError(data.message);
            }
        } catch (error) {
            this.showError('文件上传失败: ' + error.message);
        }
    }
    
    displayUploadedFiles(side, files) {
        const container = document.getElementById(`${side}-uploaded-files`);
        container.innerHTML = '';
        
        files.forEach((file, index) => {
            const item = document.createElement('div');
            item.className = 'file-item';
            item.innerHTML = `
                <div>
                    <span class="file-name">${file.filename}</span>
                    <span class="file-size">(${this.formatFileSize(file.size)})</span>
                </div>
                <button class="remove-btn" data-index="${index}">删除</button>
            `;
            
            item.querySelector('.remove-btn').addEventListener('click', () => {
                this[`${side}Config`].files.splice(index, 1);
                this.displayUploadedFiles(side, this[`${side}Config`].files);
                this.checkFileAssociation();
            });
            
            container.appendChild(item);
        });
    }
    
    formatFileSize(bytes) {
        if (bytes < 1024) return bytes + ' B';
        if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(2) + ' KB';
        return (bytes / (1024 * 1024)).toFixed(2) + ' MB';
    }
    
    checkFileAssociation() {
        const leftFiles = this.leftConfig.files;
        const rightFiles = this.rightConfig.files;
        
        if (leftFiles.length > 1 || rightFiles.length > 1) {
            this.fileAssociation.classList.remove('hidden');
            this.generateAssociationUI(leftFiles, rightFiles);
        } else {
            this.fileAssociation.classList.add('hidden');
        }
    }
    
    generateAssociationUI(leftFiles, rightFiles) {
        this.associationList.innerHTML = '';
        
        const maxPairs = Math.max(leftFiles.length, rightFiles.length);
        
        for (let i = 0; i < maxPairs; i++) {
            const item = document.createElement('div');
            item.className = 'association-item';
            
            const leftFile = leftFiles[i] || null;
            const rightFile = rightFiles[i] || null;
            
            item.innerHTML = `
                <select class="left-select" data-index="${i}">
                    <option value="">-- 选择左侧文件 --</option>
                    ${leftFiles.map((f, idx) => `
                        <option value="${idx}" ${idx === i ? 'selected' : ''}>${f.filename}</option>
                    `).join('')}
                </select>
                <span>⇄</span>
                <select class="right-select" data-index="${i}">
                    <option value="">-- 选择右侧文件 --</option>
                    ${rightFiles.map((f, idx) => `
                        <option value="${idx}" ${idx === i ? 'selected' : ''}>${f.filename}</option>
                    `).join('')}
                </select>
            `;
            
            this.associationList.appendChild(item);
        }
    }
    
    async handleConfigImport(event, side) {
        const file = event.target.files[0];
        if (!file) return;
        
        try {
            const content = await this.readFileContent(file);
            const config = this.parseConfigFile(content);
            
            if (config) {
                this.fillDatabaseConfig(side, config);
                this.showSuccess(`配置文件导入成功！已识别出数据库配置`);
            } else {
                this.showError('无法识别配置文件格式，请检查文件内容');
            }
        } catch (error) {
            this.showError('读取配置文件失败: ' + error.message);
        }
        
        event.target.value = '';
    }
    
    handleConfigTextParse(side) {
        const textarea = document.getElementById(`${side}-config-text`);
        const content = textarea.value.trim();
        
        if (!content) {
            this.showError('请先粘贴配置内容');
            return;
        }
        
        try {
            const config = this.parseConfigFile(content);
            
            if (config) {
                this.fillDatabaseConfig(side, config);
                this.showSuccess(`配置识别成功！已自动填充数据库配置`);
                textarea.value = '';
            } else {
                this.showError('无法识别配置格式，请检查内容是否正确');
            }
        } catch (error) {
            this.showError('配置解析失败: ' + error.message);
        }
    }
    
    readFileContent(file) {
        return new Promise((resolve, reject) => {
            const reader = new FileReader();
            reader.onload = (e) => resolve(e.target.result);
            reader.onerror = (e) => reject(new Error('文件读取失败'));
            reader.readAsText(file);
        });
    }
    
    parseConfigFile(content) {
        content = content.trim();
        
        const parsers = [
            this.parseYiiConfig,
            this.parseGoDSN,
            this.parseJSONConfig,
            this.parseINIConfig,
            this.parseENVConfig,
            this.parsePythonConfig,
            this.parseGenericConfig
        ];
        
        for (const parser of parsers) {
            try {
                const config = parser.call(this, content);
                if (config && config.host) {
                    return this.filterDbConfig(config);
                }
            } catch (e) {
                continue;
            }
        }
        
        return null;
    }
    
    filterDbConfig(config) {
        const filtered = {};
        const validKeys = ['host', 'port', 'database', 'user', 'password'];
        
        for (const key of validKeys) {
            if (config[key] && config[key] !== 'true' && config[key] !== 'false') {
                filtered[key] = config[key];
            }
        }
        
        if (filtered.port) {
            filtered.port = parseInt(filtered.port) || 3306;
        }
        
        return filtered;
    }
    
    parseYiiConfig(content) {
        const config = {};
        
        const connectionStringMatch = content.match(/connectionString['"]?\s*=>\s*['"]([^'"]+)['"]/i);
        if (connectionStringMatch) {
            const connStr = connectionStringMatch[1];
            
            const hostMatch = connStr.match(/host=([^;]+)/i);
            if (hostMatch) config.host = hostMatch[1];
            
            const portMatch = connStr.match(/port=(\d+)/i);
            if (portMatch) config.port = portMatch[1];
            
            const dbMatch = connStr.match(/dbname=([^;]+)/i);
            if (dbMatch) config.database = dbMatch[1];
        }
        
        if (!config.host) {
            const hostPatterns = [
                /mysql:host=([^;]+)/i,
                /host['"]?\s*=>\s*['"]([^'"]+)['"]/i
            ];
            for (const pattern of hostPatterns) {
                const match = content.match(pattern);
                if (match) {
                    config.host = match[1];
                    break;
                }
            }
        }
        
        if (!config.port) {
            const portMatch = content.match(/port[=:\s]+(\d+)/i);
            if (portMatch) config.port = portMatch[1];
        }
        
        if (!config.database) {
            const dbPatterns = [
                /dbname=([^;]+)/i,
                /database['"]?\s*=>\s*['"]([^'"]+)['"]/i
            ];
            for (const pattern of dbPatterns) {
                const match = content.match(pattern);
                if (match) {
                    config.database = match[1];
                    break;
                }
            }
        }
        
        const userPatterns = [
            /username['"]?\s*=>\s*['"]([^'"]+)['"]/i,
            /user['"]?\s*=>\s*['"]([^'"]+)['"]/i
        ];
        for (const pattern of userPatterns) {
            const match = content.match(pattern);
            if (match) {
                config.user = match[1];
                break;
            }
        }
        
        const passwordPatterns = [
            /password['"]?\s*=>\s*['"]([^'"]+)['"]/i
        ];
        for (const pattern of passwordPatterns) {
            const match = content.match(pattern);
            if (match) {
                config.password = match[1];
                break;
            }
        }
        
        return config.host ? config : null;
    }
    
    parseGoDSN(content) {
        const dsnPattern = /(\w+):(\w+)@tcp\(([^:]+):(\d+)\)\/(\w+)/i;
        const match = content.match(dsnPattern);
        
        if (match) {
            return {
                user: match[1],
                password: match[2],
                host: match[3],
                port: match[4],
                database: match[5]
            };
        }
        
        return null;
    }
    
    parseJSONConfig(content) {
        try {
            const json = JSON.parse(content);
            const config = {};
            
            const mappings = {
                host: ['host', 'hostname', 'server', 'db_host'],
                port: ['port', 'db_port'],
                database: ['database', 'db', 'dbname', 'database_name'],
                user: ['user', 'username', 'db_user', 'db_username'],
                password: ['password', 'pass', 'db_password']
            };
            
            for (const [key, aliases] of Object.entries(mappings)) {
                for (const alias of aliases) {
                    if (json[alias]) {
                        config[key] = json[alias];
                        break;
                    }
                }
            }
            
            return config.host ? config : null;
        } catch (e) {
            return null;
        }
    }
    
    parseINIConfig(content) {
        const config = {};
        const lines = content.split('\n');
        
        const mappings = {
            host: ['host', 'hostname', 'server', 'db_host'],
            port: ['port', 'db_port'],
            database: ['database', 'db', 'dbname', 'database_name'],
            user: ['user', 'username', 'db_user'],
            password: ['password', 'pass', 'db_password']
        };
        
        for (const line of lines) {
            const trimmed = line.trim();
            if (!trimmed || trimmed.startsWith('#') || trimmed.startsWith(';') || trimmed.startsWith('[')) {
                continue;
            }
            
            const [key, ...valueParts] = trimmed.split('=');
            if (key && valueParts.length > 0) {
                const normalizedKey = key.trim().toLowerCase();
                const value = valueParts.join('=').trim().replace(/^["']|["']$/g, '');
                
                for (const [configKey, aliases] of Object.entries(mappings)) {
                    if (aliases.includes(normalizedKey)) {
                        config[configKey] = value;
                        break;
                    }
                }
            }
        }
        
        return config.host ? config : null;
    }
    
    parseENVConfig(content) {
        const config = {};
        const lines = content.split('\n');
        
        const mappings = {
            host: ['db_host', 'database_host', 'mysql_host', 'host'],
            port: ['db_port', 'database_port', 'mysql_port', 'port'],
            database: ['db_name', 'database_name', 'mysql_database', 'database'],
            user: ['db_user', 'database_user', 'mysql_user', 'user', 'username'],
            password: ['db_password', 'database_password', 'mysql_password', 'password']
        };
        
        for (const line of lines) {
            const trimmed = line.trim();
            if (!trimmed || trimmed.startsWith('#')) {
                continue;
            }
            
            const [key, ...valueParts] = trimmed.split('=');
            if (key && valueParts.length > 0) {
                const normalizedKey = key.trim().toUpperCase();
                const value = valueParts.join('=').trim().replace(/^["']|["']$/g, '');
                
                for (const [configKey, aliases] of Object.entries(mappings)) {
                    if (aliases.some(alias => normalizedKey === alias.toUpperCase())) {
                        config[configKey] = value;
                        break;
                    }
                }
            }
        }
        
        return config.host ? config : null;
    }
    
    parsePythonConfig(content) {
        const config = {};
        
        const patterns = {
            host: [
                /(?:mysql_)?host\s*=\s*['"]([^'"]+)['"]/i,
                /'host'\s*:\s*'([^']+)'/i
            ],
            port: [
                /(?:mysql_)?port\s*=\s*(\d+)/i,
                /'port'\s*:\s*(\d+)/i
            ],
            database: [
                /(?:mysql_)?database\s*=\s*['"]([^'"]+)['"]/i,
                /(?:mysql_)?db\s*=\s*['"]([^'"]+)['"]/i,
                /'database'\s*:\s*'([^']+)'/i
            ],
            user: [
                /(?:mysql_)?user\s*=\s*['"]([^'"]+)['"]/i,
                /(?:mysql_)?username\s*=\s*['"]([^'"]+)['"]/i,
                /'user'\s*:\s*'([^']+)'/i
            ],
            password: [
                /(?:mysql_)?password\s*=\s*['"]([^'"]+)['"]/i,
                /(?:mysql_)?passwd\s*=\s*['"]([^'"]+)['"]/i,
                /'password'\s*:\s*'([^']+)'/i
            ]
        };
        
        for (const [key, patternList] of Object.entries(patterns)) {
            for (const pattern of patternList) {
                const match = content.match(pattern);
                if (match) {
                    config[key] = match[1];
                    break;
                }
            }
        }
        
        return config.host ? config : null;
    }
    
    parseGenericConfig(content) {
        const config = {};
        
        const patterns = {
            host: [
                /(?:host|hostname|server)\s*[=:]\s*['"]?([^'"\s;]+)['"]?/i,
                /host=([^;\s]+)/i
            ],
            port: [
                /(?:port)\s*[=:]\s*(\d+)/i,
                /port=(\d+)/i
            ],
            database: [
                /(?:database|db|dbname)\s*[=:]\s*['"]?([^'"\s;]+)['"]?/i,
                /dbname=([^;\s]+)/i,
                /database=([^;\s]+)/i
            ],
            user: [
                /(?:user|username)\s*[=:]\s*['"]?([^'"\s;]+)['"]?/i
            ],
            password: [
                /(?:password|passwd)\s*[=:]\s*['"]?([^'"\s;]+)['"]?/i
            ]
        };
        
        for (const [key, patternList] of Object.entries(patterns)) {
            for (const pattern of patternList) {
                const match = content.match(pattern);
                if (match) {
                    config[key] = match[1];
                    break;
                }
            }
        }
        
        return config.host ? config : null;
    }
    
    fillDatabaseConfig(side, config) {
        if (config.host) {
            document.getElementById(`${side}-host`).value = config.host;
        }
        if (config.port) {
            document.getElementById(`${side}-port`).value = config.port;
        }
        if (config.database) {
            document.getElementById(`${side}-database`).value = config.database;
        }
        if (config.user) {
            document.getElementById(`${side}-user`).value = config.user;
        }
        if (config.password) {
            document.getElementById(`${side}-password`).value = config.password;
        }
    }
    
    async startComparison() {
        const leftData = this.prepareComparisonData('left');
        const rightData = this.prepareComparisonData('right');
        
        if (!leftData || !rightData) {
            this.showError('请完成数据源配置');
            return;
        }
        
        this.compareBtn.disabled = true;
        this.compareBtn.innerHTML = '<span class="btn-icon">⏳</span> 对比中...';
        this.progressContainer.classList.remove('hidden');
        this.resultContainer.classList.add('hidden');
        this.errorContainer.classList.add('hidden');
        
        try {
            const response = await fetch('api/compare', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    left: leftData,
                    right: rightData
                })
            });
            
            const data = await response.json();
            
            if (data.success) {
                this.currentTaskId = data.taskId;
                this.pollTaskStatus();
            } else {
                this.showError(data.message);
                this.resetCompareButton();
            }
        } catch (error) {
            this.showError('启动对比失败: ' + error.message);
            this.resetCompareButton();
        }
    }
    
    async startDatabaseComparison() {
        if (!this.leftConfig.config || !this.rightConfig.config) {
            this.showError('请先完成左右数据库连接配置');
            return;
        }
        
        this.compareDatabaseBtn.disabled = true;
        this.compareDatabaseBtn.innerHTML = '<span class="btn-icon">⏳</span> 对比中...';
        this.progressContainer.classList.remove('hidden');
        this.resultContainer.classList.add('hidden');
        this.errorContainer.classList.add('hidden');
        
        try {
            const response = await fetch('api/compare-database', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    left: this.leftConfig.config,
                    right: this.rightConfig.config
                })
            });
            
            const data = await response.json();
            
            if (data.success) {
                this.currentTaskId = data.taskId;
                this.pollTaskStatus();
            } else {
                this.showError(data.message);
                this.resetDatabaseCompareButton();
            }
        } catch (error) {
            this.showError('启动数据库对比失败: ' + error.message);
            this.resetDatabaseCompareButton();
        }
    }
    
    prepareComparisonData(side) {
        const config = this[`${side}Config`];
        
        if (config.type === 'database') {
            if (!config.config || !config.table) {
                return null;
            }
            
            return {
                type: 'database',
                config: config.config,
                table: config.table
            };
        } else {
            if (config.files.length === 0) {
                return null;
            }
            
            return {
                type: 'file',
                filePath: config.files[0].path,
                fileName: config.files[0].filename
            };
        }
    }
    
    async pollTaskStatus() {
        const pollInterval = 1000;
        const maxAttempts = 300;
        let attempts = 0;
        
        const poll = async () => {
            if (!this.currentTaskId) return;
            
            attempts++;
            
            try {
                const response = await fetch(`api/compare/status?taskId=${this.currentTaskId}`);
                const data = await response.json();
                
                if (data.success) {
                    this.updateProgress(data.progress, data.status);
                    
                    if (data.status === 'completed') {
                        this.showResult(data.result);
                        this.resetAllButtons();
                    } else if (data.status === 'failed') {
                        this.showError(data.error || '对比失败');
                        this.resetAllButtons();
                    } else if (attempts < maxAttempts) {
                        setTimeout(poll, pollInterval);
                    } else {
                        this.showError('对比超时');
                        this.resetAllButtons();
                    }
                } else {
                    this.showError(data.message);
                    this.resetAllButtons();
                }
            } catch (error) {
                this.showError('查询状态失败: ' + error.message);
                this.resetAllButtons();
            }
        };
        
        poll();
    }
    
    updateProgress(progress, status) {
        this.progressFill.style.width = progress + '%';
        
        const statusTexts = {
            'pending': '准备中...',
            'running': '对比中...',
            'completed': '完成',
            'failed': '失败'
        };
        
        this.progressText.textContent = `${statusTexts[status] || status} (${progress}%)`;
    }
    
    showResult(result) {
        this.progressContainer.classList.add('hidden');
        this.resultContainer.classList.remove('hidden');
        this.reportUrl = result.reportUrl;
        
        const stats = result.stats;
        this.resultStats.innerHTML = `
            <div class="stat-item">
                <h4>${stats.left_count || 0}</h4>
                <p>左表总数据量</p>
            </div>
            <div class="stat-item">
                <h4>${stats.right_count || 0}</h4>
                <p>右表总数据量</p>
            </div>
            <div class="stat-item">
                <h4>${stats.common || 0}</h4>
                <p>相同数据</p>
            </div>
            <div class="stat-item">
                <h4>${stats.different || 0}</h4>
                <p>差异数据</p>
            </div>
            <div class="stat-item">
                <h4>${stats.left_only || 0}</h4>
                <p>左侧独有</p>
            </div>
            <div class="stat-item">
                <h4>${stats.right_only || 0}</h4>
                <p>右侧独有</p>
            </div>
        `;
    }
    
    resetCompareButton() {
        this.compareBtn.disabled = false;
        this.compareBtn.innerHTML = '<span class="btn-icon">▶️</span> 开始对比数据表';
        this.currentTaskId = null;
    }
    
    resetDatabaseCompareButton() {
        this.compareDatabaseBtn.disabled = false;
        this.compareDatabaseBtn.innerHTML = '<span class="btn-icon">🗄️</span> 开始对比数据库';
        this.currentTaskId = null;
    }
    
    resetAllButtons() {
        this.resetCompareButton();
        this.resetDatabaseCompareButton();
    }
    
    showSuccess(message) {
        this.errorContainer.classList.add('hidden');
        
        let successBox = document.getElementById('success-box');
        if (!successBox) {
            successBox = document.createElement('div');
            successBox.id = 'success-box';
            successBox.className = 'success-box';
            successBox.style.cssText = `
                position: fixed;
                top: 20px;
                right: 20px;
                background: linear-gradient(135deg, #28a745 0%, #20c997 100%);
                color: white;
                padding: 15px 25px;
                border-radius: 10px;
                box-shadow: 0 5px 20px rgba(40, 167, 69, 0.4);
                z-index: 10000;
                animation: slideIn 0.3s ease;
                font-weight: 600;
            `;
            document.body.appendChild(successBox);
        }
        
        successBox.textContent = '✅ ' + message;
        successBox.style.display = 'block';
        
        setTimeout(() => {
            successBox.style.display = 'none';
        }, 3000);
    }
    
    showError(message) {
        this.errorContent.textContent = message;
        this.errorContainer.classList.remove('hidden');
        this.resultContainer.classList.add('hidden');
        this.errorContainer.scrollIntoView({ behavior: 'smooth' });
    }
    
    async loadReports() {
        try {
            const response = await fetch('api/reports');
            const data = await response.json();
            
            if (data.success) {
                this.displayReports(data.reports);
            } else {
                this.historyList.innerHTML = '<div class="loading">加载失败</div>';
            }
        } catch (error) {
            this.historyList.innerHTML = '<div class="loading">加载失败</div>';
        }
    }
    
    displayReports(reports) {
        if (reports.length === 0) {
            this.historyList.innerHTML = '<div class="loading">暂无历史报告</div>';
            return;
        }
        
        this.historyList.innerHTML = '';
        this.selectedReports = new Set();
        
        const groupedReports = this.groupReportsByDate(reports);
        
        for (const [date, dateReports] of Object.entries(groupedReports)) {
            const dateGroup = document.createElement('div');
            dateGroup.className = 'date-group';
            
            const dateHeader = document.createElement('div');
            dateHeader.className = 'date-header';
            dateHeader.innerHTML = `
                <label class="date-checkbox">
                    <input type="checkbox" class="date-select-all" data-date="${date}">
                    <span class="checkmark"></span>
                </label>
                <span class="date-title">📅 ${date}</span>
                <span class="date-count">(${dateReports.length} 个报告)</span>
            `;
            
            const reportsContainer = document.createElement('div');
            reportsContainer.className = 'reports-container';
            
            dateReports.forEach(report => {
                const item = document.createElement('div');
                item.className = 'history-item';
                item.dataset.reportId = report.id;
                item.dataset.reportUrl = report.url;
                item.innerHTML = `
                    <label class="report-checkbox">
                        <input type="checkbox" class="report-select" data-report-id="${report.id}">
                        <span class="checkmark"></span>
                    </label>
                    <div class="report-info">
                        <div class="report-name">${report.filename}</div>
                        <div class="report-time">${report.timestamp}</div>
                    </div>
                    <button class="delete-icon" data-report-id="${report.id}" title="删除">✕</button>
                `;
                
                reportsContainer.appendChild(item);
            });
            
            dateGroup.appendChild(dateHeader);
            dateGroup.appendChild(reportsContainer);
            this.historyList.appendChild(dateGroup);
        }
        
        this.setupCheckboxListeners();
        
        this.historyList.querySelectorAll('.history-item').forEach(item => {
            item.addEventListener('click', (e) => {
                if (e.target.closest('.report-checkbox') || e.target.closest('.delete-icon')) {
                    return;
                }
                const url = item.dataset.reportUrl;
                if (url) {
                    window.open(url, '_blank');
                }
            });
        });
        
        this.historyList.querySelectorAll('.delete-icon').forEach(btn => {
            btn.addEventListener('click', (e) => {
                e.stopPropagation();
                this.deleteReport(e.target.dataset.reportId);
            });
        });
    }
    
    groupReportsByDate(reports) {
        const grouped = {};
        
        reports.forEach(report => {
            const dateMatch = report.id.match(/diff_report_(\d{8})/);
            const date = dateMatch ? dateMatch[1] : '未知日期';
            
            const formattedDate = this.formatDate(date);
            
            if (!grouped[formattedDate]) {
                grouped[formattedDate] = [];
            }
            grouped[formattedDate].push(report);
        });
        
        const sortedDates = Object.keys(grouped).sort((a, b) => b.localeCompare(a));
        const sortedGrouped = {};
        sortedDates.forEach(date => {
            sortedGrouped[date] = grouped[date];
        });
        
        return sortedGrouped;
    }
    
    formatDate(dateStr) {
        if (dateStr === '未知日期') return dateStr;
        
        if (dateStr.length === 8) {
            const year = dateStr.substring(0, 4);
            const month = dateStr.substring(4, 6);
            const day = dateStr.substring(6, 8);
            return `${year}-${month}-${day}`;
        }
        return dateStr;
    }
    
    setupCheckboxListeners() {
        document.querySelectorAll('.date-select-all').forEach(checkbox => {
            checkbox.addEventListener('change', (e) => {
                const dateGroup = e.target.closest('.date-group');
                const reportCheckboxes = dateGroup.querySelectorAll('.report-select');
                
                reportCheckboxes.forEach(cb => {
                    cb.checked = e.target.checked;
                    const reportId = cb.dataset.reportId;
                    if (e.target.checked) {
                        this.selectedReports.add(reportId);
                    } else {
                        this.selectedReports.delete(reportId);
                    }
                });
                
                this.updateSelectedCount();
            });
        });
        
        document.querySelectorAll('.report-select').forEach(checkbox => {
            checkbox.addEventListener('change', (e) => {
                const reportId = e.target.dataset.reportId;
                if (e.target.checked) {
                    this.selectedReports.add(reportId);
                } else {
                    this.selectedReports.delete(reportId);
                }
                
                this.updateDateSelectAllState(e.target);
                this.updateSelectedCount();
            });
        });
    }
    
    updateDateSelectAllState(checkbox) {
        const dateGroup = checkbox.closest('.date-group');
        const reportCheckboxes = dateGroup.querySelectorAll('.report-select');
        const dateSelectAll = dateGroup.querySelector('.date-select-all');
        const checkedCount = dateGroup.querySelectorAll('.report-select:checked').length;
        
        dateSelectAll.checked = checkedCount === reportCheckboxes.length;
        dateSelectAll.indeterminate = checkedCount > 0 && checkedCount < reportCheckboxes.length;
    }
    
    updateSelectedCount() {
        const count = this.selectedReports.size;
        document.getElementById('selected-count').textContent = count;
        document.getElementById('batch-delete-btn').disabled = count === 0;
    }
    
    async batchDeleteReports() {
        if (this.selectedReports.size === 0) {
            return;
        }
        
        if (!confirm(`确定要删除选中的 ${this.selectedReports.size} 个报告吗？`)) {
            return;
        }
        
        try {
            const response = await fetch('api/reports/batch-delete', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ ids: Array.from(this.selectedReports) })
            });
            
            const data = await response.json();
            
            if (data.success) {
                this.showSuccess(data.message);
                this.selectedReports.clear();
                await this.loadReports();
            } else {
                this.showError(data.message);
            }
        } catch (error) {
            this.showError('批量删除失败: ' + error.message);
        }
    }
    
    async deleteReport(reportId) {
        if (!confirm('确定要删除这个报告吗？')) {
            return;
        }
        
        try {
            const response = await fetch('api/reports/delete', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ id: reportId })
            });
            
            const data = await response.json();
            
            if (data.success) {
                this.showSuccess('报告已删除');
                await this.loadReports();
            } else {
                this.showError(data.message);
            }
        } catch (error) {
            this.showError('删除报告失败: ' + error.message);
        }
    }
}

document.addEventListener('DOMContentLoaded', () => {
    window.diffTool = new MySQLDiffTool();
});
