import sqlite3
from datetime import datetime
from typing import List, Dict, Any, Optional
import os
import shutil
from config import config

class Database:
    """Класс для работы с базой данных SQLite"""
    
    def __init__(self, db_path=None):
        if db_path is None:
            db_path = config.get('DATABASE', 'db_path', 'inventory.db')
        self.db_path = db_path
        self.init_database()
    
    def get_connection(self):
        """Создание соединения с БД"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn
    
    def init_database(self):
        """Инициализация таблиц базы данных"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Таблица товаров
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS products (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    category TEXT,
                    supplier TEXT,
                    quantity INTEGER DEFAULT 0,
                    min_quantity INTEGER DEFAULT 0,
                    price REAL DEFAULT 0,
                    location TEXT,
                    qr_code TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Таблица складов
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS warehouses (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    address TEXT,
                    manager TEXT
                )
            ''')
            
            # Таблица инвентаризаций
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS inventories (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    product_id INTEGER,
                    warehouse_id INTEGER,
                    expected_quantity INTEGER,
                    actual_quantity INTEGER,
                    difference INTEGER,
                    status TEXT DEFAULT 'pending',
                    inventor_name TEXT,
                    date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    notes TEXT,
                    FOREIGN KEY (product_id) REFERENCES products(id),
                    FOREIGN KEY (warehouse_id) REFERENCES warehouses(id)
                )
            ''')
            
            # Таблица аудит-логов
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS audit_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_name TEXT,
                    action TEXT,
                    entity_type TEXT,
                    entity_id INTEGER,
                    old_values TEXT,
                    new_values TEXT,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Добавляем тестовый склад если пусто
            cursor.execute('SELECT COUNT(*) FROM warehouses')
            if cursor.fetchone()[0] == 0:
                cursor.execute('''
                    INSERT INTO warehouses (name, address, manager)
                    VALUES ('Основной склад', 'г. Курск, ул. Запольная, 47', 'Иванов И.И.')
                ''')
            
            # Добавляем тестовые товары
            cursor.execute('SELECT COUNT(*) FROM products')
            if cursor.fetchone()[0] == 0:
                test_products = [
                    ('Деталь А-123', 'Металл', 'ООО "Сталь"', 100, 20, 350.50, 'Стеллаж 1'),
                    ('Деталь Б-456', 'Пластик', 'ООО "Пластмасс"', 50, 10, 120.00, 'Стеллаж 2'),
                    ('Крепёж М8', 'Метизы', 'ООО "Крепёж"', 500, 100, 5.75, 'Стеллаж 3'),
                    ('Провод ПВ-3', 'Электро', 'ООО "Кабель"', 200, 50, 85.30, 'Стеллаж 4'),
                    ('Панель ПК-1', 'Пластик', 'ООО "Пластмасс"', 30, 10, 450.00, 'Стеллаж 5'),
                    ('Винт М6', 'Метизы', 'ООО "Крепёж"', 1000, 200, 2.50, 'Стеллаж 3'),
                ]
                for p in test_products:
                    cursor.execute('''
                        INSERT INTO products (name, category, supplier, quantity, min_quantity, price, location)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                    ''', p)
            
            conn.commit()
    
    # ----- CRUD ДЛЯ ТОВАРОВ -----
    
    def get_all_products(self) -> List[Dict]:
        """Получить все товары"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM products ORDER BY name')
            rows = cursor.fetchall()
            return [dict(row) for row in rows]
    
    def get_product_by_id(self, product_id: int) -> Optional[Dict]:
        """Получить товар по ID"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM products WHERE id = ?', (product_id,))
            row = cursor.fetchone()
            return dict(row) if row else None
    
    def add_product(self, data: Dict) -> int:
        """Добавить новый товар"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO products (name, category, supplier, quantity, min_quantity, price, location)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (data['name'], data.get('category', ''), data.get('supplier', ''),
                  data.get('quantity', 0), data.get('min_quantity', 0),
                  data.get('price', 0), data.get('location', '')))
            conn.commit()
            return cursor.lastrowid
    
    def update_product(self, product_id: int, data: Dict) -> bool:
        """Обновить товар"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE products 
                SET name = ?, category = ?, supplier = ?, quantity = ?, 
                    min_quantity = ?, price = ?, location = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            ''', (data['name'], data.get('category', ''), data.get('supplier', ''),
                  data.get('quantity', 0), data.get('min_quantity', 0),
                  data.get('price', 0), data.get('location', ''), product_id))
            conn.commit()
            return cursor.rowcount > 0
    
    def delete_product(self, product_id: int) -> bool:
        """Удалить товар"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('DELETE FROM products WHERE id = ?', (product_id,))
            conn.commit()
            return cursor.rowcount > 0
    
    def search_products(self, query: str) -> List[Dict]:
        """Поиск товаров"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT * FROM products 
                WHERE name LIKE ? OR category LIKE ? OR supplier LIKE ? OR location LIKE ?
            ''', (f'%{query}%', f'%{query}%', f'%{query}%', f'%{query}%'))
            rows = cursor.fetchall()
            return [dict(row) for row in rows]
    
    def get_low_stock_products(self) -> List[Dict]:
        """Товары с низким остатком"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT * FROM products 
                WHERE quantity <= min_quantity
                ORDER BY quantity
            ''')
            rows = cursor.fetchall()
            return [dict(row) for row in rows]
    
    # ----- РАБОТА С ИНВЕНТАРИЗАЦИЯМИ -----
    
    def create_inventory(self, data: Dict) -> int:
        """Создать запись инвентаризации"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            difference = data['actual_quantity'] - data['expected_quantity']
            
            cursor.execute('''
                INSERT INTO inventories (product_id, warehouse_id, expected_quantity, 
                                         actual_quantity, difference, status, inventor_name, notes)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (data['product_id'], data.get('warehouse_id', 1),
                  data['expected_quantity'], data['actual_quantity'],
                  difference,
                  data.get('status', 'completed'),
                  data.get('inventor_name', ''),
                  data.get('notes', '')))
            conn.commit()
            
            # Обновляем количество товара
            cursor.execute('''
                UPDATE products SET quantity = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            ''', (data['actual_quantity'], data['product_id']))
            conn.commit()
            
            return cursor.lastrowid
    
    def get_all_inventories(self) -> List[Dict]:
        """Получить все инвентаризации"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT i.*, p.name as product_name, w.name as warehouse_name
                FROM inventories i
                JOIN products p ON i.product_id = p.id
                JOIN warehouses w ON i.warehouse_id = w.id
                ORDER BY i.date DESC
            ''')
            rows = cursor.fetchall()
            return [dict(row) for row in rows]
    
    def get_inventory_by_id(self, inventory_id: int) -> Optional[Dict]:
        """Получить инвентаризацию по ID"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT i.*, p.name as product_name, w.name as warehouse_name
                FROM inventories i
                JOIN products p ON i.product_id = p.id
                JOIN warehouses w ON i.warehouse_id = w.id
                WHERE i.id = ?
            ''', (inventory_id,))
            row = cursor.fetchone()
            return dict(row) if row else None
    
    # ----- АУДИТ-ЛОГ -----
    
    def add_audit_log(self, user_name: str, action: str, entity_type: str, 
                      entity_id: int, old_values: str = '', new_values: str = ''):
        """Добавить запись в аудит-лог"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO audit_log (user_name, action, entity_type, entity_id, old_values, new_values)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (user_name, action, entity_type, entity_id, old_values, new_values))
            conn.commit()
    
    def get_audit_log(self, limit: int = 100) -> List[Dict]:
        """Получить аудит-лог"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT * FROM audit_log 
                ORDER BY timestamp DESC 
                LIMIT ?
            ''', (limit,))
            rows = cursor.fetchall()
            return [dict(row) for row in rows]
    
    def clear_audit_log(self) -> bool:
        """Очистить аудит-лог"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('DELETE FROM audit_log')
            conn.commit()
            return True
    
    # ----- РАБОТА СО СКЛАДАМИ -----
    
    def get_all_warehouses(self) -> List[Dict]:
        """Получить все склады"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM warehouses')
            rows = cursor.fetchall()
            return [dict(row) for row in rows]
    
    def add_warehouse(self, data: Dict) -> int:
        """Добавить склад"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO warehouses (name, address, manager)
                VALUES (?, ?, ?)
            ''', (data['name'], data.get('address', ''), data.get('manager', '')))
            conn.commit()
            return cursor.lastrowid
    
    # ----- СТАТИСТИКА И ОТЧЁТЫ -----
    
    def get_statistics(self) -> Dict:
        """Получить статистику по системе"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            stats = {}
            
            cursor.execute('SELECT COUNT(*) FROM products')
            stats['total_products'] = cursor.fetchone()[0]
            
            cursor.execute('SELECT COUNT(*) FROM inventories')
            stats['total_inventories'] = cursor.fetchone()[0]
            
            cursor.execute('''
                SELECT COUNT(*) FROM inventories 
                WHERE difference != 0
            ''')
            stats['discrepancies'] = cursor.fetchone()[0]
            
            cursor.execute('''
                SELECT SUM(quantity * price) FROM products
            ''')
            stats['total_value'] = cursor.fetchone()[0] or 0
            
            cursor.execute('''
                SELECT COUNT(*) FROM products 
                WHERE quantity <= min_quantity
            ''')
            stats['low_stock_count'] = cursor.fetchone()[0]
            
            return stats
    
    def get_products_by_category(self) -> Dict[str, int]:
        """Количество товаров по категориям"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT category, COUNT(*) as count 
                FROM products 
                GROUP BY category
            ''')
            rows = cursor.fetchall()
            return {row['category']: row['count'] for row in rows}
    
    def get_inventory_discrepancies(self) -> List[Dict]:
        """Получить все расхождения по инвентаризациям"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT i.*, p.name as product_name
                FROM inventories i
                JOIN products p ON i.product_id = p.id
                WHERE i.difference != 0
                ORDER BY ABS(i.difference) DESC
            ''')
            rows = cursor.fetchall()
            return [dict(row) for row in rows]
    
    # ----- БЭКАП -----
    
    def backup_database(self) -> str:
        """Создать резервную копию базы данных"""
        backup_folder = config.get('DATABASE', 'backup_folder', './backups/')
        os.makedirs(backup_folder, exist_ok=True)
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_path = os.path.join(backup_folder, f'inventory_backup_{timestamp}.db')
        
        shutil.copy2(self.db_path, backup_path)
        return backup_path

# Создаём глобальный объект БД
db = Database()