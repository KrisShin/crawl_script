import yaml
from pathlib import Path
from typing import Any, Dict, Optional

from common.settings import CONFIG_PATH


class ConfigLoader(object):
    """
    YAML 配置加载器（单例模式）
    用法：
    >>> cfg = ConfigLoader.get_instance()
    >>> mysql_host = cfg.database.mysql.host
    """

    _instance = None

    def __new__(cls, config_path: str | Path = CONFIG_PATH):
        if not cls._instance:
            cls._instance = super().__new__(cls)
            cls._instance._init_config(config_path)
        return cls._instance

    def _init_config(self, config_path: Path):
        if not config_path or not config_path.exists():
            raise FileNotFoundError("config.yaml not found in default locations")

        try:
            with open(config_path, 'r') as f:
                raw_config = yaml.safe_load(f)
                self._config = self._dict_to_object(raw_config)
        except yaml.YAMLError as e:
            raise ValueError(f"Invalid YAML format: {str(e)}")
        except Exception as e:
            raise RuntimeError(f"Failed to load config: {str(e)}")

    class _ConfigNode:
        """配置节点包装类"""

        def __init__(self, data: Dict[str, Any]):
            for key, value in data.items():
                if isinstance(value, dict):
                    setattr(self, key, ConfigLoader._ConfigNode(value))
                else:
                    setattr(self, key, value)

        def __repr__(self):
            return str(self.__dict__)

    @staticmethod
    def _dict_to_object(data: Dict) -> _ConfigNode:
        """递归转换字典为对象"""
        return ConfigLoader._ConfigNode(data)

    @property
    def database(self):
        """访问数据库配置的快捷方式"""
        return self._config.database

    @property
    def oss(self):
        """访问 OSS 配置的快捷方式"""
        if not hasattr(self._config, 'oss'):
            raise AttributeError("config.yaml 中缺少 'oss' 配置节")
        return self._config.oss

    @property
    def hunyuan(self):
        """访问 OSS 配置的快捷方式"""
        if not hasattr(self._config, 'hunyuan'):
            raise AttributeError("config.yaml 中缺少 'hunyuan' 配置节")
        return self._config.hunyuan

    @property
    def charging_alliance(self):
        """访问 OSS 配置的快捷方式"""
        if not hasattr(self._config, 'charging_alliance'):
            raise AttributeError("config.yaml 中缺少 'charging_alliance' 配置节")
        return self._config.charging_alliance

    def get(self, key_path: str, default: Any = None) -> Optional[Any]:
        """
        通过点分路径获取配置值
        示例：get('database.mysql.host')
        """
        keys = key_path.split('.')
        node = self._config

        for key in keys:
            if not hasattr(node, key):
                return default
            node = getattr(node, key)
        return node


# 单例实例访问入口
def get_config() -> ConfigLoader:
    return ConfigLoader()
