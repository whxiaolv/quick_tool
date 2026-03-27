import pymysql
from pymysql.cursors import DictCursor
from typing import Dict, List, Any, Optional, Tuple
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class DatabaseConnector:
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.connection = None
        self.host = config.get('host', 'localhost')
        self.port = config.get('port', 3306)
        self.database = config.get('database')
        self.user = config.get('user')
        self.password = config.get('password')
        self.charset = config.get('charset', 'utf8mb4')

    def connect(self) -> bool:
        try:
            self.connection = pymysql.connect(
                host=self.host,
                port=self.port,
                database=self.database,
                user=self.user,
                password=self.password,
                charset=self.charset,
                cursorclass=DictCursor,
                connect_timeout=10
            )
            logger.info(f"成功连接到数据库: {self.host}:{self.port}/{self.database}")
            return True
        except Exception as e:
            logger.error(f"数据库连接失败: {str(e)}")
            raise Exception(f"数据库连接失败: {str(e)}")

    def test_connection(self) -> Dict[str, Any]:
        try:
            conn = pymysql.connect(
                host=self.host,
                port=self.port,
                database=self.database,
                user=self.user,
                password=self.password,
                charset=self.charset,
                connect_timeout=5
            )
            conn.close()
            return {
                'success': True,
                'message': f'成功连接到 {self.host}:{self.port}/{self.database}'
            }
        except Exception as e:
            return {
                'success': False,
                'message': str(e)
            }

    def get_tables(self) -> List[str]:
        if not self.connection:
            self.connect()

        try:
            with self.connection.cursor() as cursor:
                cursor.execute("SHOW TABLES")
                tables = [list(row.values())[0] for row in cursor.fetchall()]
                return tables
        except Exception as e:
            logger.error(f"获取表列表失败: {str(e)}")
            raise Exception(f"获取表列表失败: {str(e)}")

    def get_table_structure(self, table_name: str) -> Dict[str, Any]:
        if not self.connection:
            self.connect()

        try:
            with self.connection.cursor() as cursor:
                cursor.execute(f"DESCRIBE `{table_name}`")
                fields = cursor.fetchall()

                cursor.execute(f"SHOW CREATE TABLE `{table_name}`")
                create_table = cursor.fetchone()

                return {
                    'fields': fields,
                    'create_statement': list(create_table.values())[1] if create_table else ''
                }
        except Exception as e:
            logger.error(f"获取表结构失败: {str(e)}")
            raise Exception(f"获取表结构失败: {str(e)}")

    def get_table_indexes(self, table_name: str) -> List[Dict[str, Any]]:
        if not self.connection:
            self.connect()

        try:
            with self.connection.cursor() as cursor:
                cursor.execute(f"SHOW INDEX FROM `{table_name}`")
                indexes = cursor.fetchall()

                index_dict = {}
                for idx in indexes:
                    key_name = idx['Key_name']
                    if key_name not in index_dict:
                        index_dict[key_name] = {
                            'name': key_name,
                            'non_unique': idx['Non_unique'],
                            'columns': [],
                            'index_type': idx['Index_type']
                        }
                    index_dict[key_name]['columns'].append({
                        'column': idx['Column_name'],
                        'seq': idx['Seq_in_index']
                    })

                for idx_name in index_dict:
                    index_dict[idx_name]['columns'].sort(key=lambda x: x['seq'])

                return list(index_dict.values())
        except Exception as e:
            logger.error(f"获取表索引失败: {str(e)}")
            raise Exception(f"获取表索引失败: {str(e)}")

    def get_primary_key(self, table_name: str) -> List[str]:
        if not self.connection:
            self.connect()

        try:
            with self.connection.cursor() as cursor:
                cursor.execute(f"SHOW KEYS FROM `{table_name}` WHERE Key_name = 'PRIMARY'")
                primary_keys = cursor.fetchall()
                return [pk['Column_name'] for pk in primary_keys]
        except Exception as e:
            logger.error(f"获取主键失败: {str(e)}")
            raise Exception(f"获取主键失败: {str(e)}")

    def get_table_data(self, table_name: str, limit: Optional[int] = None, offset: Optional[int] = None) -> List[Dict[str, Any]]:
        if not self.connection:
            self.connect()

        try:
            with self.connection.cursor() as cursor:
                sql = f"SELECT * FROM `{table_name}`"
                if limit:
                    sql += f" LIMIT {limit}"
                    if offset:
                        sql += f" OFFSET {offset}"

                cursor.execute(sql)
                return cursor.fetchall()
        except Exception as e:
            logger.error(f"获取表数据失败: {str(e)}")
            raise Exception(f"获取表数据失败: {str(e)}")

    def get_table_count(self, table_name: str) -> int:
        if not self.connection:
            self.connect()

        try:
            with self.connection.cursor() as cursor:
                cursor.execute(f"SELECT COUNT(*) as count FROM `{table_name}`")
                result = cursor.fetchone()
                return result['count']
        except Exception as e:
            logger.error(f"获取表数据量失败: {str(e)}")
            raise Exception(f"获取表数据量失败: {str(e)}")

    def get_table_data_by_keys(self, table_name: str, primary_keys: List[str], key_values: List[tuple]) -> List[Dict[str, Any]]:
        if not self.connection:
            self.connect()

        if not key_values:
            return []

        try:
            with self.connection.cursor() as cursor:
                if len(primary_keys) == 1:
                    placeholders = ','.join(['%s'] * len(key_values))
                    sql = f"SELECT * FROM `{table_name}` WHERE `{primary_keys[0]}` IN ({placeholders})"
                    cursor.execute(sql, [kv[0] for kv in key_values])
                else:
                    conditions = []
                    params = []
                    for key_value in key_values:
                        condition = ' AND '.join([f"`{pk}` = %s" for pk in primary_keys])
                        conditions.append(f"({condition})")
                        params.extend(key_value)

                    sql = f"SELECT * FROM `{table_name}` WHERE {' OR '.join(conditions)}"
                    cursor.execute(sql, params)

                return cursor.fetchall()
        except Exception as e:
            logger.error(f"根据主键获取数据失败: {str(e)}")
            raise Exception(f"根据主键获取数据失败: {str(e)}")

    def execute_query(self, sql: str, params: Optional[tuple] = None) -> List[Dict[str, Any]]:
        if not self.connection:
            self.connect()

        try:
            with self.connection.cursor() as cursor:
                if params:
                    cursor.execute(sql, params)
                else:
                    cursor.execute(sql)
                return cursor.fetchall()
        except Exception as e:
            logger.error(f"执行查询失败: {str(e)}")
            raise Exception(f"执行查询失败: {str(e)}")

    def close(self):
        if self.connection:
            self.connection.close()
            self.connection = None
            logger.info("数据库连接已关闭")

    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
