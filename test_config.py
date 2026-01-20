from utils.config_loader import load_config

config = load_config('default.yaml')
print(config['candlestick']['long_shadow_ratio'])  # 应该输出 2.0