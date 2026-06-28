import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import json
from datetime import datetime
from config import config
from database import db
from utils import utils

class InventoryApp:
    """Главное окно приложения"""
    
    def __init__(self, root, username, on_logout=None):
        self.root = root
        self.username = username
        self.on_logout = on_logout
        
        # Загружаем настройки
        self.company_name = config.get('APP', 'company_name', 'Система инвентаризации')
        self.window_width = config.get_int('APP', 'window_width', 1100)
        self.window_height = config.get_int('APP', 'window_height', 700)
        
        # Настройка окна
        self.root.title(self.company_name)
        self.root.geometry(f"{self.window_width}x{self.window_height}")
        self.root.resizable(True, True)
        
        # Получаем информацию о пользователе
        self.user_info = config.get_user(username) if username else None
        self.user_role = self.user_info['role'] if self.user_info else 'viewer'
        self.user_fullname = self.user_info['full_name'] if self.user_info else 'Гость'
        
        # Создаём интерфейс
        self.create_widgets()
        self.load_products()
        self.update_status_bar()
        
        # Обработка закрытия
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)
    
    def create_widgets(self):
        """Создание всех виджетов"""
        
        # ----- ВЕРХНИЙ БАР -----
        top_frame = tk.Frame(self.root, bg='#2c3e50', height=60)
        top_frame.pack(fill='x')
        top_frame.pack_propagate(False)
        
        tk.Label(top_frame, text=self.company_name, font=('Segoe UI', 14, 'bold'),
                bg='#2c3e50', fg='white').pack(side='left', padx=20, pady=15)
        
        # Информация о пользователе
        user_text = f"👤 {self.user_fullname} ({self.user_role})"
        tk.Label(top_frame, text=user_text, font=('Segoe UI', 10),
                bg='#2c3e50', fg='#bdc3c7').pack(side='right', padx=10, pady=15)
        
        # Кнопка выхода
        tk.Button(top_frame, text="🚪 Выйти", command=self.logout,
                 bg='#e74c3c', fg='white', font=('Segoe UI', 9),
                 padx=10).pack(side='right', padx=10, pady=15)
        
        # ----- ПАНЕЛЬ ИНСТРУМЕНТОВ -----
        toolbar = tk.Frame(self.root, bg='#ecf0f1')
        toolbar.pack(fill='x', pady=5)
        
        # Кнопки (с проверкой прав)
        button_configs = [
            ('➕ Добавить', self.add_product, 'can_add_products'),
            ('✏️ Редактировать', self.edit_product, 'can_edit_products'),
            ('🗑️ Удалить', self.delete_product, 'can_delete_products'),
            ('📦 Инвентаризация', self.do_inventory, 'can_create_inventory'),
            ('📊 Отчёты', self.show_reports, 'can_view_reports'),
            ('📋 Аудит', self.show_audit, 'can_view_audit'),
        ]
        
        self.buttons = {}
        for text, command, permission in button_configs:
            btn = tk.Button(toolbar, text=text, command=command,
                           bg='#3498db', fg='white', font=('Segoe UI', 9, 'bold'),
                           padx=10, pady=5)
            btn.pack(side='left', padx=5, pady=5)
            self.buttons[permission] = btn
            
            # Блокируем, если нет прав
            if not self.has_permission(permission):
                btn.config(state='disabled')
        
        # ----- ПОИСК -----
        search_frame = tk.Frame(self.root, bg='#ecf0f1')
        search_frame.pack(fill='x', pady=5)
        
        tk.Label(search_frame, text="🔍 Поиск:", bg='#ecf0f1',
                font=('Segoe UI', 10)).pack(side='left', padx=10)
        
        self.search_var = tk.StringVar()
        self.search_entry = tk.Entry(search_frame, textvariable=self.search_var,
                                    font=('Segoe UI', 10), width=30)
        self.search_entry.pack(side='left', padx=5)
        self.search_entry.bind('<Return>', lambda e: self.search_products())
        
        tk.Button(search_frame, text="Найти", command=self.search_products,
                 bg='#2ecc71', fg='white', font=('Segoe UI', 9),
                 padx=10).pack(side='left', padx=5)
        
        tk.Button(search_frame, text="Сбросить", command=self.reset_search,
                 bg='#95a5a6', fg='white', font=('Segoe UI', 9),
                 padx=10).pack(side='left', padx=5)
        
        # ----- ТАБЛИЦА ТОВАРОВ -----
        table_frame = tk.Frame(self.root)
        table_frame.pack(fill='both', expand=True, padx=10, pady=5)
        
        # Scrollbars
        scroll_y = ttk.Scrollbar(table_frame)
        scroll_y.pack(side='right', fill='y')
        
        scroll_x = ttk.Scrollbar(table_frame, orient='horizontal')
        scroll_x.pack(side='bottom', fill='x')
        
        # Таблица
        columns = ('id', 'name', 'category', 'supplier', 'quantity', 'min_quantity', 'price', 'location')
        self.tree = ttk.Treeview(table_frame, columns=columns, show='headings',
                                yscrollcommand=scroll_y.set, xscrollcommand=scroll_x.set)
        
        scroll_y.config(command=self.tree.yview)
        scroll_x.config(command=self.tree.xview)
        
        # Настройка колонок
        column_headers = {
            'id': 'ID',
            'name': 'Название',
            'category': 'Категория',
            'supplier': 'Поставщик',
            'quantity': 'Кол-во',
            'min_quantity': 'Мин.',
            'price': 'Цена (₽)',
            'location': 'Место'
        }
        
        column_widths = {'id': 50, 'name': 200, 'category': 120, 'supplier': 150,
                        'quantity': 80, 'min_quantity': 70, 'price': 100, 'location': 150}
        
        for col in columns:
            self.tree.heading(col, text=column_headers.get(col, col))
            self.tree.column(col, width=column_widths.get(col, 100), anchor='center')
        
        self.tree.pack(fill='both', expand=True)
        
        # Привязываем двойной клик для редактирования
        self.tree.bind('<Double-Button-1>', lambda e: self.edit_product())
        
        # ----- СТРОКА СТАТУСА -----
        self.status_frame = tk.Frame(self.root, bg='#2c3e50', height=30)
        self.status_frame.pack(fill='x', side='bottom')
        self.status_frame.pack_propagate(False)
        
        self.status_label = tk.Label(self.status_frame, text="Готово", 
                                     bg='#2c3e50', fg='white',
                                     font=('Segoe UI', 9))
        self.status_label.pack(side='left', padx=10, pady=5)
        
        self.stats_label = tk.Label(self.status_frame, text="",
                                    bg='#2c3e50', fg='#bdc3c7',
                                    font=('Segoe UI', 9))
        self.stats_label.pack(side='right', padx=10, pady=5)
    
    def has_permission(self, permission):
        """Проверить право доступа"""
        if not self.username:
            return True
        return config.has_permission(self.username, permission)
    
    def load_products(self, products=None):
        """Загрузить товары в таблицу"""
        # Очищаем таблицу
        for item in self.tree.get_children():
            self.tree.delete(item)
        
        if products is None:
            products = db.get_all_products()
        
        for product in products:
            self.tree.insert('', 'end', values=(
                product['id'],
                product['name'],
                product.get('category', ''),
                product.get('supplier', ''),
                product['quantity'],
                product.get('min_quantity', 0),
                f"{product.get('price', 0):.2f}",
                product.get('location', '')
            ))
        
        self.update_status()
    
    def search_products(self):
        """Поиск товаров"""
        query = self.search_var.get().strip()
        if query:
            results = db.search_products(query)
            self.load_products(results)
            self.status_label.config(text=f"Найдено: {len(results)} записей")
        else:
            self.load_products()
            self.status_label.config(text="Показаны все товары")
    
    def reset_search(self):
        """Сброс поиска"""
        self.search_var.set('')
        self.load_products()
        self.status_label.config(text="Показаны все товары")
    
    def get_selected_product(self):
        """Получить выбранный товар"""
        selection = self.tree.selection()
        if not selection:
            messagebox.showwarning("Предупреждение", "Выберите товар")
            return None
        
        item = self.tree.item(selection[0])
        product_id = item['values'][0]
        return db.get_product_by_id(product_id)
    
    def add_product(self):
        """Добавить товар"""
        window = ProductWindow(self.root, self.username, mode='add')
        self.root.wait_window(window)
        self.load_products()
        self.update_status()
    
    def edit_product(self):
        """Редактировать товар"""
        product = self.get_selected_product()
        if not product:
            return
        
        window = ProductWindow(self.root, self.username, mode='edit', product=product)
        self.root.wait_window(window)
        self.load_products()
        self.update_status()
    
    def delete_product(self):
        """Удалить товар"""
        product = self.get_selected_product()
        if not product:
            return
        
        if messagebox.askyesno("Подтверждение", 
                               f"Удалить товар '{product['name']}'?"):
            db.delete_product(product['id'])
            db.add_audit_log(self.username, 'delete', 'product', 
                           product['id'], json.dumps(product))
            self.load_products()
            self.update_status()
            self.status_label.config(text=f"Товар '{product['name']}' удалён")
    
    def do_inventory(self):
        """Провести инвентаризацию"""
        product = self.get_selected_product()
        if not product:
            return
        
        window = InventoryWindow(self.root, self.username, product)
        self.root.wait_window(window)
        self.load_products()
        self.update_status()
        self.status_label.config(text="Инвентаризация завершена")
    
    def show_reports(self):
        """Показать отчёты"""
        window = ReportsWindow(self.root)
        self.root.wait_window(window)
    
    def show_audit(self):
        """Показать аудит-лог"""
        window = AuditWindow(self.root)
        self.root.wait_window(window)
    
    def update_status(self):
        """Обновить строку статуса"""
        stats = db.get_statistics()
        self.stats_label.config(
            text=f"Товаров: {stats['total_products']} | "
                 f"Низкий остаток: {stats['low_stock_count']} | "
                 f"Общая стоимость: {utils.format_currency(stats['total_value'])}"
        )
    
    def update_status_bar(self):
        """Обновить верхнюю панель"""
        pass
    
    def logout(self):
        """Выход из текущего пользователя"""
        if messagebox.askyesno("Выход", "Вы уверены, что хотите выйти из системы?"):
            # Вызываем callback для перехода на авторизацию
            if self.on_logout:
                self.on_logout()

    def on_close(self):
        """Закрытие приложения - полный выход"""
        if messagebox.askyesno("Выход", "Вы уверены, что хотите закрыть приложение?"):
            self.root.quit()
            self.root.destroy()


# ----- ОКНО ДОБАВЛЕНИЯ/РЕДАКТИРОВАНИЯ ТОВАРА -----

class ProductWindow(tk.Toplevel):
    """Окно добавления/редактирования товара"""
    
    def __init__(self, parent, username, mode='add', product=None):
        super().__init__(parent)
        self.parent = parent
        self.username = username
        self.mode = mode
        self.product = product
        
        title = "Добавление товара" if mode == 'add' else "Редактирование товара"
        self.title(title)
        self.geometry("500x500")
        self.resizable(False, False)
        self.grab_set()
        
        self.create_widgets()
        self.center_window()
    
    def create_widgets(self):
        """Создать виджеты"""
        main_frame = tk.Frame(self, padx=30, pady=20)
        main_frame.pack(fill='both', expand=True)
        
        # Поля ввода
        fields = [
            ('name', 'Название:', 'entry'),
            ('category', 'Категория:', 'entry'),
            ('supplier', 'Поставщик:', 'entry'),
            ('quantity', 'Количество:', 'entry'),
            ('min_quantity', 'Минимальный остаток:', 'entry'),
            ('price', 'Цена (₽):', 'entry'),
            ('location', 'Место хранения:', 'entry'),
        ]
        
        self.entries = {}
        for row, (key, label, type_) in enumerate(fields):
            tk.Label(main_frame, text=label, font=('Segoe UI', 10)).grid(row=row, column=0, sticky='w', pady=5)
            
            if type_ == 'entry':
                entry = tk.Entry(main_frame, font=('Segoe UI', 10), width=35)
                entry.grid(row=row, column=1, pady=5, padx=10)
                self.entries[key] = entry
        
        # Заполняем данные при редактировании
        if self.mode == 'edit' and self.product:
            self.entries['name'].insert(0, self.product.get('name', ''))
            self.entries['category'].insert(0, self.product.get('category', ''))
            self.entries['supplier'].insert(0, self.product.get('supplier', ''))
            self.entries['quantity'].insert(0, str(self.product.get('quantity', 0)))
            self.entries['min_quantity'].insert(0, str(self.product.get('min_quantity', 0)))
            self.entries['price'].insert(0, str(self.product.get('price', 0)))
            self.entries['location'].insert(0, self.product.get('location', ''))
        
        # Кнопки
        button_frame = tk.Frame(main_frame)
        button_frame.grid(row=len(fields), column=0, columnspan=2, pady=20)
        
        btn_text = "Сохранить" if self.mode == 'add' else "Обновить"
        tk.Button(button_frame, text=btn_text, command=self.save,
                 bg='#3498db', fg='white', font=('Segoe UI', 10, 'bold'),
                 padx=20, pady=5).pack(side='left', padx=10)
        
        tk.Button(button_frame, text="Отмена", command=self.destroy,
                 bg='#95a5a6', fg='white', font=('Segoe UI', 10),
                 padx=20, pady=5).pack(side='left', padx=10)
    
    def center_window(self):
        """Центрирование окна"""
        self.update_idletasks()
        width = self.winfo_width()
        height = self.winfo_height()
        x = (self.winfo_screenwidth() // 2) - (width // 2)
        y = (self.winfo_screenheight() // 2) - (height // 2)
        self.geometry(f'{width}x{height}+{x}+{y}')
    
    def save(self):
        """Сохранить товар"""
        data = {key: entry.get().strip() for key, entry in self.entries.items()}
        
        # Проверка обязательных полей
        if not data['name']:
            messagebox.showerror("Ошибка", "Введите название товара")
            return
        
        # Преобразование чисел
        try:
            data['quantity'] = int(data['quantity']) if data['quantity'] else 0
            data['min_quantity'] = int(data['min_quantity']) if data['min_quantity'] else 0
            data['price'] = float(data['price']) if data['price'] else 0
        except ValueError:
            messagebox.showerror("Ошибка", "Проверьте правильность ввода чисел")
            return
        
        if self.mode == 'add':
            product_id = db.add_product(data)
            db.add_audit_log(self.username, 'add', 'product', product_id, '', json.dumps(data))
            messagebox.showinfo("Успех", "Товар добавлен")
        else:
            db.update_product(self.product['id'], data)
            db.add_audit_log(self.username, 'edit', 'product', 
                           self.product['id'], json.dumps(self.product), json.dumps(data))
            messagebox.showinfo("Успех", "Товар обновлён")
        
        self.destroy()


# ----- ОКНО ИНВЕНТАРИЗАЦИИ -----

class InventoryWindow(tk.Toplevel):
    """Окно проведения инвентаризации"""
    
    def __init__(self, parent, username, product):
        super().__init__(parent)
        self.parent = parent
        self.username = username
        self.product = product
        
        self.title("Проведение инвентаризации")
        self.geometry("450x350")
        self.resizable(False, False)
        self.grab_set()
        
        self.create_widgets()
        self.center_window()
    
    def create_widgets(self):
        """Создать виджеты"""
        main_frame = tk.Frame(self, padx=30, pady=20)
        main_frame.pack(fill='both', expand=True)
        
        # Информация о товаре
        tk.Label(main_frame, text="Товар:", font=('Segoe UI', 10, 'bold')).grid(row=0, column=0, sticky='w', pady=5)
        tk.Label(main_frame, text=self.product['name'], font=('Segoe UI', 10)).grid(row=0, column=1, sticky='w', pady=5)
        
        tk.Label(main_frame, text="Ожидаемое кол-во:", font=('Segoe UI', 10, 'bold')).grid(row=1, column=0, sticky='w', pady=5)
        tk.Label(main_frame, text=str(self.product['quantity']), font=('Segoe UI', 10)).grid(row=1, column=1, sticky='w', pady=5)
        
        # Фактическое количество
        tk.Label(main_frame, text="Фактическое кол-во:", font=('Segoe UI', 10)).grid(row=2, column=0, sticky='w', pady=10)
        self.actual_var = tk.StringVar()
        self.actual_entry = tk.Entry(main_frame, textvariable=self.actual_var, font=('Segoe UI', 10), width=20)
        self.actual_entry.grid(row=2, column=1, sticky='w', pady=10)
        
        # Инвентаризатор
        tk.Label(main_frame, text="Инвентаризатор:", font=('Segoe UI', 10)).grid(row=3, column=0, sticky='w', pady=5)
        self.inventor_entry = tk.Entry(main_frame, font=('Segoe UI', 10), width=20)
        self.inventor_entry.grid(row=3, column=1, sticky='w', pady=5)
        
        # Примечание
        tk.Label(main_frame, text="Примечание:", font=('Segoe UI', 10)).grid(row=4, column=0, sticky='w', pady=5)
        self.notes_entry = tk.Entry(main_frame, font=('Segoe UI', 10), width=20)
        self.notes_entry.grid(row=4, column=1, sticky='w', pady=5)
        
        # Кнопки
        button_frame = tk.Frame(main_frame)
        button_frame.grid(row=5, column=0, columnspan=2, pady=20)
        
        tk.Button(button_frame, text="Сохранить", command=self.save,
                 bg='#3498db', fg='white', font=('Segoe UI', 10, 'bold'),
                 padx=20, pady=5).pack(side='left', padx=10)
        
        tk.Button(button_frame, text="Отмена", command=self.destroy,
                 bg='#95a5a6', fg='white', font=('Segoe UI', 10),
                 padx=20, pady=5).pack(side='left', padx=10)
    
    def center_window(self):
        """Центрирование окна"""
        self.update_idletasks()
        width = self.winfo_width()
        height = self.winfo_height()
        x = (self.winfo_screenwidth() // 2) - (width // 2)
        y = (self.winfo_screenheight() // 2) - (height // 2)
        self.geometry(f'{width}x{height}+{x}+{y}')
    
    def save(self):
        """Сохранить инвентаризацию"""
        try:
            actual = int(self.actual_var.get().strip())
        except ValueError:
            messagebox.showerror("Ошибка", "Введите корректное количество")
            return
        
        inventor = self.inventor_entry.get().strip()
        notes = self.notes_entry.get().strip()
        
        data = {
            'product_id': self.product['id'],
            'warehouse_id': 1,
            'expected_quantity': self.product['quantity'],
            'actual_quantity': actual,
            'inventor_name': inventor or self.username,
            'notes': notes
        }
        
        db.create_inventory(data)
        db.add_audit_log(self.username, 'inventory', 'inventory', 
                        self.product['id'], 
                        f"Ожидалось: {data['expected_quantity']}", 
                        f"Фактически: {actual}")
        
        messagebox.showinfo("Успех", "Инвентаризация завершена")
        self.destroy()


# ----- ОКНО ОТЧЁТОВ -----

class ReportsWindow(tk.Toplevel):
    """Окно отчётов и аналитики"""
    
    def __init__(self, parent):
        super().__init__(parent)
        self.parent = parent
        
        self.title("Отчёты и аналитика")
        self.geometry("800x600")
        self.resizable(True, True)
        self.grab_set()
        
        self.create_widgets()
        self.center_window()
        self.load_reports()
    
    def create_widgets(self):
        """Создать виджеты"""
        # Верхняя панель
        toolbar = tk.Frame(self, bg='#ecf0f1')
        toolbar.pack(fill='x', pady=5)
        
        tk.Button(toolbar, text="📊 Товары по категориям", command=self.show_categories,
                 bg='#3498db', fg='white', font=('Segoe UI', 9),
                 padx=10, pady=5).pack(side='left', padx=5)
        
        tk.Button(toolbar, text="📉 Расхождения", command=self.show_discrepancies,
                 bg='#e74c3c', fg='white', font=('Segoe UI', 9),
                 padx=10, pady=5).pack(side='left', padx=5)
        
        tk.Button(toolbar, text="📈 Общая стоимость", command=self.show_value,
                 bg='#2ecc71', fg='white', font=('Segoe UI', 9),
                 padx=10, pady=5).pack(side='left', padx=5)
        
        tk.Button(toolbar, text="📥 Экспорт в CSV", command=self.export_csv,
                 bg='#f39c12', fg='white', font=('Segoe UI', 9),
                 padx=10, pady=5).pack(side='left', padx=5)
        
        # Область для графиков
        self.chart_frame = tk.Frame(self, bg='white')
        self.chart_frame.pack(fill='both', expand=True, padx=10, pady=10)
    
    def center_window(self):
        """Центрирование окна"""
        self.update_idletasks()
        width = self.winfo_width()
        height = self.winfo_height()
        x = (self.winfo_screenwidth() // 2) - (width // 2)
        y = (self.winfo_screenheight() // 2) - (height // 2)
        self.geometry(f'{width}x{height}+{x}+{y}')
    
    def load_reports(self):
        """Загрузить отчёты по умолчанию"""
        self.show_categories()
    
    def clear_chart_frame(self):
        """Очистить область графиков"""
        for widget in self.chart_frame.winfo_children():
            widget.destroy()
    
    def show_categories(self):
        """Показать диаграмму категорий"""
        self.clear_chart_frame()
        data = db.get_products_by_category()
        if data:
            utils.show_chart(self.chart_frame, data, 'bar', 
                           'Товары по категориям', 'Категория', 'Количество')
        else:
            tk.Label(self.chart_frame, text="Нет данных для отображения").pack()
    
    def show_discrepancies(self):
        """Показать расхождения"""
        self.clear_chart_frame()
        data = db.get_inventory_discrepancies()
        if data:
            chart_data = {item['product_name']: item['difference'] for item in data[:10]}
            utils.show_chart(self.chart_frame, chart_data, 'bar',
                           'Расхождения по инвентаризациям', 'Товар', 'Разница')
        else:
            tk.Label(self.chart_frame, text="Нет расхождений").pack()
    
    def show_value(self):
        """Показать стоимость товаров"""
        self.clear_chart_frame()
        products = db.get_all_products()
        if products:
            chart_data = {p['name']: p['quantity'] * p['price'] for p in products[:10]}
            utils.show_chart(self.chart_frame, chart_data, 'bar',
                           'Общая стоимость товаров', 'Товар', 'Стоимость (₽)')
        else:
            tk.Label(self.chart_frame, text="Нет данных для отображения").pack()
    
    def export_csv(self):
        """Экспорт в CSV"""
        products = db.get_all_products()
        if products:
            filename = utils.export_to_csv(products)
            if filename:
                messagebox.showinfo("Успех", f"Данные экспортированы в {filename}")
            else:
                messagebox.showerror("Ошибка", "Ошибка экспорта")
        else:
            messagebox.showwarning("Предупреждение", "Нет данных для экспорта")


# ----- ОКНО АУДИТА -----

class AuditWindow(tk.Toplevel):
    """Окно просмотра аудит-лога"""
    
    def __init__(self, parent):
        super().__init__(parent)
        self.parent = parent
        
        self.title("Аудит-лог")
        self.geometry("900x500")
        self.resizable(True, True)
        self.grab_set()
        
        self.create_widgets()
        self.center_window()
        self.load_audit()
    
    def create_widgets(self):
        """Создать виджеты"""
        # Таблица
        frame = tk.Frame(self)
        frame.pack(fill='both', expand=True, padx=10, pady=10)
        
        scroll_y = ttk.Scrollbar(frame)
        scroll_y.pack(side='right', fill='y')
        
        scroll_x = ttk.Scrollbar(frame, orient='horizontal')
        scroll_x.pack(side='bottom', fill='x')
        
        columns = ('id', 'user_name', 'action', 'entity_type', 'entity_id', 'timestamp')
        self.tree = ttk.Treeview(frame, columns=columns, show='headings',
                                yscrollcommand=scroll_y.set, xscrollcommand=scroll_x.set)
        
        scroll_y.config(command=self.tree.yview)
        scroll_x.config(command=self.tree.xview)
        
        column_headers = {
            'id': 'ID',
            'user_name': 'Пользователь',
            'action': 'Действие',
            'entity_type': 'Тип',
            'entity_id': 'ID записи',
            'timestamp': 'Время'
        }
        
        for col in columns:
            self.tree.heading(col, text=column_headers.get(col, col))
            self.tree.column(col, width=150, anchor='center')
        
        self.tree.pack(fill='both', expand=True)
        
        # Кнопка обновления
        tk.Button(self, text="🔄 Обновить", command=self.load_audit,
                 bg='#3498db', fg='white', font=('Segoe UI', 9),
                 padx=10).pack(pady=5)
    
    def center_window(self):
        """Центрирование окна"""
        self.update_idletasks()
        width = self.winfo_width()
        height = self.winfo_height()
        x = (self.winfo_screenwidth() // 2) - (width // 2)
        y = (self.winfo_screenheight() // 2) - (height // 2)
        self.geometry(f'{width}x{height}+{x}+{y}')
    
    def load_audit(self):
        """Загрузить аудит-лог"""
        for item in self.tree.get_children():
            self.tree.delete(item)
        
        logs = db.get_audit_log(100)
        for log in logs:
            self.tree.insert('', 'end', values=(
                log['id'],
                log['user_name'],
                log['action'],
                log['entity_type'],
                log['entity_id'],
                utils.format_date(log['timestamp'])
            ))