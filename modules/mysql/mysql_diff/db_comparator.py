from typing import Dict, List, Any, Tuple, Optional
from db_connector import DatabaseConnector
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class DatabaseComparator:
    def __init__(self, left_connector: DatabaseConnector, right_connector: DatabaseConnector):
        self.left = left_connector
        self.right = right_connector

    def compare_structure(self, left_table: str, right_table: str) -> Dict[str, Any]:
        logger.info(f"开始对比表结构: {left_table} vs {right_table}")

        left_structure = self.left.get_table_structure(left_table)
        right_structure = self.right.get_table_structure(right_table)

        left_indexes = self.left.get_table_indexes(left_table)
        right_indexes = self.right.get_table_indexes(right_table)

        field_comparison = self._compare_fields(
            left_structure['fields'],
            right_structure['fields']
        )

        index_comparison = self._compare_indexes(left_indexes, right_indexes)

        return {
            'left_table': left_table,
            'right_table': right_table,
            'fields': field_comparison,
            'indexes': index_comparison
        }

    def _compare_fields(self, left_fields: List[Dict], right_fields: List[Dict]) -> Dict[str, Any]:
        left_field_dict = {f['Field']: f for f in left_fields}
        right_field_dict = {f['Field']: f for f in right_fields}

        all_field_names = set(left_field_dict.keys()) | set(right_field_dict.keys())

        common_fields = []
        left_only_fields = []
        right_only_fields = []
        different_fields = []

        for field_name in sorted(all_field_names):
            if field_name in left_field_dict and field_name in right_field_dict:
                left_field = left_field_dict[field_name]
                right_field = right_field_dict[field_name]

                differences = self._get_field_differences(left_field, right_field)

                if differences:
                    different_fields.append({
                        'field': field_name,
                        'left': left_field,
                        'right': right_field,
                        'differences': differences
                    })
                else:
                    common_fields.append({
                        'field': field_name,
                        'definition': left_field
                    })

            elif field_name in left_field_dict:
                left_only_fields.append({
                    'field': field_name,
                    'definition': left_field_dict[field_name]
                })
            else:
                right_only_fields.append({
                    'field': field_name,
                    'definition': right_field_dict[field_name]
                })

        return {
            'common': common_fields,
            'left_only': left_only_fields,
            'right_only': right_only_fields,
            'different': different_fields,
            'stats': {
                'total': len(all_field_names),
                'common': len(common_fields),
                'left_only': len(left_only_fields),
                'right_only': len(right_only_fields),
                'different': len(different_fields)
            }
        }

    def _get_field_differences(self, left_field: Dict, right_field: Dict) -> Dict[str, Tuple]:
        differences = {}
        compare_keys = ['Type', 'Null', 'Key', 'Default', 'Extra']

        for key in compare_keys:
            left_val = left_field.get(key)
            right_val = right_field.get(key)

            if left_val != right_val:
                differences[key] = (left_val, right_val)

        return differences

    def _compare_indexes(self, left_indexes: List[Dict], right_indexes: List[Dict]) -> Dict[str, Any]:
        left_index_dict = {idx['name']: idx for idx in left_indexes}
        right_index_dict = {idx['name']: idx for idx in right_indexes}

        all_index_names = set(left_index_dict.keys()) | set(right_index_dict.keys())

        common_indexes = []
        left_only_indexes = []
        right_only_indexes = []
        different_indexes = []

        for idx_name in sorted(all_index_names):
            if idx_name in left_index_dict and idx_name in right_index_dict:
                left_idx = left_index_dict[idx_name]
                right_idx = right_index_dict[idx_name]

                if self._indexes_are_equal(left_idx, right_idx):
                    common_indexes.append(left_idx)
                else:
                    different_indexes.append({
                        'name': idx_name,
                        'left': left_idx,
                        'right': right_idx
                    })

            elif idx_name in left_index_dict:
                left_only_indexes.append(left_index_dict[idx_name])
            else:
                right_only_indexes.append(right_index_dict[idx_name])

        return {
            'common': common_indexes,
            'left_only': left_only_indexes,
            'right_only': right_only_indexes,
            'different': different_indexes,
            'stats': {
                'total': len(all_index_names),
                'common': len(common_indexes),
                'left_only': len(left_only_indexes),
                'right_only': len(right_only_indexes),
                'different': len(different_indexes)
            }
        }

    def _indexes_are_equal(self, left_idx: Dict, right_idx: Dict) -> bool:
        if left_idx['non_unique'] != right_idx['non_unique']:
            return False

        if left_idx['index_type'] != right_idx['index_type']:
            return False

        left_columns = [(c['column'], c['seq']) for c in left_idx['columns']]
        right_columns = [(c['column'], c['seq']) for c in right_idx['columns']]

        return left_columns == right_columns

    def compare_data(self, left_table: str, right_table: str, batch_size: int = 1000) -> Dict[str, Any]:
        logger.info(f"开始对比表数据: {left_table} vs {right_table}")

        left_primary_keys = self.left.get_primary_key(left_table)
        right_primary_keys = self.right.get_primary_key(right_table)

        if left_primary_keys != right_primary_keys:
            logger.warning(f"主键不一致: 左表 {left_primary_keys}, 右表 {right_primary_keys}")

        primary_keys = left_primary_keys if left_primary_keys else right_primary_keys

        if not primary_keys:
            logger.warning("未找到主键，将使用所有字段进行对比")
            left_structure = self.left.get_table_structure(left_table)
            primary_keys = [f['Field'] for f in left_structure['fields']]

        left_count = self.left.get_table_count(left_table)
        right_count = self.right.get_table_count(right_table)

        logger.info(f"左表数据量: {left_count}, 右表数据量: {right_count}")

        left_data_map = {}
        offset = 0
        while offset < left_count:
            batch = self.left.get_table_data(left_table, limit=batch_size, offset=offset)
            for row in batch:
                key = tuple(row[pk] for pk in primary_keys)
                left_data_map[key] = row
            offset += batch_size
            logger.info(f"已加载左表数据: {min(offset, left_count)}/{left_count}")

        right_data_map = {}
        offset = 0
        while offset < right_count:
            batch = self.right.get_table_data(right_table, limit=batch_size, offset=offset)
            for row in batch:
                key = tuple(row[pk] for pk in primary_keys)
                right_data_map[key] = row
            offset += batch_size
            logger.info(f"已加载右表数据: {min(offset, right_count)}/{right_count}")

        all_keys = set(left_data_map.keys()) | set(right_data_map.keys())

        common_data = []
        different_data = []
        left_only_data = []
        right_only_data = []

        for key in all_keys:
            if key in left_data_map and key in right_data_map:
                left_row = left_data_map[key]
                right_row = right_data_map[key]

                differences = self._compare_rows(left_row, right_row)

                if differences:
                    different_data.append({
                        'key': key,
                        'left': left_row,
                        'right': right_row,
                        'differences': differences
                    })
                else:
                    common_data.append({
                        'key': key,
                        'data': left_row
                    })

            elif key in left_data_map:
                left_only_data.append({
                    'key': key,
                    'data': left_data_map[key]
                })
            else:
                right_only_data.append({
                    'key': key,
                    'data': right_data_map[key]
                })

        return {
            'left_table': left_table,
            'right_table': right_table,
            'primary_keys': primary_keys,
            'common': common_data,
            'different': different_data,
            'left_only': left_only_data,
            'right_only': right_only_data,
            'stats': {
                'total': len(all_keys),
                'common': len(common_data),
                'different': len(different_data),
                'left_only': len(left_only_data),
                'right_only': len(right_only_data),
                'left_count': left_count,
                'right_count': right_count
            }
        }

    def _compare_rows(self, left_row: Dict, right_row: Dict) -> Dict[str, Tuple]:
        differences = {}

        all_keys = set(left_row.keys()) | set(right_row.keys())

        for key in all_keys:
            left_val = left_row.get(key)
            right_val = right_row.get(key)

            if left_val != right_val:
                differences[key] = (left_val, right_val)

        return differences

    def compare_tables(self, left_table: str, right_table: str) -> Dict[str, Any]:
        logger.info(f"开始完整对比: {left_table} vs {right_table}")

        structure_diff = self.compare_structure(left_table, right_table)

        if structure_diff['fields']['stats']['different'] > 0:
            logger.warning("字段结构存在差异，数据对比结果可能不准确")

        data_diff = self.compare_data(left_table, right_table)

        return {
            'left_table': left_table,
            'right_table': right_table,
            'structure': structure_diff,
            'data': data_diff
        }
