# 目标：统一加载config/*.yaml文件（路径相对utils）。
# 输出：dict结构config。

import yaml
import os

def load_config(config_name: str = 'default.yaml') -> dict:
    config_path = os.path.join(os.path.dirname(__file__), '..', 'config', config_name)
    with open(config_path, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)
    return config