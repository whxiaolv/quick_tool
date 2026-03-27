import os
import re
import csv
import json
from typing import Dict, List, Any, Tuple
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class FileParser:
    @staticmethod
    def parse_sql_file(file_path: str) -> Dict[str, Any]:
        logger.info(f"开始解析 SQL 文件: {file_path}")

        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        result = {
            'tables': {},
            'parse_errors': []
        }

        table_pattern = r'CREATE\s+TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?`?(\w+)`?\s*\((.*?)\)(?:\s*ENGINE.*?)?;'
        matches = re.finditer(table_pattern, content, re.IGNORECASE | re.DOTALL)

        for match in matches:
            table_name = match.group(1)
            table_body = match.group(2)

            try:
                fields, indexes = FileParser._parse_table_body(table_body)
                result['tables'][table_name] = {
                    'fields': fields,
                    'indexes': indexes,
                    'create_statement': match.group(0)
                }
                logger.info(f"成功解析表: {table_name}")
            except Exception as e:
                error_msg = f"解析表 {table_name} 失败: {str(e)}"
                logger.error(error_msg)
                result['parse_errors'].append(error_msg)

        insert_pattern = r'INSERT\s+INTO\s+`?(\w+)`?\s*(?:\([^)]+\))?\s*VALUES\s*\((.*?)\);'
        insert_matches = re.finditer(insert_pattern, content, re.IGNORECASE | re.DOTALL)

        for match in insert_matches:
            table_name = match.group(1)
            values_str = match.group(2)

            if table_name not in result['tables']:
                result['tables'][table_name] = {
                    'fields': [],
                    'indexes': [],
                    'data': []
                }

            if 'data' not in result['tables'][table_name]:
                result['tables'][table_name]['data'] = []

            try:
                values = FileParser._parse_insert_values(values_str)
                fields = result['tables'][table_name].get('fields', [])
                if fields and len(values) == len(fields):
                    data_dict = {}
                    for i, field in enumerate(fields):
                        data_dict[field['Field']] = values[i]
                    result['tables'][table_name]['data'].append(data_dict)
                else:
                    result['tables'][table_name]['data'].append(values)
            except Exception as e:
                error_msg = f"解析 INSERT 语句失败 (表 {table_name}): {str(e)}"
                logger.warning(error_msg)

        logger.info(f"SQL 文件解析完成，共解析 {len(result['tables'])} 个表")
        return result

    @staticmethod
    def _parse_table_body(table_body: str) -> Tuple[List[Dict], List[Dict]]:
        lines = [line.strip() for line in table_body.split('\n') if line.strip()]

        fields = []
        indexes = []

        for line in lines:
            line = line.rstrip(',')

            if line.upper().startswith('PRIMARY KEY'):
                match = re.search(r'PRIMARY\s+KEY\s*\((.*?)\)', line, re.IGNORECASE)
                if match:
                    columns = [col.strip('` ') for col in match.group(1).split(',')]
                    indexes.append({
                        'name': 'PRIMARY',
                        'columns': [{'column': col, 'seq': i+1} for i, col in enumerate(columns)],
                        'non_unique': 0,
                        'index_type': 'BTREE'
                    })

            elif line.upper().startswith('KEY') or line.upper().startswith('INDEX'):
                match = re.search(r'(?:KEY|INDEX)\s+`?(\w+)`?\s*\((.*?)\)', line, re.IGNORECASE)
                if match:
                    index_name = match.group(1)
                    columns = [col.strip('` ') for col in match.group(2).split(',')]
                    indexes.append({
                        'name': index_name,
                        'columns': [{'column': col, 'seq': i+1} for i, col in enumerate(columns)],
                        'non_unique': 1,
                        'index_type': 'BTREE'
                    })

            elif line.upper().startswith('UNIQUE'):
                match = re.search(r'UNIQUE\s+(?:KEY|INDEX)\s+`?(\w+)`?\s*\((.*?)\)', line, re.IGNORECASE)
                if match:
                    index_name = match.group(1)
                    columns = [col.strip('` ') for col in match.group(2).split(',')]
                    indexes.append({
                        'name': index_name,
                        'columns': [{'column': col, 'seq': i+1} for i, col in enumerate(columns)],
                        'non_unique': 0,
                        'index_type': 'BTREE'
                    })

            elif not line.upper().startswith(('CONSTRAINT', 'FOREIGN', 'CHECK')):
                field_match = re.match(r'`?(\w+)`?\s+(\w+(?:\([^)]+\))?)(.*)', line)
                if field_match:
                    field_name = field_match.group(1)
                    field_type = field_match.group(2)
                    field_attrs = field_match.group(3)

                    field = {
                        'Field': field_name,
                        'Type': field_type,
                        'Null': 'YES',
                        'Key': '',
                        'Default': None,
                        'Extra': ''
                    }

                    if 'NOT NULL' in field_attrs.upper():
                        field['Null'] = 'NO'

                    if 'PRIMARY KEY' in field_attrs.upper():
                        field['Key'] = 'PRI'

                    if 'AUTO_INCREMENT' in field_attrs.upper():
                        field['Extra'] = 'auto_increment'

                    default_match = re.search(r'DEFAULT\s+([^\s,]+)', field_attrs, re.IGNORECASE)
                    if default_match:
                        default_val = default_match.group(1)
                        if default_val.upper() != 'NULL':
                            field['Default'] = default_val.strip("'\"")

                    fields.append(field)

        return fields, indexes

    @staticmethod
    def _parse_insert_values(values_str: str) -> List[Any]:
        values = []
        current = ''
        in_quotes = False
        quote_char = None
        escaped = False

        for char in values_str:
            if escaped:
                current += char
                escaped = False
            elif char == '\\':
                escaped = True
                current += char
            elif char in ('"', "'") and not in_quotes:
                in_quotes = True
                quote_char = char
                current += char
            elif char == quote_char and in_quotes:
                in_quotes = False
                quote_char = None
                current += char
            elif char == ',' and not in_quotes:
                values.append(current.strip())
                current = ''
            else:
                current += char

        if current.strip():
            values.append(current.strip())

        return values

    @staticmethod
    def parse_csv_file(file_path: str) -> Dict[str, Any]:
        logger.info(f"开始解析 CSV 文件: {file_path}")

        result = {
            'fields': [],
            'data': [],
            'parse_errors': []
        }

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                reader = csv.reader(f)

                headers = next(reader)
                result['fields'] = [
                    {
                        'Field': header,
                        'Type': 'VARCHAR(255)',
                        'Null': 'YES',
                        'Key': '',
                        'Default': None,
                        'Extra': ''
                    }
                    for header in headers
                ]

                for row in reader:
                    data_dict = {}
                    for i, header in enumerate(headers):
                        value = row[i] if i < len(row) else None
                        data_dict[header] = value
                    result['data'].append(data_dict)

            logger.info(f"CSV 文件解析完成，共 {len(result['data'])} 行数据")
            return result

        except Exception as e:
            error_msg = f"解析 CSV 文件失败: {str(e)}"
            logger.error(error_msg)
            result['parse_errors'].append(error_msg)
            return result

    @staticmethod
    def parse_json_file(file_path: str) -> Dict[str, Any]:
        logger.info(f"开始解析 JSON 文件: {file_path}")

        result = {
            'fields': [],
            'data': [],
            'parse_errors': []
        }

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            if isinstance(data, list) and len(data) > 0:
                first_item = data[0]
                if isinstance(first_item, dict):
                    result['fields'] = [
                        {
                            'Field': key,
                            'Type': 'VARCHAR(255)',
                            'Null': 'YES',
                            'Key': '',
                            'Default': None,
                            'Extra': ''
                        }
                        for key in first_item.keys()
                    ]

                    result['data'] = data

            logger.info(f"JSON 文件解析完成，共 {len(result['data'])} 行数据")
            return result

        except Exception as e:
            error_msg = f"解析 JSON 文件失败: {str(e)}"
            logger.error(error_msg)
            result['parse_errors'].append(error_msg)
            return result

    @staticmethod
    def detect_file_type(file_path: str) -> str:
        ext = os.path.splitext(file_path)[1].lower()

        if ext == '.sql':
            return 'sql'
        elif ext == '.csv':
            return 'csv'
        elif ext == '.json':
            return 'json'
        else:
            raise ValueError(f"不支持的文件类型: {ext}")

    @staticmethod
    def parse_file(file_path: str) -> Dict[str, Any]:
        file_type = FileParser.detect_file_type(file_path)

        if file_type == 'sql':
            return FileParser.parse_sql_file(file_path)
        elif file_type == 'csv':
            parsed = FileParser.parse_csv_file(file_path)
            return {
                'tables': {
                    os.path.basename(file_path).replace('.csv', ''): parsed
                }
            }
        elif file_type == 'json':
            parsed = FileParser.parse_json_file(file_path)
            return {
                'tables': {
                    os.path.basename(file_path).replace('.json', ''): parsed
                }
            }
