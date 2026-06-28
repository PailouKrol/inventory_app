import tkinter as tk
from tkinter import ttk, messagebox
from config import config

class AuthWindow:
    """Окно авторизации"""
    
    def __init__(self, parent, callback=None):
        self.parent = parent
        self.callback = callback
        self.login_successful = False
        self.current_user = None
        
        self.max_attempts = config.get_int('AUTH', 'max_login_attempts', 3)
        self.attempts = 0
        self.blocked = False
        
        self.create_window()
    
    def create_window(self):
        """Создать окно авторизации"""
        self.parent.withdraw()
        
        self.window = tk.Toplevel(self.parent)
        self.window.title("Авторизация")
        self.window.geometry("450x520")
        self.window.resizable(False, False)
        self.window.protocol("WM_DELETE_WINDOW", self.on_close)
        
        self.center_window()
        
        # Заголовок
        company_name = config.get('APP', 'company_name', 'Система инвентаризации')
        title_frame = tk.Frame(self.window, bg='#2c3e50', height=120)
        title_frame.pack(fill='x')
        title_frame.pack_propagate(False)

        # Создаём внутренний фрейм с отступами
        inner_frame = tk.Frame(title_frame, bg='#2c3e50')
        inner_frame.pack(fill='both', expand=True, padx=20, pady=15)

        tk.Label(inner_frame, text=company_name, font=('Segoe UI', 14, 'bold'),
                bg='#2c3e50', fg='white').pack(anchor='center', pady=(5, 0))
        tk.Label(inner_frame, text="Вход в систему", font=('Segoe UI', 10),
        bg='#2c3e50', fg='#bdc3c7').pack(anchor='center', pady=(0, 5))
        
        # Основной блок
        main_frame = tk.Frame(self.window, padx=40, pady=30)
        main_frame.pack(fill='both', expand=True)
        
        # Логин
        tk.Label(main_frame, text="Логин:", font=('Segoe UI', 10)).pack(anchor='w')
        self.login_var = tk.StringVar()
        self.login_entry = tk.Entry(main_frame, textvariable=self.login_var,
                                   font=('Segoe UI', 10), width=30)
        self.login_entry.pack(pady=(0, 15), fill='x')
        self.login_entry.focus()
        
        # Пароль
        tk.Label(main_frame, text="Пароль:", font=('Segoe UI', 10)).pack(anchor='w')
        self.password_var = tk.StringVar()
        self.password_entry = tk.Entry(main_frame, textvariable=self.password_var,
                                      font=('Segoe UI', 10), width=30, show='●')
        self.password_entry.pack(pady=(0, 15), fill='x')
        self.password_entry.bind('<Return>', lambda e: self.login())
        
        # Кнопки
        button_frame = tk.Frame(main_frame)
        button_frame.pack(pady=10)
        
        tk.Button(button_frame, text="Войти", command=self.login,
                 bg='#3498db', fg='white', font=('Segoe UI', 10, 'bold'),
                 width=12, padx=5, pady=3).pack(side='left', padx=5)
        
        tk.Button(button_frame, text="Выход", command=self.on_close,
                 bg='#e74c3c', fg='white', font=('Segoe UI', 10, 'bold'),
                 width=12, padx=5, pady=3).pack(side='left', padx=5)
        
        # Статус
        self.status_label = tk.Label(main_frame, text="", font=('Segoe UI', 9),
                                     fg='#e74c3c')
        self.status_label.pack(pady=5)
        
        # Информация о пользователях
        info_frame = tk.Frame(self.window, bg='#ecf0f1')
        info_frame.pack(fill='x', side='bottom')

        tk.Label(info_frame, text="Пользователи по умолчанию:", font=('Segoe UI', 8),
                bg='#ecf0f1').pack(pady=(5,0))

        # Строка с пользователями (краткое описание)
        users_text = (
            "admin / admin123 (Админ)  |  "
            "user / user123 (Кладовщик)  |  "
            "manager / manager123 (Менеджер)  |  "
            "auditor / auditor123 (Аудитор)    "
        )
        tk.Label(info_frame, text=users_text, font=('Segoe UI', 7),
        bg='#ecf0f1', wraplength=400, justify='center').pack(pady=(0,5))
        
        self.window.bind('<Return>', lambda e: self.login())
    
    def center_window(self):
        """Центрирование окна"""
        self.window.update_idletasks()
        width = self.window.winfo_width()
        height = self.window.winfo_height()
        x = (self.window.winfo_screenwidth() // 2) - (width // 2)
        y = (self.window.winfo_screenheight() // 2) - (height // 2)
        self.window.geometry(f'{width}x{height}+{x}+{y}')
    
    def login(self):
        """Обработка входа"""
        if self.blocked:
            self.status_label.config(text="❌ Слишком много попыток. Перезапустите приложение.")
            return
        
        login = self.login_var.get().strip()
        password = self.password_var.get().strip()
        
        if not login or not password:
            self.status_label.config(text="❌ Введите логин и пароль")
            return
        
        user = config.get_user(login)
        if not user:
            self.attempts += 1
            self.status_label.config(text=f"❌ Пользователь не найден (попытка {self.attempts}/{self.max_attempts})")
            self.check_attempts()
            return
        
        if not user['active']:
            self.status_label.config(text="❌ Пользователь заблокирован")
            return
        
        if config.check_password(login, password):
            self.current_user = login
            self.login_successful = True
            config.set_current_user(login)
            self.status_label.config(text="✅ Вход выполнен!", fg='#27ae60')
            
            self.window.destroy()
            self.parent.deiconify()
            
            if self.callback:
                self.callback(login)
            else:
                from app import InventoryApp
                app = InventoryApp(self.parent, login)
                self.parent.mainloop()
        else:
            self.attempts += 1
            self.status_label.config(text=f"❌ Неверный пароль (попытка {self.attempts}/{self.max_attempts})")
            self.password_var.set('')
            self.password_entry.focus()
            self.check_attempts()
    
    def check_attempts(self):
        """Проверка количества попыток"""
        if self.attempts >= self.max_attempts:
            self.blocked = True
            self.status_label.config(text=f"❌ Превышено количество попыток. Приложение заблокировано.")
            self.login_entry.config(state='disabled')
            self.password_entry.config(state='disabled')
    
    def on_close(self):
        """Закрытие приложения"""
        if messagebox.askyesno("Выход", "Вы действительно хотите выйти?"):
            self.parent.quit()
            self.parent.destroy()