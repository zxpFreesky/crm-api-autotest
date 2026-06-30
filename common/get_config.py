
import configparser
import os
import yaml

from .contants import conf_dir


class GetConfig:
    def __init__(self, file_name=None):
        if file_name is None:
            file_name = os.path.join(conf_dir, "test.ini")
        self.file_name = file_name
        self.conf = configparser.ConfigParser()
        self.conf.read(self.file_name, encoding="utf-8")

        self._load_users_config()

    def _load_users_config(self):
        users_file = os.path.join(conf_dir, "users.yaml")
        self._users_config = {}
        if os.path.exists(users_file):
            try:
                with open(users_file, 'r', encoding='utf-8') as f:
                    self._users_config = yaml.safe_load(f) or {}
            except Exception as e:
                print(f"[WARN] 加载账号配置失败: {e}")

    def get_value(self, section, item):
        return self.conf.get(section, item)

    def get_section(self, section):
        return dict(self.conf.items(section))

    def get_active_env(self):
        try:
            return self.conf.get("env", "active").strip()
        except (configparser.NoSectionError, configparser.NoOptionError):
            return "test"

    def get_host(self, env=None):
        """
        
          
        读取当前激活环境名称

        从 test.ini 的 [env] active 字段读取，默认 test
        
        读取当前激活环境名称
        """
        if env is None:
            env = self.get_active_env()
        return self.get_value("host", env).strip()

    def list_available_envs(self):
        return dict(self.conf.items("host"))

    def get_database_config(self):
        return self.get_section("database")

    def get_user_by_role(self, role_key=None):
        """
        获取指定角色的用户账号，统一从 config/users.yaml 读取

        :param role_key: 账号键名，如 'default'、'sale_account_1'、'assistant_account'
        :return: dict {'user': 'xxx', 'pwd': 'xxx', 'role': 'xxx'}
        """
        key = role_key or "default"
        if key in self._users_config:
            return self._users_config[key]
        raise KeyError(f"未找到账号配置: {key}, 可用账号: {list(self._users_config.keys())}")

    def list_available_users(self):
        return list(self._users_config.keys())


if __name__ == "__main__":
    cf = GetConfig()

    active = cf.get_active_env()
    host = cf.get_host()
    print(f"当前环境: {active}")
    print(f"Host: {host}")

    print("\n所有环境:")
    for env_name, env_url in cf.list_available_envs().items():
        marker = " <-- 当前" if env_name == active else ""
        print(f"  - {env_name}: {env_url}{marker}")

    print("\n可用账号 (config/users.yaml):")
    for account_key in cf.list_available_users():
        user = cf.get_user_by_role(account_key)
        print(f"  - {account_key}: {user['user']} ({user.get('role', 'unknown')})")
