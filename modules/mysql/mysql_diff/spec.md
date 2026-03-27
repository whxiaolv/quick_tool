# 数据库对比功能规范文档

## 1. 项目概述

### 1.1 项目名称
MYSQL 数据库差异对比工具 (MySQL Database Diff Tool)

### 1.2 项目目标
开发一个基于 Flask + Python + HTML + JS + CSS 的数据库对比工具，用于对比两个数据库表的结构和数据差异，生成可视化的 HTML 报告。

### 1.3 技术栈
- **后端**: Flask (Python 3.7+)
- **前端**: HTML5 + CSS3 + JavaScript (原生)
- **数据库**: MySQL 5.7+
- **依赖库**: 
  - Flask
  - PyMySQL 或 mysql-connector-python
  - pandas (可选，用于数据处理)

## 2. 功能需求

### 2.1 核心功能

#### 2.1.1 数据库连接配置
- 支持配置两个数据库连接（左右对比）
- 连接参数包括：
  - 主机地址 (host)
  - 端口号 (port)
  - 数据库名 (database)
  - 用户名 (user)
  - 密码 (password)
- 支持保存连接配置（可选）

#### 2.1.2 表结构对比
对比两个表的以下内容：
- **字段对比**：
  - 共有字段
  - 左表独有字段
  - 右表独有字段
  - 字段类型差异
  - 字段属性差异（NULL/NOT NULL, DEFAULT, COMMENT等）

- **索引对比**：
  - 共有索引
  - 左表独有索引
  - 右表独有索引
  - 索引结构差异

#### 2.1.3 数据对比
- **对比策略**：
  - 基于主键进行数据对比
  - 如果没有主键，使用所有字段联合对比
  - 支持指定对比字段（可选）

- **对比结果**：
  - 完全相同的数据
  - 数据差异（同一主键，字段值不同）
  - 左表独有数据
  - 右表独有数据

- **差异展示**：
  - 如果差异记录 ≤ 50条：显示完整数据
  - 如果差异记录 > 50条：仅显示主键ID列表，提供汇总统计

#### 2.1.4 文件上传功能
- 支持上传 SQL 文件或 CSV 文件
- 左右两个上传区域
- 支持单个或多个文件上传
- 默认左右一对一对比
- 多文件时可手动关联对比关系

#### 2.1.5 报告生成
- 生成 HTML 格式的对比报告
- 报告存储路径：`static/reports/{year}/{month}/`
- 文件命名格式：`diff_report_{timestamp}.html`
- 报告内容：
  - 对比概览（统计信息）
  - 结构差异详情
  - 数据差异详情
  - 差异高亮显示

### 2.2 用户界面需求

#### 2.2.1 主页面布局
```
+--------------------------------------------------+
|                   页面头部                         |
|          数据库差异对比工具                        |
+--------------------------------------------------+
|                                                  |
|  +--------------------+    +--------------------+ |
|  |   左侧数据库配置    |    |   右侧数据库配置    | |
|  |   或文件上传        |    |   或文件上传        | |
|  +--------------------+    +--------------------+ |
|                                                  |
|  +------------------------------------------+   |
|  |          文件关联区域（多文件时）            |   |
|  +------------------------------------------+   |
|                                                  |
|  +------------------------------------------+   |
|  |              对比按钮                      |   |
|  +------------------------------------------+   |
|                                                  |
|  +------------------------------------------+   |
|  |          对比结果列表                      |   |
|  |    (点击查看详细报告)                      |   |
|  +------------------------------------------+   |
|                                                  |
+--------------------------------------------------+
```

#### 2.2.2 对比结果页面
- 新窗口打开
- 左右分栏显示差异
- 差异部分高亮显示
- 支持折叠/展开
- 响应式设计

### 2.3 独立脚本需求
- 提供独立的 Python 脚本 `db_diff_tool.py`
- 支持命令行参数：
  - `--left-config`: 左侧数据库配置文件
  - `--right-config`: 右侧数据库配置文件
  - `--left-table`: 左侧表名
  - `--right-table`: 右侧表名
  - `--output`: 输出目录
- 可脱离 Web 应用独立运行

## 3. 技术设计

### 3.1 项目结构
```
quick_tool/
├── modules/
│   └── mysql/
│       └── mysql_diff/
│           ├── app.py                    # Flask 蓝图主文件
│           ├── db_connector.py           # 数据库连接器
│           ├── db_comparator.py          # 数据库对比核心逻辑
│           ├── report_generator.py       # HTML 报告生成器
│           ├── templates/
│           │   └── index.html            # 主页面模板
│           ├── static/
│           │   ├── app.js                # 前端 JavaScript
│           │   └── style.css             # 样式文件
│           └── uploads/                  # 上传文件临时目录
├── static/
│   └── reports/                          # 报告存储目录
│       └── {year}/
│           └── {month}/
└── db_diff_tool.py                       # 独立运行脚本
```

### 3.2 数据库对比算法

#### 3.2.1 表结构对比流程
```
1. 获取左表结构 (DESCRIBE table_left)
2. 获取右表结构 (DESCRIBE table_right)
3. 获取左表索引 (SHOW INDEX FROM table_left)
4. 获取右表索引 (SHOW INDEX FROM table_right)
5. 对比字段：
   - 找出共有字段
   - 找出独有字段
   - 对比字段属性
6. 对比索引：
   - 找出共有索引
   - 找出独有索引
   - 对比索引结构
```

#### 3.2.2 数据对比流程
```
1. 确定主键字段
2. 获取左表数据
3. 获取右表数据
4. 构建数据字典（以主键为键）
5. 对比数据：
   - 共有数据：主键在两边都存在
   - 差异数据：主键存在但字段值不同
   - 独有数据：主键只在一侧存在
6. 统计差异
7. 生成报告
```

### 3.3 API 接口设计

#### 3.3.1 数据库连接测试
```
POST /api/test-connection
Request:
{
  "host": "localhost",
  "port": 3306,
  "database": "db_name",
  "user": "root",
  "password": "password"
}
Response:
{
  "success": true,
  "message": "连接成功"
}
```

#### 3.3.2 获取数据库表列表
```
GET /api/tables?host=xxx&port=xxx&database=xxx&user=xxx&password=xxx
Response:
{
  "tables": ["table1", "table2", ...]
}
```

#### 3.3.3 执行对比
```
POST /api/compare
Request:
{
  "left": {
    "type": "database",  // 或 "file"
    "config": { ... },   // 数据库配置
    "table": "table_name",
    "file": null         // 文件路径（如果type=file）
  },
  "right": {
    "type": "database",
    "config": { ... },
    "table": "table_name",
    "file": null
  }
}
Response:
{
  "success": true,
  "reportId": "report_20260325_123456",
  "reportUrl": "/static/reports/2026/03/diff_report_20260325_123456.html"
}
```

#### 3.3.4 文件上传
```
POST /api/upload
Request: multipart/form-data
Response:
{
  "success": true,
  "files": [
    {
      "filename": "table1.sql",
      "path": "/uploads/xxx/table1.sql",
      "size": 1024
    }
  ]
}
```

#### 3.3.5 获取对比历史
```
GET /api/reports
Response:
{
  "reports": [
    {
      "id": "report_20260325_123456",
      "timestamp": "2026-03-25 12:34:56",
      "leftTable": "table1",
      "rightTable": "table2",
      "url": "/static/reports/2026/03/diff_report_20260325_123456.html"
    }
  ]
}
```

### 3.4 HTML 报告设计

#### 3.4.1 报告结构
```html
<!DOCTYPE html>
<html>
<head>
  <meta charset="UTF-8">
  <title>数据库对比报告</title>
  <style>
    /* 内联样式，确保报告独立可查看 */
  </style>
</head>
<body>
  <div class="report-container">
    <!-- 报告头部 -->
    <header>
      <h1>数据库对比报告</h1>
      <div class="meta-info">...</div>
    </header>
    
    <!-- 对比概览 -->
    <section class="overview">
      <h2>对比概览</h2>
      <div class="stats">...</div>
    </section>
    
    <!-- 结构差异 -->
    <section class="structure-diff">
      <h2>结构差异</h2>
      <div class="field-diff">...</div>
      <div class="index-diff">...</div>
    </section>
    
    <!-- 数据差异 -->
    <section class="data-diff">
      <h2>数据差异</h2>
      <div class="diff-table">...</div>
    </section>
  </div>
</body>
</html>
```

#### 3.4.2 样式设计
- 使用渐变色背景
- 差异部分使用红色高亮
- 共有部分使用绿色标识
- 独有部分使用蓝色标识
- 响应式布局，支持移动端查看

## 4. 实现细节

### 4.1 数据库连接器 (db_connector.py)
```python
class DatabaseConnector:
    def __init__(self, config):
        self.config = config
        self.connection = None
    
    def connect(self):
        # 建立数据库连接
        
    def get_table_structure(self, table_name):
        # 获取表结构
        
    def get_table_indexes(self, table_name):
        # 获取表索引
        
    def get_table_data(self, table_name):
        # 获取表数据
        
    def close(self):
        # 关闭连接
```

### 4.2 数据库对比器 (db_comparator.py)
```python
class DatabaseComparator:
    def __init__(self, left_connector, right_connector):
        self.left = left_connector
        self.right = right_connector
    
    def compare_structure(self, left_table, right_table):
        # 对比表结构
        
    def compare_data(self, left_table, right_table):
        # 对比数据
        
    def _compare_fields(self, left_fields, right_fields):
        # 对比字段
        
    def _compare_indexes(self, left_indexes, right_indexes):
        # 对比索引
        
    def _compare_rows(self, left_data, right_data, primary_key):
        # 对比数据行
```

### 4.3 报告生成器 (report_generator.py)
```python
class ReportGenerator:
    def __init__(self, output_dir):
        self.output_dir = output_dir
    
    def generate(self, comparison_result):
        # 生成 HTML 报告
        
    def _generate_overview(self, result):
        # 生成概览部分
        
    def _generate_structure_diff(self, result):
        # 生成结构差异部分
        
    def _generate_data_diff(self, result):
        # 生成数据差异部分
        
    def _save_report(self, html_content):
        # 保存报告文件
```

### 4.4 文件解析器
```python
class FileParser:
    @staticmethod
    def parse_sql_file(file_path):
        # 解析 SQL 文件，提取表结构和数据
        
    @staticmethod
    def parse_csv_file(file_path):
        # 解析 CSV 文件
```

## 5. 安全性考虑

### 5.1 数据库连接安全
- 不在前端明文存储密码
- 使用加密传输敏感信息
- 连接超时设置
- 连接池管理

### 5.2 文件上传安全
- 限制文件大小（最大 50MB）
- 限制文件类型（.sql, .csv）
- 文件名消毒
- 上传目录权限控制

### 5.3 输入验证
- SQL 注入防护
- XSS 防护
- 参数验证

## 6. 性能优化

### 6.1 大数据量处理
- 分页查询数据
- 流式处理
- 异步对比
- 进度反馈

### 6.2 缓存策略
- 缓存表结构信息
- 缓存对比结果（可选）

## 7. 测试计划

### 7.1 单元测试
- 数据库连接测试
- 结构对比测试
- 数据对比测试
- 报告生成测试

### 7.2 集成测试
- 端到端对比流程测试
- 文件上传测试
- 多文件关联测试

### 7.3 性能测试
- 大数据量对比测试
- 并发对比测试

## 8. 部署说明

### 8.1 环境要求
- Python 3.7+
- MySQL 5.7+
- 所需依赖见 requirements.txt

### 8.2 配置说明
- 数据库连接配置
- 报告存储路径配置
- 上传文件大小限制配置

## 9. 后续扩展

### 9.1 可能的功能扩展
- 支持更多数据库类型（PostgreSQL, SQLite 等）
- 支持定时对比任务
- 支持对比结果导出（Excel, PDF）
- 支持对比结果订阅通知
- 支持数据同步功能

### 9.2 性能优化方向
- 使用多线程对比
- 使用内存数据库加速
- 支持增量对比
