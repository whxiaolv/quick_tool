#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MySQL数据库全库对比工具
用于比较两个MySQL数据库之间所有表的差异
只执行只读查询操作，不会修改任何数据
"""

import pymysql
from pymysql.cursors import DictCursor
from typing import Dict, List, Optional
import re
from datetime import datetime
import os


class MySQLDatabaseFullComparator:
    """MySQL数据库全库对比器"""

    def __init__(self, left_config: Dict, right_config: Dict):
        """
        初始化数据库对比器
        
        Args:
            left_config: 左侧数据库配置
            right_config: 右侧数据库配置
        """
        self.left_config = left_config
        self.right_config = right_config
        self.connections: Dict[str, pymysql.Connection] = {}

    def _create_connection(self, config: Dict) -> pymysql.Connection:
        """
        创建数据库连接

        Args:
            config: 数据库配置

        Returns:
            数据库连接对象
        """
        connection = pymysql.connect(
            host=config.get('host', 'localhost'),
            port=config.get('port', 3306),
            user=config.get('user', 'root'),
            password=config.get('password', ''),
            database=config.get('database', ''),
            charset=config.get('charset', 'utf8mb4'),
            cursorclass=DictCursor,
            read_timeout=30,
            write_timeout=30,
            connect_timeout=10
        )

        return connection

    def connect(self):
        """连接到所有数据库"""
        print("正在连接数据库...")

        try:
            self.connections['left'] = self._create_connection(self.left_config)
            print(f"✓ 左侧数据库 ({self.left_config['database']}) 连接成功")
        except Exception as e:
            print(f"✗ 左侧数据库连接失败: {e}")
            raise

        try:
            self.connections['right'] = self._create_connection(self.right_config)
            print(f"✓ 右侧数据库 ({self.right_config['database']}) 连接成功")
        except Exception as e:
            print(f"✗ 右侧数据库连接失败: {e}")
            raise

    def close(self):
        """关闭所有数据库连接"""
        for db_key, conn in self.connections.items():
            if conn:
                conn.close()
                print(f"✓ {db_key} 连接已关闭")

    def _execute_query(self, db_key: str, sql: str, params: tuple = None) -> List[Dict]:
        """
        执行只读查询（带安全检查）

        Args:
            db_key: 数据库配置键名
            sql: SQL查询语句
            params: 查询参数

        Returns:
            查询结果列表
        """
        sql_upper = sql.strip().upper()
        forbidden_keywords = ['INSERT', 'UPDATE', 'DELETE', 'CREATE', 'DROP',
                            'ALTER', 'TRUNCATE', 'REPLACE', 'GRANT', 'REVOKE']

        for keyword in forbidden_keywords:
            if sql_upper.startswith(keyword):
                raise ValueError(f"禁止执行写操作: {keyword}")

        conn = self.connections.get(db_key)
        if not conn:
            raise ValueError(f"数据库 {db_key} 未连接")

        with conn.cursor() as cursor:
            cursor.execute(sql, params)
            return cursor.fetchall()

    def get_all_tables(self, db_key: str, database: str) -> List[str]:
        """
        获取数据库中所有表名

        Args:
            db_key: 数据库配置键名
            database: 数据库名

        Returns:
            表名列表
        """
        sql = """
            SELECT TABLE_NAME
            FROM information_schema.TABLES
            WHERE TABLE_SCHEMA = %s
            AND TABLE_TYPE = 'BASE TABLE'
            ORDER BY TABLE_NAME
        """

        results = self._execute_query(db_key, sql, (database,))
        return [row['TABLE_NAME'] for row in results]

    def get_table_row_count(self, db_key: str, table_name: str) -> int:
        """
        获取表的精确行数

        Args:
            db_key: 数据库配置键名
            table_name: 表名

        Returns:
            行数
        """
        sql = f"SELECT COUNT(*) as row_count FROM `{table_name}`"
        result = self._execute_query(db_key, sql)

        if result:
            return result[0]['row_count'] or 0
        return 0

    def find_update_time_column(self, db_key: str, database: str, table_name: str) -> Optional[str]:
        """
        查找表中的update_time相关字段
        支持多种命名方式：updateTime, updatetime, update_time, UPDATE_TIME等

        Args:
            db_key: 数据库配置键名
            database: 数据库名
            table_name: 表名

        Returns:
            找到的字段名，如果没找到返回None
        """
        sql = """
            SELECT COLUMN_NAME
            FROM information_schema.COLUMNS
            WHERE TABLE_SCHEMA = %s
            AND TABLE_NAME = %s
        """

        results = self._execute_query(db_key, sql, (database, table_name))
        columns = [row['COLUMN_NAME'] for row in results]

        patterns = [
            r'^update_?time$',
            r'^updateTime$',
            r'^updatetime$',
            r'^UPDATE_?TIME$',
            r'^UPDATETIME$'
        ]

        for col in columns:
            for pattern in patterns:
                if re.match(pattern, col, re.IGNORECASE):
                    return col

        return None

    def get_latest_update_time(self, db_key: str, table_name: str,
                               column_name: str) -> Optional[datetime]:
        """
        获取表中最近的更新时间

        Args:
            db_key: 数据库配置键名
            table_name: 表名
            column_name: 时间字段名

        Returns:
            最近的更新时间
        """
        sql = f"""
            SELECT `{column_name}`
            FROM `{table_name}`
            WHERE `{column_name}` IS NOT NULL
            ORDER BY `{column_name}` DESC
            LIMIT 1
        """

        result = self._execute_query(db_key, sql)

        if result and result[0][column_name]:
            value = result[0][column_name]
            if isinstance(value, int):
                try:
                    if value > 10000000000:
                        value = value // 1000
                    return datetime.fromtimestamp(value)
                except (OSError, OverflowError, ValueError):
                    return None
            elif isinstance(value, datetime):
                return value
            elif isinstance(value, str):
                for fmt in ['%Y-%m-%d %H:%M:%S', '%Y-%m-%d %H:%M:%S.%f',
                           '%Y-%m-%d', '%Y/%m/%d %H:%M:%S']:
                    try:
                        return datetime.strptime(value, fmt)
                    except ValueError:
                        continue
                try:
                    ts = int(value)
                    if ts > 10000000000:
                        ts = ts // 1000
                    return datetime.fromtimestamp(ts)
                except (OSError, OverflowError, ValueError):
                    return None
        return None

    def compare_databases(self) -> Dict:
        """
        对比两个数据库

        Returns:
            对比结果字典
        """
        print("\n" + "="*80)
        print("开始对比数据库")
        print("="*80)

        left_name = self.left_config['database']
        right_name = self.right_config['database']

        print(f"\n左侧数据库: {left_name}")
        print(f"右侧数据库: {right_name}")

        print("\n[1/4] 获取表列表...")
        left_tables = set(self.get_all_tables('left', left_name))
        right_tables = set(self.get_all_tables('right', right_name))

        common_tables = left_tables & right_tables
        left_only_tables = left_tables - right_tables
        right_only_tables = right_tables - left_tables

        print(f"  - 左侧数据库独有表: {len(left_only_tables)} 个")
        print(f"  - 右侧数据库独有表: {len(right_only_tables)} 个")
        print(f"  - 共有表: {len(common_tables)} 个")

        print("\n[2/4] 统计表数据量...")
        table_stats = []

        all_tables = sorted(left_tables | right_tables)

        for i, table in enumerate(all_tables, 1):
            print(f"  处理进度: [{i}/{len(all_tables)}] {table}", end='\r')

            stat = {
                'table_name': table,
                'in_left': table in left_tables,
                'in_right': table in right_tables,
                'left_row_count': None,
                'right_row_count': None,
                'update_time_column': None,
                'left_latest_update': None,
                'right_latest_update': None
            }

            if table in left_tables:
                stat['left_row_count'] = self.get_table_row_count('left', table)

            if table in right_tables:
                stat['right_row_count'] = self.get_table_row_count('right', table)

            table_stats.append(stat)

        print(f"  处理进度: [{len(all_tables)}/{len(all_tables)}] 完成" + " " * 20)

        print("\n[3/4] 查找update_time字段并获取最近更新时间...")

        for i, stat in enumerate(table_stats, 1):
            table = stat['table_name']
            print(f"  处理进度: [{i}/{len(table_stats)}] {table}", end='\r')

            update_col = None

            if stat['in_left']:
                update_col = self.find_update_time_column('left', left_name, table)

            if not update_col and stat['in_right']:
                update_col = self.find_update_time_column('right', right_name, table)

            if update_col:
                stat['update_time_column'] = update_col

                if stat['in_left']:
                    stat['left_latest_update'] = self.get_latest_update_time(
                        'left', table, update_col
                    )

                if stat['in_right']:
                    stat['right_latest_update'] = self.get_latest_update_time(
                        'right', table, update_col
                    )

        print(f"  处理进度: [{len(table_stats)}/{len(table_stats)}] 完成" + " " * 20)

        result = {
            'left_name': left_name,
            'right_name': right_name,
            'left_table_count': len(left_tables),
            'right_table_count': len(right_tables),
            'common_table_count': len(common_tables),
            'left_only_tables': sorted(left_only_tables),
            'right_only_tables': sorted(right_only_tables),
            'table_stats': table_stats
        }

        return result

    def generate_report(self, result: Dict, output_file: str = None):
        """
        生成对比报告

        Args:
            result: 对比结果
            output_file: 输出文件路径（可选）
        """
        html_content = self._generate_html_report(result)

        if output_file:
            os.makedirs(os.path.dirname(output_file), exist_ok=True)
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(html_content)
            print(f"\n报告已保存到: {output_file}")

        return html_content

    def _generate_html_report(self, result: Dict) -> str:
        """
        生成HTML格式的报告

        Args:
            result: 对比结果

        Returns:
            HTML字符串
        """
        html_parts = []

        html_parts.append('''<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>MySQL数据库对比报告</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        body {
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
        }
        .container {
            max-width: 1400px;
            margin: 0 auto;
            background: white;
            border-radius: 16px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
            overflow: hidden;
        }
        .header {
            background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%);
            color: white;
            padding: 30px;
            text-align: center;
        }
        .header h1 {
            font-size: 28px;
            margin-bottom: 10px;
        }
        .header .time {
            opacity: 0.8;
            font-size: 14px;
        }
        .content {
            padding: 30px;
        }
        .section {
            margin-bottom: 30px;
        }
        .section-title {
            font-size: 20px;
            color: #1e3c72;
            border-bottom: 3px solid #1e3c72;
            padding-bottom: 10px;
            margin-bottom: 20px;
        }
        .stats-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }
        .stat-card {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 20px;
            border-radius: 12px;
            text-align: center;
        }
        .stat-card.left-db {
            background: linear-gradient(135deg, #11998e 0%, #38ef7d 100%);
        }
        .stat-card.right-db {
            background: linear-gradient(135deg, #ee0979 0%, #ff6a00 100%);
        }
        .stat-card .label {
            font-size: 14px;
            opacity: 0.9;
            margin-bottom: 5px;
        }
        .stat-card .value {
            font-size: 28px;
            font-weight: bold;
        }
        .unique-tables {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 20px;
            margin-bottom: 30px;
        }
        .unique-tables .box {
            background: #f8f9fa;
            border-radius: 12px;
            padding: 20px;
        }
        .unique-tables .box h3 {
            color: #495057;
            margin-bottom: 15px;
            font-size: 16px;
        }
        .unique-tables .box.left-db h3 {
            color: #11998e;
        }
        .unique-tables .box.right-db h3 {
            color: #ee0979;
        }
        .unique-tables ul {
            list-style: none;
            max-height: 200px;
            overflow-y: auto;
        }
        .unique-tables li {
            padding: 8px 12px;
            background: white;
            margin-bottom: 5px;
            border-radius: 6px;
            font-size: 14px;
        }
        .table-container {
            overflow-x: auto;
        }
        table {
            width: 100%;
            border-collapse: collapse;
            font-size: 14px;
        }
        th {
            background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%);
            color: white;
            padding: 15px 12px;
            text-align: left;
            font-weight: 600;
            position: sticky;
            top: 0;
        }
        td {
            padding: 12px;
            border-bottom: 1px solid #e9ecef;
            vertical-align: top;
        }
        tr:hover {
            background: #f8f9fa;
        }
        .table-name {
            font-weight: 600;
            color: #1e3c72;
            min-width: 150px;
        }
        .db-cell {
            min-width: 250px;
        }
        .db-cell.left-db {
            border-left: 4px solid #11998e;
        }
        .db-cell.right-db {
            border-left: 4px solid #ee0979;
        }
        .row-count {
            font-size: 18px;
            font-weight: bold;
            color: #333;
        }
        .update-time {
            font-size: 12px;
            color: #666;
            margin-top: 5px;
        }
        .no-update {
            color: #999;
            font-style: italic;
        }
        .table-not-exist {
            color: #dc3545;
            font-style: italic;
        }
        .diff-highlight {
            background: #fff3cd;
            padding: 2px 6px;
            border-radius: 4px;
        }
        .footer {
            text-align: center;
            padding: 20px;
            background: #f8f9fa;
            color: #6c757d;
            font-size: 14px;
        }
        @media (max-width: 768px) {
            .unique-tables {
                grid-template-columns: 1fr;
            }
            .stats-grid {
                grid-template-columns: 1fr;
            }
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>📊 MySQL数据库对比报告</h1>
            <div class="time">生成时间: ''' + datetime.now().strftime('%Y-%m-%d %H:%M:%S') + '''</div>
        </div>
        <div class="content">
            <div class="section">
                <div class="stats-grid">
                    <div class="stat-card left-db">
                        <div class="label">左侧数据库</div>
                        <div class="value">''' + str(result['left_table_count']) + '''</div>
                        <div class="label">''' + result['left_name'] + '''</div>
                    </div>
                    <div class="stat-card right-db">
                        <div class="label">右侧数据库</div>
                        <div class="value">''' + str(result['right_table_count']) + '''</div>
                        <div class="label">''' + result['right_name'] + '''</div>
                    </div>
                    <div class="stat-card">
                        <div class="label">共有表</div>
                        <div class="value">''' + str(result['common_table_count']) + '''</div>
                    </div>
                </div>
            </div>''')

        if result['left_only_tables'] or result['right_only_tables']:
            html_parts.append('''
            <div class="section">
                <div class="unique-tables">''')

            if result['left_only_tables']:
                html_parts.append('''
                    <div class="box left-db">
                        <h3>📁 左侧数据库独有表 (''' + str(len(result['left_only_tables'])) + '''个)</h3>
                        <ul>''')
                for table in result['left_only_tables']:
                    html_parts.append(f'<li>{table}</li>')
                html_parts.append('''
                        </ul>
                    </div>''')

            if result['right_only_tables']:
                html_parts.append('''
                    <div class="box right-db">
                        <h3>📁 右侧数据库独有表 (''' + str(len(result['right_only_tables'])) + '''个)</h3>
                        <ul>''')
                for table in result['right_only_tables']:
                    html_parts.append(f'<li>{table}</li>')
                html_parts.append('''
                        </ul>
                    </div>''')

            html_parts.append('''
                </div>
            </div>''')

        html_parts.append('''
            <div class="section">
                <h2 class="section-title">📋 表数据量对比详情</h2>
                <div class="table-container">
                    <table>
                        <thead>
                            <tr>
                                <th>表名</th>
                                <th>''' + result['left_name'] + ''' (左侧)</th>
                                <th>''' + result['right_name'] + ''' (右侧)</th>
                            </tr>
                        </thead>
                        <tbody>''')

        for stat in result['table_stats']:
            table = stat['table_name']

            html_parts.append('''
                            <tr>
                                <td class="table-name">''' + table + '''</td>''')

            html_parts.append('''
                                <td class="db-cell left-db">''')
            if stat['in_left']:
                html_parts.append('''
                    <div class="row-count">''' + str(stat['left_row_count']) + ''' 条数据</div>''')
                if stat['left_latest_update']:
                    html_parts.append('''
                    <div class="update-time">最近更新: ''' + stat['left_latest_update'].strftime('%Y-%m-%d %H:%M:%S') + '''</div>''')
                else:
                    if stat['update_time_column']:
                        html_parts.append('''
                    <div class="update-time no-update">无更新时间数据</div>''')
                    else:
                        html_parts.append('''
                    <div class="update-time no-update">没有更新字段</div>''')
            else:
                html_parts.append('''
                    <div class="table-not-exist">表不存在</div>''')
            html_parts.append('''
                                </td>''')

            html_parts.append('''
                                <td class="db-cell right-db">''')
            if stat['in_right']:
                html_parts.append('''
                    <div class="row-count">''' + str(stat['right_row_count']) + ''' 条数据</div>''')
                if stat['right_latest_update']:
                    html_parts.append('''
                    <div class="update-time">最近更新: ''' + stat['right_latest_update'].strftime('%Y-%m-%d %H:%M:%S') + '''</div>''')
                else:
                    if stat['update_time_column']:
                        html_parts.append('''
                    <div class="update-time no-update">无更新时间数据</div>''')
                    else:
                        html_parts.append('''
                    <div class="update-time no-update">没有更新字段</div>''')
            else:
                html_parts.append('''
                    <div class="table-not-exist">表不存在</div>''')
            html_parts.append('''
                                </td>
                            </tr>''')

        html_parts.append('''
                        </tbody>
                    </table>
                </div>
            </div>
        </div>
        <div class="footer">
            报告生成完成 | MySQL数据库对比工具
        </div>
    </div>
</body>
</html>''')

        return ''.join(html_parts)
