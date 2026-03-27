import os
import json
from flask import Flask, render_template

app = Flask(__name__)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

def register_blueprints():
    modules_dir = os.path.join(BASE_DIR, 'modules')
    if not os.path.exists(modules_dir):
        return
    
    for module_name in os.listdir(modules_dir):
        module_path = os.path.join(modules_dir, module_name)
        if os.path.isdir(module_path):
            for sub_module in os.listdir(module_path):
                sub_path = os.path.join(module_path, sub_module)
                if os.path.isdir(sub_path):
                    app_file = os.path.join(sub_path, 'app.py')
                    if os.path.exists(app_file):
                        try:
                            import importlib.util
                            spec = importlib.util.spec_from_file_location(
                                f"modules.{module_name}.{sub_module}",
                                app_file
                            )
                            module = importlib.util.module_from_spec(spec)
                            spec.loader.exec_module(module)
                            
                            if hasattr(module, 'bp'):
                                url_prefix = f'/modules/{module_name}/{sub_module}'
                                app.register_blueprint(module.bp, url_prefix=url_prefix)
                                print(f"Registered blueprint: {url_prefix}")
                            else:
                                print(f"Module {module_name}/{sub_module} does not have a Blueprint")
    
                        except Exception as e:
                            print(f"Failed to load module {module_name}/{sub_module}: {e}")

register_blueprints()

def load_config():
    config_path = os.path.join(BASE_DIR, 'config.json')
    with open(config_path, 'r', encoding='utf-8') as f:
        return json.load(f)

@app.route('/')
def index():
    config = load_config()
    return render_template('index.html', config=config)

if __name__ == '__main__':
    print(f'Quick Tool 运行在 http://localhost:5000')
    app.run(host='0.0.0.0', port=5000, debug=False)
