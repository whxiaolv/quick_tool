import os
import re
import subprocess
import json
import sys
from flask import Blueprint, render_template, jsonify, request, send_from_directory

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SCRIPT_DIR = os.path.join(BASE_DIR, 'script')
CONFIG_FILE = os.path.join(BASE_DIR, 'config.json')

bp = Blueprint('kubectl_select', __name__,
               static_folder=os.path.join(BASE_DIR, 'static'),
               template_folder=os.path.join(BASE_DIR, 'templates'))

EXECUTION_TIMEOUT = 30

def load_config():
    default_config = {
        'forbidden_commands': [
            'delete', 'create', 'apply', 'patch', 'replace',
            'edit', 'scale', 'autoscale', 'cordon', 'uncordon',
            'drain', 'taint', 'port-forward', 'proxy', 'attach',
            'exec', 'cp', 'auth', 'certificate', 'cluster-info',
            'top'
        ],
        'allowed_commands': [
            'get', 'describe', 'logs', 'explain', 'api-resources', 'api-versions'
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
ALLOWED_COMMANDS = config.get('allowed_commands', [])

def validate_kubectl_command(script_content):
    errors = []
    lines = script_content.split('\n')
    
    for i, line in enumerate(lines):
        line = line.strip()
        
        if (line == '' or line.startswith('#') or line.startswith('import') or 
            line.startswith('from') or line.startswith('def') or 
            line.startswith('class') or line.startswith('return') or
            line.startswith('print') or line.startswith('json.') or
            line.startswith('subprocess.') or line.startswith('sys.') or
            line.startswith('os.') or line.startswith('if ') or
            line.startswith('elif ') or line.startswith('else:') or
            line.startswith('for ') or line.startswith('while ') or
            line.startswith('try:') or line.startswith('except') or
            line.startswith('finally:') or line.startswith('with ') or
            line.startswith('pass') or line.startswith('continue') or
            line.startswith('break')):
            continue
        
        kubectl_pattern = r'kubectl\s+(\w+)'
        matches = re.findall(kubectl_pattern, line)
        
        for match in matches:
            if match in FORBIDDEN_COMMANDS:
                errors.append({
                    'line': i + 1,
                    'command': match,
                    'reason': f'禁止命令: kubectl {match}'
                })
    
    return {
        'valid': len(errors) == 0,
        'errors': errors
    }

def check_kubectl_installed():
    try:
        subprocess.run(['which', 'kubectl'], check=True, capture_output=True)
        return True
    except subprocess.CalledProcessError:
        return False

def parse_script_info(content):
    """
    从Python脚本内容中，提取 TITLE、DESCRIPTION（支持大小写）
    """
    info = {
        "title": "",
        "description": ""
    }

    # 只按行解析前20行
    lines = content.splitlines()[:20]

    for line in lines:
        line = line.strip()
        # 匹配 TITLE: 支持 # title: / # TITLE:
        title_match = re.match(r'^#\s*TITLE:\s*(.*)', line, re.IGNORECASE)
        if title_match:
            info["title"] = title_match.group(1).strip()

        # 匹配 DESCRIPTION:
        desc_match = re.match(r'^#\s*DESCRIPTION:\s*(.*)', line, re.IGNORECASE)
        if desc_match:
            info["description"] = desc_match.group(1).strip()

    return info

@bp.route('/')
def index():
    return send_from_directory(os.path.join(BASE_DIR, 'templates'), 'index.html')

@bp.route('api/check-kubectl')
def api_check_kubectl():
    return jsonify({'installed': check_kubectl_installed()})

@bp.route('api/scripts')
def api_scripts():
    print(SCRIPT_DIR)
    if not os.path.exists(SCRIPT_DIR):
        os.makedirs(SCRIPT_DIR, exist_ok=True)
        return jsonify({'scripts': []})
    
    scripts = []
    for filename in os.listdir(SCRIPT_DIR):
        if filename.endswith('.py'):
            filepath = os.path.join(SCRIPT_DIR, filename)
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                validation = validate_kubectl_command(content)
                # 直接复用 content 解析标题和描述
                script_info = parse_script_info(content)
                
                scripts.append({
                    'title': script_info['title'],
                    'description': script_info['description'],
                    'name': filename,
                    'path': filepath,
                    'valid': validation['valid'],
                    'errors': validation['errors']
                })
            except Exception as e:
                scripts.append({
                    'title': script_info['title'],
                    'description': script_info['description'],
                    'name': filename,
                    'path': filepath,
                    'valid': False,
                    'errors': [{'line': 0, 'reason': f'读取文件失败: {str(e)}'}]
                })
    
    return jsonify({'scripts': scripts})

@bp.route('api/script/content')
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

@bp.route('api/script/save', methods=['POST'])
def api_script_save():
    data = request.get_json()
    script_path = data.get('path')
    content = data.get('content')
    
    if not script_path or content is None:
        return jsonify({'error': '缺少必要参数'}), 400

    create = data.get('create', 0) 
    # 1 表示新建，0 表示编辑    
    if create == 0:
        if not script_path.startswith(SCRIPT_DIR):
            return jsonify({'error': '无效的脚本路径'}), 400

    if create == 1:
        # 新建的话，只有 script/xxx.py 
        script_path = os.path.join(os.path.dirname(SCRIPT_DIR),script_path)
        
    validation = validate_kubectl_command(content)
    if not validation['valid']:
        return jsonify({
            'error': '脚本安全验证失败',
            'details': validation['errors']
        }), 400
    
    try:
        with open(script_path, 'w', encoding='utf-8') as f:
            f.write(content)
        return jsonify({'success': True, 'message': '保存成功'})
    except Exception as e:
        return jsonify({'error': f'保存脚本失败: {str(e)}'}), 500

@bp.route('api/script/delete', methods=['DELETE'])
def api_script_delete():
    data = request.get_json()
    script_path = data.get('path')
    
    if not script_path:
        return jsonify({'error': '缺少脚本路径参数'}), 400
    
    if not script_path.startswith(SCRIPT_DIR):
        return jsonify({'error': '无效的脚本路径'}), 400
    
    try:
        if os.path.exists(script_path):
            os.remove(script_path)
            return jsonify({'success': True, 'message': '删除成功'})
        else:
            return jsonify({'error': '脚本文件不存在'}), 404
    except Exception as e:
        return jsonify({'error': f'删除脚本失败: {str(e)}'}), 500

@bp.route('api/script/validate', methods=['POST'])
def api_script_validate():
    data = request.get_json()
    content = data.get('content', '')
    
    validation = validate_kubectl_command(content)
    return jsonify(validation)

@bp.route('api/execute', methods=['POST'])
def api_execute():
    data = request.get_json()
    script_path = data.get('scriptPath')
    parameters = data.get('parameters', {})
    
    if not script_path:
        return jsonify({'error': '缺少脚本路径参数'}), 400
    
    if not script_path.startswith(SCRIPT_DIR):
        return jsonify({'error': '无效的脚本路径'}), 400
    
    try:
        with open(script_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        validation = validate_kubectl_command(content)
        if not validation['valid']:
            return jsonify({
                'error': '脚本安全验证失败',
                'details': validation['errors']
            }), 400
        
        script_dir = os.path.dirname(script_path)
        script_name = os.path.basename(script_path)
        
        # 设置环境变量的方式
        env = os.environ.copy()
        for key, value in parameters.items():
            env[key] = str(value)
        # 使用  subprocess.run(env=env) 执行脚本

        # 设置 传参
        cmd = [sys.executable, script_path]
        for key, value in parameters.items():
            cmd.append(f"--{key}={value}")   
        
        result = subprocess.run(
            cmd,  # ✅ 直接传参，不用环境变量！
            cwd=script_dir,
            capture_output=True,
            text=True,
            timeout=EXECUTION_TIMEOUT,
            # env=env
        )
        
        if result.returncode != 0:
            return jsonify({
                'error': '脚本执行失败',
                'stderr': result.stderr,
                'returncode': result.returncode
            }), 500
        
        try:
            json_output = json.loads(result.stdout)
            return jsonify({
                'success': True,
                'output': json_output,
                'stdout': result.stdout
            })
        except json.JSONDecodeError:
            return jsonify({
                'error': '脚本输出不是有效的 JSON 格式',
                'stdout': result.stdout,
                'stderr': result.stderr
            }), 500
            
    except subprocess.TimeoutExpired:
        return jsonify({'error': f'执行超时（超过 {EXECUTION_TIMEOUT} 秒）'}), 500
    except FileNotFoundError:
        return jsonify({'error': f'脚本文件不存在: {script_path}'}), 400
    except Exception as e:
        return jsonify({'error': str(e)}), 500
