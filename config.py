import configparser
import os
import hashlib
from typing import Dict, Any, Optional

class Config:
    """Класс для работы с конфигурационным файлом"""
    
    def __init__(self, config_path="config.ini"):
        self.config_path = config_path
        self.config = configparser.ConfigParser(allow_no_value=True)
        self._current_user = None
        self.load_config()
    
    def load_config(self):
        """Загрузить конфигурацию из файла"""
        if os.path.exists(self.config_path):
            self.config.read(self.config_path, encoding='utf-8')
        else:
            self._create_default_config()
    
    def _create_default_config(self):
        """Создать конфигурацию по умолчанию, если файл отсутствует"""
        self.config['APP'] = {
            'company_name': 'АО "Авиаавтоматика"',
            'version': '1.0.0',
            'app_title': 'Система инвентаризации завода',
            'window_width': '1100',
            'window_height': '700',
            'theme': 'light',
            'language': 'ru',
            'debug_mode': 'False'
        }
        
        self.config['DATABASE'] = {
            'db_path': 'inventory.db',
            'backup_on_exit': 'True',
            'backup_folder': './backups/',
            'max_backups': '10'
        }
        
        self.config['AUTH'] = {
            'require_auth': 'True',
            'session_timeout': '30',
            'max_login_attempts': '3',
            'block_duration': '5',
            'allow_registration': 'False',
            'password_min_length': '6',
            'password_require_numbers': 'True',
            'password_require_special': 'False'
        }
        
        self.config['USERS'] = {
            'admin': 'admin123|admin|Администратор Системы|True',
            'user': 'user123|warehouse_worker|Иванов Иван Иванович|True',
            'manager': 'manager123|warehouse_manager|Петров Сергей Николаевич|True',
            'auditor': 'auditor123|auditor|Сидорова Анна Михайловна|True',
            'viewer': 'viewer123|viewer|Козлов Виктор Дмитриевич|False'
        }
        
        self.save_config()
    
    def save_config(self):
        """Сохранить конфигурацию в файл"""
        with open(self.config_path, 'w', encoding='utf-8') as f:
            self.config.write(f)
    
    def get(self, section, key, default=None):
        """Получить значение из конфигурации"""
        try:
            return self.config.get(section, key)
        except (configparser.NoSectionError, configparser.NoOptionError):
            return default
    
    def get_bool(self, section, key, default=False):
        """Получить булево значение"""
        value = self.get(section, key)
        if value is None:
            return default
        return value.lower() in ('true', '1', 'yes', 'on')
    
    def get_int(self, section, key, default=0):
        """Получить целочисленное значение"""
        value = self.get(section, key)
        if value is None:
            return default
        try:
            return int(value)
        except ValueError:
            return default
    
    def get_float(self, section, key, default=0.0):
        """Получить число с плавающей точкой"""
        value = self.get(section, key)
        if value is None:
            return default
        try:
            return float(value)
        except ValueError:
            return default
    
    def get_list(self, section, key, default=[], delimiter=','):
        """Получить список значений"""
        value = self.get(section, key)
        if value is None:
            return default
        return [item.strip() for item in value.split(delimiter) if item.strip()]
    
    def set(self, section, key, value):
        """Установить значение в конфигурации"""
        if not self.config.has_section(section):
            self.config.add_section(section)
        self.config.set(section, key, str(value))
        self.save_config()
    
    # ----- УПРАВЛЕНИЕ ПОЛЬЗОВАТЕЛЯМИ -----
    
    def get_users(self) -> Dict[str, Dict]:
        """Получить всех пользователей из конфига"""
        users = {}
        if self.config.has_section('USERS'):
            for login, data in self.config.items('USERS'):
                parts = data.split('|')
                if len(parts) == 4:
                    users[login] = {
                        'password': parts[0],
                        'role': parts[1],
                        'full_name': parts[2],
                        'active': parts[3].lower() == 'true'
                    }
        return users
    
    def get_user(self, login: str) -> Optional[Dict]:
        """Получить информацию о пользователе по логину"""
        users = self.get_users()
        return users.get(login)
    
    def add_user(self, login: str, password: str, role: str, full_name: str, active: bool = True):
        """Добавить нового пользователя"""
        if not self.config.has_section('USERS'):
            self.config.add_section('USERS')
        
        if self.get_bool('SECURITY', 'encrypt_passwords', False):
            password = self._hash_password(password)
        
        user_data = f"{password}|{role}|{full_name}|{str(active)}"
        self.config.set('USERS', login, user_data)
        self.save_config()
    
    def update_user(self, login: str, password: str = None, role: str = None, 
                    full_name: str = None, active: bool = None):
        """Обновить данные пользователя"""
        user = self.get_user(login)
        if not user:
            return False
        
        new_password = password if password else user['password']
        if password and self.get_bool('SECURITY', 'encrypt_passwords', False):
            new_password = self._hash_password(password)
        
        new_role = role if role else user['role']
        new_full_name = full_name if full_name else user['full_name']
        new_active = active if active is not None else user['active']
        
        user_data = f"{new_password}|{new_role}|{new_full_name}|{str(new_active)}"
        self.config.set('USERS', login, user_data)
        self.save_config()
        return True
    
    def delete_user(self, login: str) -> bool:
        """Удалить пользователя"""
        if self.config.has_section('USERS'):
            if self.config.remove_option('USERS', login):
                self.save_config()
                return True
        return False
    
    def check_password(self, login: str, password: str) -> bool:
        """Проверить пароль пользователя"""
        user = self.get_user(login)
        if not user or not user['active']:
            return False
        
        stored_password = user['password']
        
        if self.get_bool('SECURITY', 'encrypt_passwords', False):
            password = self._hash_password(password)
        
        return password == stored_password
    
    def _hash_password(self, password: str) -> str:
        """Хэширование пароля"""
        salt = self.get('SECURITY', 'salt', 'my_salt_key_123')
        return hashlib.sha256((salt + password).encode()).hexdigest()
    
    # ----- ПРОВЕРКА ПРАВ ДОСТУПА -----
    
    def has_permission(self, login: str, permission: str) -> bool:
        """Проверить, есть ли у пользователя разрешение"""
        user = self.get_user(login)
        if not user or not user['active']:
            return False
        
        role = user['role']
        section = f'ROLES:{role}'
        if self.config.has_section(section):
            return self.get_bool(section, permission, False)
        return False
    
    def get_role_permissions(self, role: str) -> Dict[str, bool]:
        """Получить все права для роли"""
        permissions = {}
        section = f'ROLES:{role}'
        if self.config.has_section(section):
            for key, value in self.config.items(section):
                permissions[key] = value.lower() in ('true', '1', 'yes', 'on')
        return permissions
    
    def get_current_user(self) -> Optional[Dict]:
        """Получить текущего авторизованного пользователя"""
        return self._current_user
    
    def set_current_user(self, login: str):
        """Установить текущего пользователя"""
        self._current_user = self.get_user(login)
    
    def is_authenticated(self) -> bool:
        """Проверить, включена ли авторизация"""
        return self.get_bool('AUTH', 'require_auth', True)
    
    def get_ui_color(self, color_name: str, default: str = '#ffffff') -> str:
        """Получить цвет из UI-настроек"""
        return self.get('UI', color_name, default)
    
    def get_export_formats(self) -> list:
        """Получить доступные форматы экспорта"""
        formats = self.get('EXPORT', 'available_formats', 'csv, xlsx, json')
        return [f.strip() for f in formats.split(',')]

# Создаём глобальный объект конфигурации
config = Config()