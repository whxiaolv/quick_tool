#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MySQL 数据库差异对比工具 - 独立运行脚本

用法:
    python db_diff_tool.py --left-config left.json --right-config right.json --left-table table1 --right-table table2
    python db_diff_tool.py --left-file data1.sql --right-file data2.sql --output ./reports

配置文件格式 (JSON):
{
    "host": "localhost",
    "port": 3306,
    "database": "db_name",
    "user": "root",
    "password": "password"
}
"""

import os
import sys
import json
import argparse
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from db_connector import DatabaseConnector
from db_comparator import DatabaseComparator
from report_generator import ReportGenerator
from file_parser import FileParser


def parse_args():
    parser = argparse.ArgumentParser(
        description='MySQL 数据库差异对比工具',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
示例:
  # 对比两个数据库表
  python db_diff_tool.py --left-config left.json --right-config right.json --left-table users --right-table users_backup
  
  # 对比两个文件
  python db_diff_tool.py --left-file data1.sql --right-file data2.sql --output ./reports
  
  # 使用命令行参数
  python db_diff_tool.py --left-host localhost --left-port 3306 --left-db test --left-user root --left-pass password --left-table users \
                         --right-host localhost --right-port 3306 --right-db test2 --right-user root --right-pass password --right-table users
        '''
    )
    
    parser.add_argument('--left-config', help='左侧数据库配置文件 (JSON)')
    parser.add_argument('--right-config', help='右侧数据库配置文件 (JSON)')
    parser.add_argument('--left-table', help='左侧表名')
    parser.add_argument('--right-table', help='右侧表名')
    
    parser.add_argument('--left-file', help='左侧数据文件 (SQL/CSV/JSON)')
    parser.add_argument('--right-file', help='右侧数据文件 (SQL/CSV/JSON)')
    
    parser.add_argument('--left-host', help='左侧数据库主机')
    parser.add_argument('--left-port', type=int, default=3306, help='左侧数据库端口')
    parser.add_argument('--left-db', help='左侧数据库名')
    parser.add_argument('--left-user', help='左侧数据库用户名')
    parser.add_argument('--left-pass', help='左侧数据库密码')
    
    parser.add_argument('--right-host', help='右侧数据库主机')
    parser.add_argument('--right-port', type=int, default=3306, help='右侧数据库端口')
    parser.add_argument('--right-db', help='右侧数据库名')
    parser.add_argument('--right-user', help='右侧数据库用户名')
    parser.add_argument('--right-pass', help='右侧数据库密码')
    
    parser.add_argument('--output', default='./reports', help='报告输出目录')
    parser.add_argument('--batch-size', type=int, default=1000, help='批量查询大小')
    
    return parser.parse_args()


def load_config(config_file):
    with open(config_file, 'r', encoding='utf-8') as f:
        return json.load(f)


def get_left_config(args):
    if args.left_config:
        return load_config(args.left_config)
    
    if args.left_host and args.left_db and args.left_user:
        return {
            'host': args.left_host,
            'port': args.left_port,
            'database': args.left_db,
            'user': args.left_user,
            'password': args.left_pass or ''
        }
    
    return None


def get_right_config(args):
    if args.right_config:
        return load_config(args.right_config)
    
    if args.right_host and args.right_db and args.right_user:
        return {
            'host': args.right_host,
            'port': args.right_port,
            'database': args.right_db,
            'user': args.right_user,
            'password': args.right_pass or ''
        }
    
    return None


def compare_databases(left_config, right_config, left_table, right_table, output_dir, batch_size):
    print(f"开始对比数据库表...")
    print(f"左侧: {left_config['host']}:{left_config['port']}/{left_config['database']}.{left_table}")
    print(f"右侧: {right_config['host']}:{right_config['port']}/{right_config['database']}.{right_table}")
    
    left_connector = DatabaseConnector(left_config)
    right_connector = DatabaseConnector(right_config)
    
    try:
        left_connector.connect()
        right_connector.connect()
        
        comparator = DatabaseComparator(left_connector, right_connector)
        result = comparator.compare_tables(left_table, right_table)
        
        report_generator = ReportGenerator(output_dir)
        left_name = f"{left_config['database']}.{left_table}"
        right_name = f"{right_config['database']}.{right_table}"
        report_path = report_generator.generate(result, left_name, right_name)
        
        print(f"\n对比完成!")
        print(f"报告已生成: {report_path}")
        
        stats = result.get('data', {}).get('stats', {})
        print(f"\n统计信息:")
        print(f"  左表总数据量: {stats.get('left_count', 0)}  |  右表总数据量: {stats.get('right_count', 0)}")
        print(f"  相同数据: {stats.get('common', 0)}  |  差异数据: {stats.get('different', 0)}")
        print(f"  左侧独有: {stats.get('left_only', 0)}  |  右侧独有: {stats.get('right_only', 0)}")
        
        return report_path
        
    finally:
        left_connector.close()
        right_connector.close()


def compare_files(left_file, right_file, output_dir):
    print(f"开始对比文件...")
    print(f"左侧: {left_file}")
    print(f"右侧: {right_file}")
    
    left_parsed = FileParser.parse_file(left_file)
    right_parsed = FileParser.parse_file(right_file)
    
    left_table_name = list(left_parsed['tables'].keys())[0] if left_parsed['tables'] else 'unknown'
    right_table_name = list(right_parsed['tables'].keys())[0] if right_parsed['tables'] else 'unknown'
    
    left_table = left_parsed['tables'].get(left_table_name, {})
    right_table = right_parsed['tables'].get(right_table_name, {})
    
    left_fields = left_table.get('fields', [])
    right_fields = right_table.get('fields', [])
    
    field_comparison = {
        'common': [],
        'left_only': [],
        'right_only': [],
        'different': [],
        'stats': {
            'total': 0,
            'common': 0,
            'left_only': 0,
            'right_only': 0,
            'different': 0
        }
    }
    
    left_field_names = {f['Field'] for f in left_fields}
    right_field_names = {f['Field'] for f in right_fields}
    
    all_field_names = left_field_names | right_field_names
    field_comparison['stats']['total'] = len(all_field_names)
    
    for field_name in all_field_names:
        if field_name in left_field_names and field_name in right_field_names:
            field_comparison['common'].append({'field': field_name})
            field_comparison['stats']['common'] += 1
        elif field_name in left_field_names:
            field_comparison['left_only'].append({'field': field_name})
            field_comparison['stats']['left_only'] += 1
        else:
            field_comparison['right_only'].append({'field': field_name})
            field_comparison['stats']['right_only'] += 1
    
    left_data = left_table.get('data', [])
    right_data = right_table.get('data', [])
    
    data_comparison = {
        'common': [],
        'different': [],
        'left_only': [],
        'right_only': [],
        'stats': {
            'total': 0,
            'common': 0,
            'different': 0,
            'left_only': 0,
            'right_only': 0
        }
    }
    
    if left_data and right_data:
        if isinstance(left_data[0], dict) and isinstance(right_data[0], dict):
            left_keys = set(left_data[0].keys())
            right_keys = set(right_data[0].keys())
            common_keys = left_keys & right_keys
            
            if common_keys:
                primary_key = list(common_keys)[0]
                
                left_data_map = {item.get(primary_key): item for item in left_data}
                right_data_map = {item.get(primary_key): item for item in right_data}
                
                all_keys = set(left_data_map.keys()) | set(right_data_map.keys())
                data_comparison['stats']['total'] = len(all_keys)
                
                for key in all_keys:
                    if key in left_data_map and key in right_data_map:
                        if left_data_map[key] == right_data_map[key]:
                            data_comparison['common'].append({
                                'key': (key,),
                                'data': left_data_map[key]
                            })
                            data_comparison['stats']['common'] += 1
                        else:
                            differences = {}
                            for k in common_keys:
                                if left_data_map[key].get(k) != right_data_map[key].get(k):
                                    differences[k] = (
                                        left_data_map[key].get(k),
                                        right_data_map[key].get(k)
                                    )
                            
                            data_comparison['different'].append({
                                'key': (key,),
                                'left': left_data_map[key],
                                'right': right_data_map[key],
                                'differences': differences
                            })
                            data_comparison['stats']['different'] += 1
                    elif key in left_data_map:
                        data_comparison['left_only'].append({
                            'key': (key,),
                            'data': left_data_map[key]
                        })
                        data_comparison['stats']['left_only'] += 1
                    else:
                        data_comparison['right_only'].append({
                            'key': (key,),
                            'data': right_data_map[key]
                        })
                        data_comparison['stats']['right_only'] += 1
    
    result = {
        'left_table': left_table_name,
        'right_table': right_table_name,
        'structure': {
            'fields': field_comparison,
            'indexes': {
                'common': [],
                'left_only': [],
                'right_only': [],
                'different': [],
                'stats': {
                    'total': 0,
                    'common': 0,
                    'left_only': 0,
                    'right_only': 0,
                    'different': 0
                }
            }
        },
        'data': data_comparison
    }
    
    report_generator = ReportGenerator(output_dir)
    left_name = os.path.basename(left_file)
    right_name = os.path.basename(right_file)
    report_path = report_generator.generate(result, left_name, right_name)
    
    print(f"\n对比完成!")
    print(f"报告已生成: {report_path}")
    
    stats = data_comparison.get('stats', {})
    print(f"\n统计信息:")
    print(f"  左表总数据量: {stats.get('left_count', 0)}  |  右表总数据量: {stats.get('right_count', 0)}")
    print(f"  相同数据: {stats.get('common', 0)}  |  差异数据: {stats.get('different', 0)}")
    print(f"  左侧独有: {stats.get('left_only', 0)}  |  右侧独有: {stats.get('right_only', 0)}")
    
    return report_path


def main():
    args = parse_args()
    
    if not os.path.exists(args.output):
        os.makedirs(args.output, exist_ok=True)
    
    if args.left_file and args.right_file:
        if not os.path.exists(args.left_file):
            print(f"错误: 左侧文件不存在: {args.left_file}")
            sys.exit(1)
        
        if not os.path.exists(args.right_file):
            print(f"错误: 右侧文件不存在: {args.right_file}")
            sys.exit(1)
        
        compare_files(args.left_file, args.right_file, args.output)
        
    elif args.left_config or args.right_config:
        left_config = get_left_config(args)
        right_config = get_right_config(args)
        
        if not left_config:
            print("错误: 请提供左侧数据库配置")
            sys.exit(1)
        
        if not right_config:
            print("错误: 请提供右侧数据库配置")
            sys.exit(1)
        
        if not args.left_table or not args.right_table:
            print("错误: 请提供表名 (--left-table 和 --right-table)")
            sys.exit(1)
        
        compare_databases(
            left_config,
            right_config,
            args.left_table,
            args.right_table,
            args.output,
            args.batch_size
        )
        
    else:
        print("错误: 请提供数据库配置或文件路径")
        parser.print_help()
        sys.exit(1)


if __name__ == '__main__':
    main()
