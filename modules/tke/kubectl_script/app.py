import os
import re
import subprocess
import threading
import uuid
import time
import json
from flask import Blueprint, render_template, jsonify, request, send_from_directory


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SCRIPT_DIR = os.path.join(BASE_DIR, 'script')
CONFIG_FILE = os.path.join(BASE_DIR, 'config.json')

bp = Blueprint('kubectl_script', __name__, 
               static_folder=os.path.join(BASE_DIR, 'static'),       # 子模块自己的静态文件
    template_folder=os.path.join(BASE_DIR, 'templates'))

# print(f"Blueprint BASE_DIR==> {BASE_DIR}")
# print(f"Blueprint SCRIPT_DIR==> {SCRIPT_DIR}")
# print(f"Blueprint static_folder==> {bp.static_folder}")
# print(f"Blueprint template_folder==> {bp.template_folder}")


EXECUTION_TIMEOUT = 30
running_processes = {}
execution_results = {}

def load_config():
    """加载配置文件"""
    default_config = {
        'forbidden_commands': [
            'rm', 'rmdir', 'del', 'mv', 'cp', 'chmod', 'chown',
            'kill', 'killall', 'pkill', 'systemctl', 'service', 'initctl',
            'iptables', 'ip', 'ifconfig', 'useradd', 'userdel', 'passwd',
            'apt', 'yum', 'apk', 'pip', 'npm', 'reboot', 'shutdown', 'halt'
        ],
        'clusters': [
            {
                'id': 'cls-ll9vckkf',
                'name': 'cls-ll9vckkf',
                'namespaces': [
                    'ns2-upgrade',
                    'ns2-scloud',
                    'ns2-scloud-old',
                    'ns2-uc-test'
                ]
            }
        ]
    }
    
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                config = json.load(f)
                return config
        except Exception as e:
            print(f"加载配置文件失败，使用默认配置: {e}")
            return default_config
    else:
        return default_config

config = load_config()
FORBIDDEN_COMMANDS = config.get('forbidden_commands', [])

def check_kubectl_installed():
    try:
        subprocess.run(['which', 'kubectl'], check=True, capture_output=True)
        return True
    except subprocess.CalledProcessError:
        return False

def validate_script(script_content):
    errors = []
    lines = script_content.split('\n')
    
    for i, line in enumerate(lines):
        line = line.strip()
        
        if (line.startswith('#') or line == '' or line.startswith('if ') or 
            line.startswith('then') or line.startswith('fi') or line.startswith('else') or
            line.startswith('echo ') or line.startswith('exit')):
            continue
        
        for forbidden in FORBIDDEN_COMMANDS:
            if re.search(r'\b' + re.escape(forbidden) + r'\b', line):
                errors.append({
                    'line': i + 1,
                    'command': forbidden,
                    'reason': f'禁止命令: {forbidden}'
                })
                break
    
    return {
        'valid': len(errors) == 0,
        'errors': errors
    }

def run_command_async(command, execution_id, timeout=EXECUTION_TIMEOUT):
    process = subprocess.Popen(
        command,
        shell=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )
    running_processes[execution_id] = process
    execution_results[execution_id] = {
        'status': 'running',
        'stdout': '',
        'stderr': '',
        'returncode': None,
        'command': command
    }
    
    def wait_for_process():
        try:
            stdout, stderr = process.communicate(timeout=timeout)
            execution_results[execution_id] = {
                'status': 'completed',
                'stdout': stdout,
                'stderr': stderr,
                'returncode': process.returncode,
                'command': command,
                'timeout': False
            }
        except subprocess.TimeoutExpired:
            process.kill()
            process.communicate()
            execution_results[execution_id] = {
                'status': 'timeout',
                'stdout': '',
                'stderr': f'执行超时（超过 {timeout} 秒）',
                'returncode': -1,
                'command': command,
                'timeout': True
            }
        finally:
            if execution_id in running_processes:
                del running_processes[execution_id]
    
    thread = threading.Thread(target=wait_for_process)
    thread.daemon = True
    thread.start()

@bp.route('/')
def index():
    return send_from_directory(os.path.join(BASE_DIR, 'templates'), 'index.html')

@bp.route('/api/check-kubectl')
def api_check_kubectl():
    return jsonify({'installed': check_kubectl_installed()})

@bp.route('/api/clusters')
def api_clusters():
    return jsonify({
        'clusters': config.get('clusters', [])
    })

@bp.route('/api/namespaces')
def api_namespaces():
    cluster_id = request.args.get('clusterId')
    
    if cluster_id:
        clusters = config.get('clusters', [])
        for cluster in clusters:
            if cluster.get('id') == cluster_id:
                return jsonify({
                    'namespaces': cluster.get('namespaces', [])
                })
        return jsonify({'namespaces': []})
    else:
        return jsonify({
            'namespaces': []
        })

@bp.route('/api/deployments')
def api_deployments():
    namespace = request.args.get('namespace')
    keyword = request.args.get('keyword', '')
    
    if not namespace:
        return jsonify({'error': '缺少命名空间参数'}), 400
    
    command = f'kubectl get deployments.apps --namespace {namespace}'
    if keyword:
        command += f' | grep {keyword}'
    
    try:
        result = subprocess.run(command, shell=True, capture_output=True, text=True, timeout=10)
        if result.returncode != 0 and not keyword:
            return jsonify({'error': result.stderr or '执行命令失败'}), 500
        
        lines = result.stdout.strip().split('\n')
        deployments = []
        
        for line in lines[1:]:
            if line.strip():
                parts = line.split()
                if parts:
                    deployments.append({
                        'name': parts[0],
                        'ready': parts[1] if len(parts) > 1 else '',
                        'updated': parts[2] if len(parts) > 2 else '',
                        'available': parts[3] if len(parts) > 3 else '',
                        'age': parts[4] if len(parts) > 4 else ''
                    })
        
        return jsonify({'deployments': deployments})
    except subprocess.TimeoutExpired:
        return jsonify({'error': '查询超时，请检查集群连接'}), 500
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@bp.route('/api/pods')
def api_pods():
    namespace = request.args.get('namespace')
    deployment = request.args.get('deployment', '')
    
    if not namespace:
        return jsonify({'error': '缺少命名空间参数'}), 400
    
    command = f'kubectl get pods -n {namespace}'
    if deployment:
        command += f' | grep {deployment}'
    
    try:
        result = subprocess.run(command, shell=True, capture_output=True, text=True, timeout=10)
        if result.returncode != 0 and not deployment:
            return jsonify({'error': result.stderr or '执行命令失败'}), 500

        lines = result.stdout.strip().split('\n')
        pods = []
        
        start_index = 1 if not deployment else 0
        
        for line in lines[start_index:]:
            if line.strip():
                parts = line.split()
                if parts:
                    pods.append({
                        'name': parts[0],
                        'ready': parts[1] if len(parts) > 1 else '',
                        'status': parts[2] if len(parts) > 2 else '',
                        'restarts': parts[3] if len(parts) > 3 else '',
                        'age': parts[4] if len(parts) > 4 else ''
                    })
        
        return jsonify({'pods': pods})
    except subprocess.TimeoutExpired:
        return jsonify({'error': '查询超时，请检查集群连接'}), 500
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@bp.route('/api/scripts')
def api_scripts():
    if not os.path.exists(SCRIPT_DIR):
        os.makedirs(SCRIPT_DIR, exist_ok=True)
        return jsonify({'scripts': []})
    
    scripts = []
    for filename in os.listdir(SCRIPT_DIR):
        if filename.endswith('.sh'):
            filepath = os.path.join(SCRIPT_DIR, filename)
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    content = f.read()
                validation = validate_script(content)
                scripts.append({
                    'name': filename,
                    'path': filepath,
                    'valid': validation['valid'],
                    'errors': validation['errors']
                })
            except Exception as e:
                scripts.append({
                    'name': filename,
                    'path': filepath,
                    'valid': False,
                    'errors': [{'line': 0, 'reason': f'读取文件失败: {str(e)}'}]
                })
    
    return jsonify({'scripts': scripts})

@bp.route('/api/script/content')
def api_script_content():
    script_path = request.args.get('path')
    
    if not script_path:
        return jsonify({'error': '缺少脚本路径参数'}), 400
    
    if not script_path.startswith(SCRIPT_DIR):
        return jsonify({'error': '无效的脚本路径'}), 400
    
    try:
        with open(script_path, 'r', encoding='utf-8') as f:
            content = f.read()
        return jsonify({'content': content})
    except Exception as e:
        return jsonify({'error': f'读取脚本失败: {str(e)}'}), 500

@bp.route('/api/script/save', methods=['POST'])
def api_script_save():
    data = request.get_json()
    script_path = data.get('path')
    content = data.get('content')
    
    if not script_path or content is None:
        return jsonify({'error': '缺少必要参数'}), 400
    
    if not script_path.startswith(SCRIPT_DIR):
        return jsonify({'error': '无效的脚本路径'}), 400
    
    try:
        with open(script_path, 'w', encoding='utf-8') as f:
            f.write(content)
        return jsonify({'success': True, 'message': '保存成功'})
    except Exception as e:
        return jsonify({'error': f'保存脚本失败: {str(e)}'}), 500

@bp.route('/api/command/validate', methods=['POST'])
def api_command_validate():
    data = request.get_json()
    command = data.get('command', '')
    
    validation = validate_script(command)
    return jsonify(validation)

@bp.route('/api/execute/start', methods=['POST'])
def api_execute_start():
    data = request.get_json()
    pod = data.get('pod')
    namespace = data.get('namespace')
    script_path = data.get('scriptPath')
    command_text = data.get('command')
    
    if not pod or not namespace:
        return jsonify({'error': '缺少必要参数'}), 400
    
    execution_id = str(uuid.uuid4())
    
    if script_path:
        try:
            with open(script_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            validation = validate_script(content)
            if not validation['valid']:
                return jsonify({
                    'error': '脚本安全验证失败',
                    'details': validation['errors']
                }), 400
            
            command = f'cat "{script_path}" | kubectl exec -i {pod} --namespace {namespace} -- sh -s'
        except FileNotFoundError:
            return jsonify({'error': f'脚本文件不存在: {script_path}'}), 400
        except Exception as e:
            return jsonify({'error': f'读取脚本失败: {str(e)}'}), 400
    elif command_text:
        validation = validate_script(command_text)
        if not validation['valid']:
            return jsonify({
                'error': '命令安全验证失败',
                'details': validation['errors']
            }), 400
        
        command = f'kubectl exec {pod} --namespace {namespace} -- sh -c \'{command_text}\''
    else:
        return jsonify({'error': '缺少脚本路径或命令'}), 400
    
    run_command_async(command, execution_id)
    
    return jsonify({
        'success': True,
        'executionId': execution_id,
        'command': command
    })

@bp.route('/api/execute/status', methods=['GET'])
def api_execute_status():
    execution_id = request.args.get('executionId')
    
    if not execution_id:
        return jsonify({'error': '缺少执行ID'}), 400
    
    if execution_id not in execution_results:
        return jsonify({'error': '未找到执行任务'}), 404
    
    result = execution_results[execution_id]
    
    response = {
        'status': result['status'],
        'command': result['command']
    }
    
    if result['status'] in ['completed', 'timeout']:
        response['stdout'] = result['stdout']
        response['stderr'] = result['stderr']
        response['returncode'] = result['returncode']
        response['timeout'] = result.get('timeout', False)
    
    return jsonify(response)

@bp.route('/api/execute/abort', methods=['POST'])
def api_execute_abort():
    data = request.get_json()
    execution_id = data.get('executionId')
    
    if not execution_id:
        return jsonify({'error': '缺少执行ID'}), 400
    
    if execution_id in running_processes:
        process = running_processes[execution_id]
        process.kill()
        del running_processes[execution_id]
        execution_results[execution_id] = {
            'status': 'aborted',
            'stdout': '',
            'stderr': '执行已被用户中止',
            'returncode': -1,
            'command': execution_results.get(execution_id, {}).get('command', ''),
            'timeout': False
        }
        return jsonify({'success': True, 'message': '已中止执行'})
    
    return jsonify({'error': '未找到执行中的任务'}), 404

@bp.route('/api/execute', methods=['POST'])
def api_execute():
    data = request.get_json()
    pod = data.get('pod')
    namespace = data.get('namespace')
    script_path = data.get('scriptPath')
    
    if not pod or not namespace or not script_path:
        return jsonify({'error': '缺少必要参数'}), 400
    
    try:
        with open(script_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        validation = validate_script(content)
        if not validation['valid']:
            return jsonify({
                'error': '脚本安全验证失败',
                'details': validation['errors']
            }), 400
        
        command = f'cat "{script_path}" | kubectl exec -i {pod} --namespace {namespace} -- sh -s'
        result = subprocess.run(command, shell=True, capture_output=True, text=True, timeout=EXECUTION_TIMEOUT)
        
        if result.returncode != 0:
            return jsonify({'error': result.stderr or '执行命令失败'}), 500
        
        return jsonify({
            'success': True,
            'output': result.stdout,
            'command': command
        })
    except subprocess.TimeoutExpired:
        return jsonify({'error': f'执行超时（超过 {EXECUTION_TIMEOUT} 秒）'}), 500
    except FileNotFoundError:
        return jsonify({'error': f'脚本文件不存在: {script_path}'}), 400
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@bp.route('/api/execute/command', methods=['POST'])
def api_execute_command():
    data = request.get_json()
    pod = data.get('pod')
    namespace = data.get('namespace')
    command_text = data.get('command', '')
    
    if not pod or not namespace or not command_text:
        return jsonify({'error': '缺少必要参数'}), 400
    
    validation = validate_script(command_text)
    if not validation['valid']:
        return jsonify({
            'error': '命令安全验证失败',
            'details': validation['errors']
        }), 400
    
    try:
        command = f'kubectl exec {pod} --namespace {namespace} -- sh -c \'{command_text}\''
        result = subprocess.run(command, shell=True, capture_output=True, text=True, timeout=EXECUTION_TIMEOUT)
        
        if result.returncode != 0:
            return jsonify({'error': result.stderr or '执行命令失败'}), 500
        
        return jsonify({
            'success': True,
            'output': result.stdout,
            'command': command
        })
    except subprocess.TimeoutExpired:
        return jsonify({'error': f'执行超时（超过 {EXECUTION_TIMEOUT} 秒）'}), 500
    except Exception as e:
        return jsonify({'error': str(e)}), 500
