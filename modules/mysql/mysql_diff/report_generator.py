import os
from datetime import datetime
from typing import Dict, List, Any
import json
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ReportGenerator:
    def __init__(self, output_dir: str):
        self.output_dir = output_dir
        self.max_display_rows = 50

    def generate(self, comparison_result: Dict[str, Any], left_name: str, right_name: str) -> str:
        logger.info("开始生成对比报告")

        now = datetime.now()
        year = now.strftime('%Y')
        month = now.strftime('%m')
        timestamp = now.strftime('%Y%m%d_%H%M%S')

        report_dir = os.path.join(self.output_dir, year, month)
        os.makedirs(report_dir, exist_ok=True)

        left_table = self._extract_table_name(left_name)
        right_table = self._extract_table_name(right_name)

        filename = f"{left_table}_{right_table}_diff_report_{timestamp}.html"
        filepath = os.path.join(report_dir, filename)

        html_content = self._generate_html(comparison_result, left_name, right_name, timestamp)

        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(html_content)

        logger.info(f"报告已生成: {filepath}")
        return filepath

    def _extract_table_name(self, name: str) -> str:
        if '.' in name:
            parts = name.split('.')
            if len(parts) >= 2:
                return parts[-1]
        
        if ':' in name:
            parts = name.split(':')
            if len(parts) >= 2:
                return parts[-1]
        
        safe_name = name.replace('/', '_').replace('\\', '_').replace(' ', '_')
        safe_name = ''.join(c for c in safe_name if c.isalnum() or c in ['_', '-'])
        
        return safe_name if safe_name else 'table'

    def _generate_html(self, result: Dict[str, Any], left_name: str, right_name: str, timestamp: str) -> str:
        html = f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>数据库对比报告 - {timestamp}</title>
    <style>
        {self._get_styles()}
    </style>
</head>
<body>
    <div class="container">
        <header class="header">
            <h1>📊 数据库对比报告</h1>
            <div class="meta-info">
                <p><strong>生成时间:</strong> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
                <p><strong>左表:</strong> {left_name}</p>
                <p><strong>右表:</strong> {right_name}</p>
            </div>
        </header>

        <section class="overview">
            <h2>📈 对比概览</h2>
            {self._generate_overview(result)}
        </section>

        <section class="structure-diff">
            <h2>🏗️ 结构差异</h2>
            {self._generate_structure_diff(result.get('structure', {}))}
        </section>

        <section class="data-diff">
            <h2>📋 数据差异</h2>
            {self._generate_data_diff(result.get('data', {}))}
        </section>
    </div>
</body>
</html>'''
        return html

    def _get_styles(self) -> str:
        return '''
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }

        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'PingFang SC', 'Hiragino Sans GB', 'Microsoft YaHei', sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
            color: #333;
        }

        .container {
            max-width: 1400px;
            margin: 0 auto;
            background: rgba(255, 255, 255, 0.98);
            border-radius: 20px;
            box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
            overflow: hidden;
        }

        .header {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 40px;
            text-align: center;
        }

        .header h1 {
            font-size: 2.5rem;
            margin-bottom: 20px;
        }

        .meta-info {
            background: rgba(255, 255, 255, 0.2);
            padding: 20px;
            border-radius: 10px;
            display: inline-block;
        }

        .meta-info p {
            margin: 5px 0;
            font-size: 1rem;
        }

        section {
            padding: 30px 40px;
            border-bottom: 1px solid #e9ecef;
        }

        section:last-child {
            border-bottom: none;
        }

        h2 {
            font-size: 1.8rem;
            margin-bottom: 20px;
            color: #667eea;
            display: flex;
            align-items: center;
            gap: 10px;
        }

        .stats-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin: 20px 0;
        }

        .stat-card {
            background: linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%);
            padding: 20px;
            border-radius: 15px;
            text-align: center;
            border: 2px solid #dee2e6;
        }

        .stat-card h3 {
            font-size: 2rem;
            color: #667eea;
            margin-bottom: 10px;
        }

        .stat-card p {
            color: #666;
            font-size: 0.9rem;
        }

        .diff-section {
            margin: 20px 0;
        }

        .diff-section h3 {
            font-size: 1.3rem;
            margin-bottom: 15px;
            padding: 10px 15px;
            background: #f8f9fa;
            border-radius: 10px;
            border-left: 4px solid #667eea;
        }

        .table-container {
            overflow-x: auto;
            margin: 15px 0;
            border-radius: 10px;
            border: 2px solid #dee2e6;
        }

        table {
            width: 100%;
            border-collapse: collapse;
            font-size: 0.9rem;
        }

        th {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 12px;
            text-align: left;
            font-weight: 600;
        }

        td {
            padding: 10px 12px;
            border-bottom: 1px solid #e9ecef;
        }

        tr:hover {
            background: #f8f9ff;
        }

        .badge {
            display: inline-block;
            padding: 4px 12px;
            border-radius: 20px;
            font-size: 0.85rem;
            font-weight: 600;
        }

        .badge-common {
            background: #d4edda;
            color: #155724;
        }

        .badge-diff {
            background: #f8d7da;
            color: #721c24;
        }

        .badge-left {
            background: #cce5ff;
            color: #004085;
        }

        .badge-right {
            background: #fff3cd;
            color: #856404;
        }

        .diff-value {
            display: inline-block;
            padding: 4px 8px;
            border-radius: 5px;
            font-family: 'Monaco', 'Menlo', monospace;
            font-size: 0.85rem;
        }

        .diff-left {
            background: #ffebee;
            color: #c62828;
        }

        .diff-right {
            background: #e8f5e9;
            color: #2e7d32;
        }

        .summary-box {
            background: #fff3cd;
            border: 2px solid #ffc107;
            border-radius: 10px;
            padding: 20px;
            margin: 20px 0;
        }

        .summary-box h4 {
            color: #856404;
            margin-bottom: 10px;
        }

        .key-list {
            display: flex;
            flex-wrap: wrap;
            gap: 8px;
            margin-top: 10px;
        }

        .key-item {
            background: white;
            padding: 6px 12px;
            border-radius: 5px;
            font-family: monospace;
            font-size: 0.85rem;
            border: 1px solid #dee2e6;
        }

        .empty-message {
            text-align: center;
            padding: 40px;
            color: #999;
            font-size: 1.1rem;
        }

        @media (max-width: 768px) {
            .header h1 {
                font-size: 1.8rem;
            }

            section {
                padding: 20px;
            }

            h2 {
                font-size: 1.4rem;
            }
        }
        '''

    def _generate_overview(self, result: Dict[str, Any]) -> str:
        structure_stats = result.get('structure', {}).get('fields', {}).get('stats', {})
        data_stats = result.get('data', {}).get('stats', {})

        html = f'''
        <div class="stats-grid">
            <div class="stat-card">
                <h3>{structure_stats.get('total', 0)}</h3>
                <p>总字段数</p>
            </div>
            <div class="stat-card">
                <h3>{structure_stats.get('common', 0)}</h3>
                <p>共有字段</p>
            </div>
            <div class="stat-card">
                <h3>{structure_stats.get('different', 0)}</h3>
                <p>差异字段</p>
            </div>
            <div class="stat-card">
                <h3>{data_stats.get('left_count', 0)}</h3>
                <p>左表总数据量</p>
            </div>
            <div class="stat-card">
                <h3>{data_stats.get('right_count', 0)}</h3>
                <p>右表总数据量</p>
            </div>
            <div class="stat-card">
                <h3>{data_stats.get('common', 0)}</h3>
                <p>相同数据</p>
            </div>
            <div class="stat-card">
                <h3>{data_stats.get('left_only', 0)}</h3>
                <p>左表独有</p>
            </div>
            <div class="stat-card">
                <h3>{data_stats.get('right_only', 0)}</h3>
                <p>右表独有</p>
            </div>
            <div class="stat-card">
                <h3>{data_stats.get('different', 0)}</h3>
                <p>差异数据</p>
            </div>
        </div>
        '''
        return html

    def _generate_different_data_scrollable(self, different: List[Dict], primary_keys: List[str]) -> str:
        html = f'''
        <div class="diff-section">
            <h3>❌ 差异数据 ({len(different)} 条)</h3>
            <div class="scrollable-container" style="max-height: 500px; overflow-y: auto; border: 2px solid #f8d7da; border-radius: 10px; padding: 15px; background: #fff5f5;">
        '''

        for item in different:
            key = item.get('key', ())
            if isinstance(key, tuple):
                key_str = ', '.join(str(k) for k in key)
            else:
                key_str = str(key)

            html += f'''
                <div class="diff-item" style="margin-bottom: 20px; padding: 15px; background: white; border-radius: 8px; border-left: 4px solid #dc3545;">
                    <div style="font-weight: 600; color: #721c24; margin-bottom: 10px; padding: 8px; background: #f8d7da; border-radius: 5px;">
                        🔑 主键: {key_str}
                    </div>
                    <table style="width: 100%; border-collapse: collapse;">
                        <thead>
                            <tr style="background: #f8f9fa;">
                                <th style="padding: 8px; text-align: left; border-bottom: 2px solid #dee2e6;">字段</th>
                                <th style="padding: 8px; text-align: left; border-bottom: 2px solid #dee2e6;">左表值</th>
                                <th style="padding: 8px; text-align: left; border-bottom: 2px solid #dee2e6;">右表值</th>
                            </tr>
                        </thead>
                        <tbody>
            '''

            for field, (left_val, right_val) in item['differences'].items():
                html += f'''
                            <tr>
                                <td style="padding: 8px; border-bottom: 1px solid #e9ecef;"><strong>{field}</strong></td>
                                <td style="padding: 8px; border-bottom: 1px solid #e9ecef;"><span style="background: #ffebee; color: #c62828; padding: 4px 8px; border-radius: 4px; font-family: monospace;">{left_val if left_val is not None else 'NULL'}</span></td>
                                <td style="padding: 8px; border-bottom: 1px solid #e9ecef;"><span style="background: #e8f5e9; color: #2e7d32; padding: 4px 8px; border-radius: 4px; font-family: monospace;">{right_val if right_val is not None else 'NULL'}</span></td>
                            </tr>
                '''

            html += '''
                        </tbody>
                    </table>
                </div>
            '''

        html += '''
            </div>
        </div>
        '''
        return html

    def _generate_common_data_with_ranges(self, title: str, common: List[Dict], primary_keys: List[str]) -> str:
        if not common:
            return ''

        keys = []
        for item in common:
            key = item.get('key', ())
            if isinstance(key, tuple) and len(key) == 1:
                keys.append(key[0])
            elif isinstance(key, (int, str)):
                keys.append(key)

        if not keys:
            return self._generate_data_summary(title, common, 'common', primary_keys)

        try:
            numeric_keys = [int(k) for k in keys if str(k).isdigit()]
            if len(numeric_keys) == len(keys):
                keys = sorted(numeric_keys)
                ranges = self._generate_id_ranges(keys)
                
                html = f'''
                <div class="diff-section">
                    <h3>{title} ({len(common)} 条)</h3>
                    <div class="summary-box" style="background: #d4edda; border-color: #28a745;">
                        <h4 style="color: #155724;">ID 范围汇总</h4>
                        <div style="background: white; padding: 15px; border-radius: 8px; font-family: monospace; font-size: 0.9rem; line-height: 1.8;">
                            {ranges}
                        </div>
                    </div>
                </div>
                '''
                return html
        except (ValueError, TypeError):
            pass

        return self._generate_data_summary(title, common, 'common', primary_keys)

    def _generate_id_ranges(self, ids: List[int]) -> str:
        if not ids:
            return ''

        ranges = []
        start = ids[0]
        end = ids[0]

        for i in range(1, len(ids)):
            if ids[i] == end + 1:
                end = ids[i]
            else:
                if start == end:
                    ranges.append(str(start))
                else:
                    ranges.append(f"{start}-{end}")
                start = ids[i]
                end = ids[i]

        if start == end:
            ranges.append(str(start))
        else:
            ranges.append(f"{start}-{end}")

        return ', '.join(ranges)

    def _generate_structure_diff(self, structure: Dict[str, Any]) -> str:
        if not structure:
            return '<div class="empty-message">无结构对比数据</div>'

        fields = structure.get('fields', {})
        indexes = structure.get('indexes', {})

        html = ''

        html += self._generate_fields_diff(fields)
        html += self._generate_indexes_diff(indexes)

        return html

    def _generate_fields_diff(self, fields: Dict[str, Any]) -> str:
        html = '<div class="diff-section"><h3>字段对比</h3>'

        common = fields.get('common', [])
        left_only = fields.get('left_only', [])
        right_only = fields.get('right_only', [])
        different = fields.get('different', [])

        if common:
            html += f'''
            <div class="table-container">
                <p style="padding: 10px; background: #d4edda; color: #155724; font-weight: 600;">
                    ✅ 共有字段 ({len(common)} 个)
                </p>
                <table>
                    <thead>
                        <tr>
                            <th>字段名</th>
                            <th>类型</th>
                            <th>允许空</th>
                            <th>键</th>
                            <th>默认值</th>
                            <th>额外</th>
                        </tr>
                    </thead>
                    <tbody>
            '''
            for field in common:
                defn = field.get('definition', field)
                field_name = field.get('field', field.get('Field', ''))
                html += f'''
                        <tr>
                            <td><strong>{field_name}</strong></td>
                            <td>{defn.get('Type', '')}</td>
                            <td>{defn.get('Null', '')}</td>
                            <td>{defn.get('Key', '')}</td>
                            <td>{defn.get('Default', '')}</td>
                            <td>{defn.get('Extra', '')}</td>
                        </tr>
                '''
            html += '</tbody></table></div>'

        if left_only:
            html += f'''
            <div class="table-container">
                <p style="padding: 10px; background: #cce5ff; color: #004085; font-weight: 600;">
                    🔵 左表独有字段 ({len(left_only)} 个)
                </p>
                <table>
                    <thead>
                        <tr>
                            <th>字段名</th>
                            <th>类型</th>
                            <th>允许空</th>
                            <th>键</th>
                            <th>默认值</th>
                            <th>额外</th>
                        </tr>
                    </thead>
                    <tbody>
            '''
            for field in left_only:
                defn = field.get('definition', field)
                field_name = field.get('field', field.get('Field', ''))
                html += f'''
                        <tr>
                            <td><strong>{field_name}</strong></td>
                            <td>{defn.get('Type', '')}</td>
                            <td>{defn.get('Null', '')}</td>
                            <td>{defn.get('Key', '')}</td>
                            <td>{defn.get('Default', '')}</td>
                            <td>{defn.get('Extra', '')}</td>
                        </tr>
                '''
            html += '</tbody></table></div>'

        if right_only:
            html += f'''
            <div class="table-container">
                <p style="padding: 10px; background: #fff3cd; color: #856404; font-weight: 600;">
                    🟡 右表独有字段 ({len(right_only)} 个)
                </p>
                <table>
                    <thead>
                        <tr>
                            <th>字段名</th>
                            <th>类型</th>
                            <th>允许空</th>
                            <th>键</th>
                            <th>默认值</th>
                            <th>额外</th>
                        </tr>
                    </thead>
                    <tbody>
            '''
            for field in right_only:
                defn = field.get('definition', field)
                field_name = field.get('field', field.get('Field', ''))
                html += f'''
                        <tr>
                            <td><strong>{field_name}</strong></td>
                            <td>{defn.get('Type', '')}</td>
                            <td>{defn.get('Null', '')}</td>
                            <td>{defn.get('Key', '')}</td>
                            <td>{defn.get('Default', '')}</td>
                            <td>{defn.get('Extra', '')}</td>
                        </tr>
                '''
            html += '</tbody></table></div>'

        if different:
            html += f'''
            <div class="table-container">
                <p style="padding: 10px; background: #f8d7da; color: #721c24; font-weight: 600;">
                    ❌ 差异字段 ({len(different)} 个)
                </p>
                <table>
                    <thead>
                        <tr>
                            <th>字段名</th>
                            <th>差异项</th>
                            <th>左表值</th>
                            <th>右表值</th>
                        </tr>
                    </thead>
                    <tbody>
            '''
            for field in different:
                for diff_key, (left_val, right_val) in field['differences'].items():
                    html += f'''
                        <tr>
                            <td><strong>{field['field']}</strong></td>
                            <td>{diff_key}</td>
                            <td><span class="diff-value diff-left">{left_val}</span></td>
                            <td><span class="diff-value diff-right">{right_val}</span></td>
                        </tr>
                    '''
            html += '</tbody></table></div>'

        html += '</div>'
        return html

    def _generate_indexes_diff(self, indexes: Dict[str, Any]) -> str:
        html = '<div class="diff-section"><h3>索引对比</h3>'

        common = indexes.get('common', [])
        left_only = indexes.get('left_only', [])
        right_only = indexes.get('right_only', [])
        different = indexes.get('different', [])

        if common:
            html += f'''
            <div class="table-container">
                <p style="padding: 10px; background: #d4edda; color: #155724; font-weight: 600;">
                    ✅ 共有索引 ({len(common)} 个)
                </p>
                <table>
                    <thead>
                        <tr>
                            <th>索引名</th>
                            <th>列</th>
                            <th>唯一性</th>
                            <th>类型</th>
                        </tr>
                    </thead>
                    <tbody>
            '''
            for idx in common:
                columns = ', '.join([c['column'] for c in idx['columns']])
                unique = '是' if idx['non_unique'] == 0 else '否'
                html += f'''
                        <tr>
                            <td><strong>{idx['name']}</strong></td>
                            <td>{columns}</td>
                            <td>{unique}</td>
                            <td>{idx['index_type']}</td>
                        </tr>
                '''
            html += '</tbody></table></div>'

        if left_only:
            html += f'''
            <div class="table-container">
                <p style="padding: 10px; background: #cce5ff; color: #004085; font-weight: 600;">
                    🔵 左表独有索引 ({len(left_only)} 个)
                </p>
                <table>
                    <thead>
                        <tr>
                            <th>索引名</th>
                            <th>列</th>
                            <th>唯一性</th>
                            <th>类型</th>
                        </tr>
                    </thead>
                    <tbody>
            '''
            for idx in left_only:
                columns = ', '.join([c['column'] for c in idx['columns']])
                unique = '是' if idx['non_unique'] == 0 else '否'
                html += f'''
                        <tr>
                            <td><strong>{idx['name']}</strong></td>
                            <td>{columns}</td>
                            <td>{unique}</td>
                            <td>{idx['index_type']}</td>
                        </tr>
                '''
            html += '</tbody></table></div>'

        if right_only:
            html += f'''
            <div class="table-container">
                <p style="padding: 10px; background: #fff3cd; color: #856404; font-weight: 600;">
                    🟡 右表独有索引 ({len(right_only)} 个)
                </p>
                <table>
                    <thead>
                        <tr>
                            <th>索引名</th>
                            <th>列</th>
                            <th>唯一性</th>
                            <th>类型</th>
                        </tr>
                    </thead>
                    <tbody>
            '''
            for idx in right_only:
                columns = ', '.join([c['column'] for c in idx['columns']])
                unique = '是' if idx['non_unique'] == 0 else '否'
                html += f'''
                        <tr>
                            <td><strong>{idx['name']}</strong></td>
                            <td>{columns}</td>
                            <td>{unique}</td>
                            <td>{idx['index_type']}</td>
                        </tr>
                '''
            html += '</tbody></table></div>'

        if different:
            html += f'''
            <div class="table-container">
                <p style="padding: 10px; background: #f8d7da; color: #721c24; font-weight: 600;">
                    ❌ 差异索引 ({len(different)} 个)
                </p>
                <table>
                    <thead>
                        <tr>
                            <th>索引名</th>
                            <th>左表</th>
                            <th>右表</th>
                        </tr>
                    </thead>
                    <tbody>
            '''
            for idx in different:
                left_cols = ', '.join([c['column'] for c in idx['left']['columns']])
                right_cols = ', '.join([c['column'] for c in idx['right']['columns']])
                html += f'''
                        <tr>
                            <td><strong>{idx['name']}</strong></td>
                            <td><span class="diff-value diff-left">{left_cols}</span></td>
                            <td><span class="diff-value diff-right">{right_cols}</span></td>
                        </tr>
                '''
            html += '</tbody></table></div>'

        html += '</div>'
        return html

    def _generate_data_diff(self, data: Dict[str, Any]) -> str:
        if not data:
            return '<div class="empty-message">无数据对比结果</div>'

        html = ''

        common = data.get('common', [])
        different = data.get('different', [])
        left_only = data.get('left_only', [])
        right_only = data.get('right_only', [])
        primary_keys = data.get('primary_keys', [])

        if common:
            html += self._generate_common_data_with_ranges(
                '✅ 相同数据',
                common,
                primary_keys
            )

        if left_only:
            if len(left_only) <= self.max_display_rows:
                html += self._generate_data_table(
                    '🔵 左表独有数据',
                    left_only,
                    'left',
                    primary_keys
                )
            else:
                html += self._generate_data_summary(
                    '🔵 左表独有数据',
                    left_only,
                    'left',
                    primary_keys
                )

        if right_only:
            if len(right_only) <= self.max_display_rows:
                html += self._generate_data_table(
                    '� 右表独有数据',
                    right_only,
                    'right',
                    primary_keys
                )
            else:
                html += self._generate_data_summary(
                    '� 右表独有数据',
                    right_only,
                    'right',
                    primary_keys
                )

        if different:
            html += self._generate_different_data_scrollable(different, primary_keys)

        return html

    def _generate_data_table(self, title: str, data: List[Dict], data_type: str, primary_keys: List[str]) -> str:
        if not data:
            return ''

        bg_colors = {
            'common': '#d4edda',
            'left': '#cce5ff',
            'right': '#fff3cd'
        }
        text_colors = {
            'common': '#155724',
            'left': '#004085',
            'right': '#856404'
        }

        html = f'''
        <div class="diff-section">
            <h3>{title} ({len(data)} 条)</h3>
            <div class="table-container">
                <p style="padding: 10px; background: {bg_colors[data_type]}; color: {text_colors[data_type]}; font-weight: 600;">
                    {title} ({len(data)} 条)
                </p>
                <table>
                    <thead>
                        <tr>
        '''

        if data:
            sample = data[0].get('data', data[0])
            for key in sample.keys():
                html += f'<th>{key}</th>'

        html += '''
                        </tr>
                    </thead>
                    <tbody>
        '''

        for item in data:
            row_data = item.get('data', item)
            html += '<tr>'
            for key, value in row_data.items():
                html += f'<td>{value if value is not None else "NULL"}</td>'
            html += '</tr>'

        html += '''
                    </tbody>
                </table>
            </div>
        </div>
        '''
        return html

    def _generate_data_summary(self, title: str, data: List[Dict], data_type: str, primary_keys: List[str]) -> str:
        bg_colors = {
            'common': '#fff3cd',
            'left': '#cce5ff',
            'right': '#fff3cd'
        }
        text_colors = {
            'common': '#856404',
            'left': '#004085',
            'right': '#856404'
        }

        html = f'''
        <div class="diff-section">
            <h3>{title} (汇总)</h3>
            <div class="summary-box">
                <h4>数据量过大 (共 {len(data)} 条)，仅显示主键汇总</h4>
                <div class="key-list">
        '''

        for item in data[:100]:
            key = item.get('key', ())
            if isinstance(key, tuple):
                key_str = ', '.join(str(k) for k in key)
            else:
                key_str = str(key)
            html += f'<span class="key-item">{key_str}</span>'

        if len(data) > 100:
            html += f'<span class="key-item">... 还有 {len(data) - 100} 条</span>'

        html += '''
                </div>
            </div>
        </div>
        '''
        return html

    def _generate_different_data_table(self, different: List[Dict], primary_keys: List[str]) -> str:
        html = f'''
        <div class="diff-section">
            <h3>❌ 差异数据 ({len(different)} 条)</h3>
        '''

        for item in different:
            key = item.get('key', ())
            if isinstance(key, tuple):
                key_str = ', '.join(str(k) for k in key)
            else:
                key_str = str(key)

            html += f'''
            <div class="table-container" style="margin: 20px 0;">
                <p style="padding: 10px; background: #f8d7da; color: #721c24; font-weight: 600;">
                    主键: {key_str}
                </p>
                <table>
                    <thead>
                        <tr>
                            <th>字段</th>
                            <th>左表值</th>
                            <th>右表值</th>
                        </tr>
                    </thead>
                    <tbody>
            '''

            for field, (left_val, right_val) in item['differences'].items():
                html += f'''
                        <tr>
                            <td><strong>{field}</strong></td>
                            <td><span class="diff-value diff-left">{left_val if left_val is not None else 'NULL'}</span></td>
                            <td><span class="diff-value diff-right">{right_val if right_val is not None else 'NULL'}</span></td>
                        </tr>
                '''

            html += '''
                    </tbody>
                </table>
            </div>
            '''

        html += '</div>'
        return html

    def _generate_different_data_summary(self, different: List[Dict], primary_keys: List[str]) -> str:
        html = f'''
        <div class="diff-section">
            <h3>❌ 差异数据 (汇总)</h3>
            <div class="summary-box">
                <h4>差异数据量过大 (共 {len(different)} 条)，仅显示主键汇总</h4>
                <div class="key-list">
        '''

        for item in different[:100]:
            key = item.get('key', ())
            if isinstance(key, tuple):
                key_str = ', '.join(str(k) for k in key)
            else:
                key_str = str(key)
            html += f'<span class="key-item">{key_str}</span>'

        if len(different) > 100:
            html += f'<span class="key-item">... 还有 {len(different) - 100} 条</span>'

        html += '''
                </div>
            </div>
        </div>
        '''
        return html
