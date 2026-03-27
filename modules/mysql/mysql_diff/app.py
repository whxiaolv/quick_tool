import os
import sys
import uuid
import json
import threading
from datetime import datetime
from flask import Blueprint, render_template, jsonify, request, send_from_directory
from werkzeug.utils import secure_filename

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from db_connector import DatabaseConnector
from db_comparator import DatabaseComparator
from report_generator import ReportGenerator
from file_parser import FileParser
from db_full_compare import MySQLDatabaseFullComparator
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_DIR = os.path.join(BASE_DIR, 'uploads')
REPORT_DIR = os.path.join(BASE_DIR, 'static/reports')

os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(REPORT_DIR, exist_ok=True)

bp = Blueprint('mysql_diff', __name__,
               static_folder=os.path.join(BASE_DIR, 'static'),
               template_folder=os.path.join(BASE_DIR, 'templates'))

ALLOWED_EXTENSIONS = {'sql', 'csv', 'json'}
MAX_FILE_SIZE = 50 * 1024 * 1024

comparison_tasks = {}


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@bp.route('/')
def index():
    return send_from_directory(os.path.join(BASE_DIR, 'templates'), 'index.html')


@bp.route('/api/test-connection', methods=['POST'])
def test_connection():
    try:
        data = request.get_json()

        config = {
            'host': data.get('host'),
            'port': data.get('port', 3306),
            'database': data.get('database'),
            'user': data.get('user'),
            'password': data.get('password')
        }

        connector = DatabaseConnector(config)
        result = connector.test_connection()

        return jsonify(result)

    except Exception as e:
        logger.error(f"测试连接失败: {str(e)}")
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


@bp.route('/api/tables', methods=['POST'])
def get_tables():
    try:
        data = request.get_json()

        config = {
            'host': data.get('host'),
            'port': data.get('port', 3306),
            'database': data.get('database'),
            'user': data.get('user'),
            'password': data.get('password')
        }

        connector = DatabaseConnector(config)
        connector.connect()
        tables = connector.get_tables()
        connector.close()

        return jsonify({
            'success': True,
            'tables': tables
        })

    except Exception as e:
        logger.error(f"获取表列表失败: {str(e)}")
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


@bp.route('/api/upload', methods=['POST'])
def upload_files():
    try:
        if 'files' not in request.files:
            return jsonify({
                'success': False,
                'message': '没有上传文件'
            }), 400

        files = request.files.getlist('files')
        uploaded_files = []

        for file in files:
            if file.filename == '':
                continue

            if not allowed_file(file.filename):
                return jsonify({
                    'success': False,
                    'message': f'不支持的文件类型: {file.filename}'
                }), 400

            filename = secure_filename(file.filename)
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            unique_filename = f"{timestamp}_{filename}"
            filepath = os.path.join(UPLOAD_DIR, unique_filename)

            file.save(filepath)

            file_size = os.path.getsize(filepath)
            if file_size > MAX_FILE_SIZE:
                os.remove(filepath)
                return jsonify({
                    'success': False,
                    'message': f'文件过大: {file.filename} (最大 50MB)'
                }), 400

            uploaded_files.append({
                'filename': filename,
                'path': filepath,
                'size': file_size,
                'type': filename.rsplit('.', 1)[1].lower()
            })

        return jsonify({
            'success': True,
            'files': uploaded_files
        })

    except Exception as e:
        logger.error(f"文件上传失败: {str(e)}")
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


@bp.route('/api/parse-file', methods=['POST'])
def parse_file():
    try:
        data = request.get_json()
        file_path = data.get('filePath')

        if not file_path or not os.path.exists(file_path):
            return jsonify({
                'success': False,
                'message': '文件不存在'
            }), 400

        parsed = FileParser.parse_file(file_path)

        return jsonify({
            'success': True,
            'parsed': parsed
        })

    except Exception as e:
        logger.error(f"文件解析失败: {str(e)}")
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


@bp.route('/api/compare', methods=['POST'])
def compare():
    try:
        data = request.get_json()

        left = data.get('left', {})
        right = data.get('right', {})

        task_id = str(uuid.uuid4())

        comparison_tasks[task_id] = {
            'status': 'pending',
            'progress': 0,
            'result': None,
            'error': None
        }

        thread = threading.Thread(
            target=run_comparison,
            args=(task_id, left, right)
        )
        thread.daemon = True
        thread.start()

        return jsonify({
            'success': True,
            'taskId': task_id
        })

    except Exception as e:
        logger.error(f"启动对比任务失败: {str(e)}")
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


def run_comparison(task_id, left_config, right_config):
    try:
        comparison_tasks[task_id]['status'] = 'running'
        comparison_tasks[task_id]['progress'] = 10

        left_connector = None
        right_connector = None

        if left_config.get('type') == 'database':
            left_connector = DatabaseConnector(left_config.get('config'))
            left_connector.connect()
            left_name = f"{left_config['config']['database']}.{left_config['table']}"
        else:
            parsed = FileParser.parse_file(left_config['filePath'])
            table_name = list(parsed['tables'].keys())[0] if parsed['tables'] else 'unknown'
            left_name = f"{left_config['fileName']}:{table_name}"

        comparison_tasks[task_id]['progress'] = 30

        if right_config.get('type') == 'database':
            right_connector = DatabaseConnector(right_config.get('config'))
            right_connector.connect()
            right_name = f"{right_config['config']['database']}.{right_config['table']}"
        else:
            parsed = FileParser.parse_file(right_config['filePath'])
            table_name = list(parsed['tables'].keys())[0] if parsed['tables'] else 'unknown'
            right_name = f"{right_config['fileName']}:{table_name}"

        comparison_tasks[task_id]['progress'] = 50

        if left_config.get('type') == 'database' and right_config.get('type') == 'database':
            comparator = DatabaseComparator(left_connector, right_connector)
            result = comparator.compare_tables(
                left_config['table'],
                right_config['table']
            )
        else:
            result = compare_from_files(left_config, right_config)

        comparison_tasks[task_id]['progress'] = 80

        report_generator = ReportGenerator(REPORT_DIR)
        report_path = report_generator.generate(result, left_name, right_name)

        relative_path = os.path.relpath(report_path, BASE_DIR)
        
        report_url = f"{relative_path.replace(os.sep, '/')}"

        # print(f'report_url====>: {report_url}')

        comparison_tasks[task_id]['status'] = 'completed'
        comparison_tasks[task_id]['progress'] = 100
        comparison_tasks[task_id]['result'] = {
            'reportUrl': report_url,
            'stats': result.get('data', {}).get('stats', {})
        }

        if left_connector:
            left_connector.close()
        if right_connector:
            right_connector.close()

    except Exception as e:
        logger.error(f"对比任务失败: {str(e)}")
        comparison_tasks[task_id]['status'] = 'failed'
        comparison_tasks[task_id]['error'] = str(e)


def compare_from_files(left_config, right_config):
    left_parsed = FileParser.parse_file(left_config['filePath'])
    right_parsed = FileParser.parse_file(right_config['filePath'])

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

    return {
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


@bp.route('/api/compare/status', methods=['GET'])
def get_comparison_status():
    try:
        task_id = request.args.get('taskId')

        if not task_id or task_id not in comparison_tasks:
            return jsonify({
                'success': False,
                'message': '任务不存在'
            }), 404

        task = comparison_tasks[task_id]

        response = {
            'success': True,
            'status': task['status'],
            'progress': task['progress']
        }

        if task['status'] == 'completed' and task['result']:
            response['result'] = task['result']
        elif task['status'] == 'failed' and task['error']:
            response['error'] = task['error']

        return jsonify(response)

    except Exception as e:
        logger.error(f"获取任务状态失败: {str(e)}")
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


@bp.route('/api/reports', methods=['GET'])
def get_reports():
    try:
        reports = []

        for year in os.listdir(REPORT_DIR):
            year_dir = os.path.join(REPORT_DIR, year)
            if not os.path.isdir(year_dir):
                continue

            for month in os.listdir(year_dir):
                month_dir = os.path.join(year_dir, month)
                if not os.path.isdir(month_dir):
                    continue

                for filename in os.listdir(month_dir):
                    if filename.endswith('.html'):
                        filepath = os.path.join(month_dir, filename)
                        stat = os.stat(filepath)

                        relative_path = os.path.relpath(filepath, BASE_DIR)
                        
                        report_url = f"{relative_path.replace(os.sep, '/')}"

                        # print(f'report_url====>: {report_url}')

                        reports.append({
                            'id': filename.replace('.html', ''),
                            'filename': filename,
                            'url': report_url,
                            'timestamp': datetime.fromtimestamp(stat.st_mtime).strftime('%Y-%m-%d %H:%M:%S'),
                            'size': stat.st_size
                        })

        reports.sort(key=lambda x: x['timestamp'], reverse=True)

        return jsonify({
            'success': True,
            'reports': reports[:50]
        })

    except Exception as e:
        logger.error(f"获取报告列表失败: {str(e)}")
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


@bp.route('/api/reports/delete', methods=['POST'])
def delete_report():
    try:
        data = request.get_json()
        report_id = data.get('id')
        
        if not report_id:
            return jsonify({
                'success': False,
                'message': '缺少报告ID'
            }), 400
        
        found = False
        for year in os.listdir(REPORT_DIR):
            year_dir = os.path.join(REPORT_DIR, year)
            if not os.path.isdir(year_dir):
                continue

            for month in os.listdir(year_dir):
                month_dir = os.path.join(year_dir, month)
                if not os.path.isdir(month_dir):
                    continue

                filename = f"{report_id}.html"
                filepath = os.path.join(month_dir, filename)
                
                if os.path.exists(filepath):
                    os.remove(filepath)
                    found = True
                    logger.info(f"已删除报告: {filepath}")
                    break
            
            if found:
                break

        if found:
            return jsonify({
                'success': True,
                'message': '报告已删除'
            })
        else:
            return jsonify({
                'success': False,
                'message': '报告不存在'
            }), 404

    except Exception as e:
        logger.error(f"删除报告失败: {str(e)}")
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


@bp.route('/api/reports/batch-delete', methods=['POST'])
def batch_delete_reports():
    try:
        data = request.get_json()
        report_ids = data.get('ids', [])
        
        if not report_ids:
            return jsonify({
                'success': False,
                'message': '缺少报告ID列表'
            }), 400
        
        deleted_count = 0
        failed_ids = []
        
        for report_id in report_ids:
            found = False
            for year in os.listdir(REPORT_DIR):
                year_dir = os.path.join(REPORT_DIR, year)
                if not os.path.isdir(year_dir):
                    continue

                for month in os.listdir(year_dir):
                    month_dir = os.path.join(year_dir, month)
                    if not os.path.isdir(month_dir):
                        continue

                    filename = f"{report_id}.html"
                    filepath = os.path.join(month_dir, filename)
                    
                    if os.path.exists(filepath):
                        try:
                            os.remove(filepath)
                            found = True
                            deleted_count += 1
                            logger.info(f"已删除报告: {filepath}")
                        except Exception as e:
                            logger.error(f"删除报告失败 {filepath}: {str(e)}")
                            failed_ids.append(report_id)
                        break
                
                if found:
                    break
            
            if not found:
                failed_ids.append(report_id)

        return jsonify({
            'success': True,
            'message': f'成功删除 {deleted_count} 个报告',
            'deleted_count': deleted_count,
            'failed_ids': failed_ids
        })

    except Exception as e:
        logger.error(f"批量删除报告失败: {str(e)}")
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


@bp.route('/api/compare-database', methods=['POST'])
def compare_database():
    try:
        data = request.get_json()

        left_config = data.get('left', {})
        right_config = data.get('right', {})

        task_id = str(uuid.uuid4())

        comparison_tasks[task_id] = {
            'status': 'pending',
            'progress': 0,
            'result': None,
            'error': None
        }

        thread = threading.Thread(
            target=run_database_comparison,
            args=(task_id, left_config, right_config)
        )
        thread.daemon = True
        thread.start()

        return jsonify({
            'success': True,
            'taskId': task_id
        })

    except Exception as e:
        logger.error(f"启动数据库对比任务失败: {str(e)}")
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


def run_database_comparison(task_id, left_config, right_config):
    try:
        comparison_tasks[task_id]['status'] = 'running'
        comparison_tasks[task_id]['progress'] = 10

        left_port = left_config.get('port', 3306)
        right_port = right_config.get('port', 3306)

        comparator = MySQLDatabaseFullComparator(left_config, right_config)

        comparison_tasks[task_id]['progress'] = 20

        comparator.connect()

        comparison_tasks[task_id]['progress'] = 30

        result = comparator.compare_databases()

        comparison_tasks[task_id]['progress'] = 80

        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"{left_port}_{right_port}_diff_report_{timestamp}.html"
        
        year_month_dir = datetime.now().strftime('%Y/%m')
        report_dir = os.path.join(REPORT_DIR, year_month_dir)
        os.makedirs(report_dir, exist_ok=True)
        
        report_path = os.path.join(report_dir, filename)
        comparator.generate_report(result, report_path)

        relative_path = os.path.relpath(report_path, BASE_DIR)
        report_url = f"{relative_path.replace(os.sep, '/')}"

        comparison_tasks[task_id]['status'] = 'completed'
        comparison_tasks[task_id]['progress'] = 100
        comparison_tasks[task_id]['result'] = {
            'reportUrl': report_url,
            'stats': {
                'left_table_count': result['left_table_count'],
                'right_table_count': result['right_table_count'],
                'common_table_count': result['common_table_count']
            }
        }

        comparator.close()

    except Exception as e:
        logger.error(f"数据库对比任务失败: {str(e)}")
        comparison_tasks[task_id]['status'] = 'failed'
        comparison_tasks[task_id]['error'] = str(e)
        if 'comparator' in locals():
            try:
                comparator.close()
            except:
                pass
