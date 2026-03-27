# MySQL 数据库差异对比工具

## 功能特性

✅ **核心对比功能**
- 对比两个表的字段结构
- 对比两个表的索引
- 对比两个表的数据差异
- 智能识别主键进行数据对比

✅ **多种数据源支持**
- 数据库直连对比
- SQL 文件对比
- CSV 文件对比
- JSON 文件对比
- **配置文件导入**（新增）

✅ **智能配置识别**
- 支持 Yii 框架配置格式
- 支持 Go DSN 连接字符串
- 支持 JSON 配置文件
- 支持 INI 配置文件
- 支持 ENV 环境变量文件
- 支持 Python 配置格式
- 自动填充数据库连接信息

✅ **智能报告生成**
- 生成专业的 HTML 报告
- 差异高亮显示
- 大数据量自动汇总
- 按时间分目录存储

✅ **独立脚本支持**
- 可脱离 Web 应用独立运行
- 支持命令行参数
- 适合自动化场景

## 使用方法

### 1. Web 界面使用

启动应用：
```bash
cd /Users/hashiqi/Documents/tencent_tke/quick_tool
python3 app.py
```

访问：http://localhost:5000/modules/mysql/mysql_diff

#### 数据库对比
1. **导入配置文件**（推荐）
   - 点击"导入配置文件"按钮
   - 选择配置文件（支持多种格式）
   - 自动填充数据库连接信息
   
2. **手动填写配置**
   - 填写主机地址、端口、数据库名
   - 填写用户名和密码
   - 点击"测试连接"
   
3. 选择要对比的表
4. 配置右侧数据源（同样支持导入配置）
5. 点击"开始对比"
6. 查看生成的报告

#### 文件对比
1. 切换到"文件上传"模式
2. 上传左侧文件（SQL/CSV/JSON）
3. 上传右侧文件
4. 点击"开始对比"
5. 查看生成的报告

### 2. 命令行使用

#### 对比数据库表
```bash
python3 db_diff_tool.py \
  --left-config left_db.json \
  --right-config right_db.json \
  --left-table table1 \
  --right-table table2 \
  --output ./reports
```

配置文件格式（left_db.json）：
```json
{
  "host": "localhost",
  "port": 3306,
  "database": "db_name",
  "user": "root",
  "password": "password"
}
```

#### 对比文件
```bash
python3 db_diff_tool.py \
  --left-file data1.sql \
  --right-file data2.sql \
  --output ./reports
```

#### 使用命令行参数
```bash
python3 db_diff_tool.py \
  --left-host localhost --left-port 3306 --left-db test --left-user root --left-pass password --left-table users \
  --right-host localhost --right-port 3306 --right-db test2 --right-user root --right-pass password --right-table users
```

## 项目结构

```
modules/mysql/mysql_diff/
├── app.py                    # Flask 蓝图主文件
├── db_connector.py           # 数据库连接器
├── db_comparator.py          # 数据库对比核心逻辑
├── report_generator.py       # HTML 报告生成器
├── file_parser.py            # 文件解析器
├── db_diff_tool.py           # 独立运行脚本
├── templates/
│   └── index.html            # 主页面模板
├── static/
│   ├── app.js                # 前端 JavaScript
│   └── style.css             # 样式文件
└── uploads/                  # 上传文件临时目录
```

## 报告说明

### 报告存储位置
```
static/reports/{year}/{month}/diff_report_{timestamp}.html
```

### 报告内容
1. **对比概览**：统计信息汇总
2. **结构差异**：
   - 共有字段
   - 左表独有字段
   - 右表独有字段
   - 差异字段
   - 索引对比
3. **数据差异**：
   - 相同数据
   - 差异数据（高亮显示）
   - 左表独有数据
   - 右表独有数据

### 大数据量处理
- 当差异数据超过 50 条时，自动汇总显示主键列表
- 避免报告过大，提高可读性

## 支持的配置文件格式

### 1. Yii 框架配置
```php
'mysql:host=m5011i.xxxx.com;port=5011;dbname=calendarapi',
'username' => 'test_user',
'password' => 'test_password',
'charset' => 'utf8',
```

### 2. Go DSN 连接字符串
```
mysql_conn = testuser:DM4OWQ@tcp(m3849i_txxxxx.com:3849)/upgrade?charset=utf8
```

### 3. JSON 配置
```json
{
  "host": "localhost",
  "port": 3306,
  "database": "test_db",
  "user": "root",
  "password": "password123"
}
```

### 4. INI 配置文件
```ini
[database]
host = db.example.com
port = 3308
database = production_db
user = prod_user
password = prod_password
```

### 5. ENV 环境变量
```env
DB_HOST=192.168.1.100
DB_PORT=3307
DB_NAME=myapp_production
DB_USER=app_user
DB_PASSWORD=secure_pass
```

### 6. Python 配置
```python
MYSQL_HOST = 'localhost'
MYSQL_PORT = 3306
MYSQL_DATABASE = 'mydb'
MYSQL_USER = 'root'
MYSQL_PASSWORD = 'password'
```

## 技术栈

- **后端**: Flask + Python 3.7+
- **前端**: HTML5 + CSS3 + JavaScript
- **数据库**: MySQL 5.7+
- **依赖**: 
  - Flask >= 2.0.0
  - PyMySQL >= 1.0.0

## 安装依赖

```bash
pip install -r requirements.txt
```

## 注意事项

1. **数据库连接**：确保数据库允许远程连接
2. **文件大小**：最大支持 50MB 的文件上传
3. **主键识别**：建议表有明确的主键，以便准确对比
4. **性能优化**：大数据量对比会分批查询，避免内存溢出

## 示例

查看 `uploads/` 目录下的测试文件：
- `test_left.sql` - 左侧测试数据
- `test_right.sql` - 右侧测试数据

运行测试：
```bash
python3 db_diff_tool.py \
  --left-file uploads/test_left.sql \
  --right-file uploads/test_right.sql \
  --output ../../../static/reports
```

## 更新日志

### v1.0.0 (2026-03-25)
- ✅ 完成核心对比功能
- ✅ 支持 SQL/CSV/JSON 文件解析
- ✅ 生成专业的 HTML 报告
- ✅ 提供独立运行脚本
- ✅ Web 界面完整实现
