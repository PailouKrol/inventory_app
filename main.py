import tkinter as tk
from config import config

class App:
    """Главный класс приложения, управляющий окнами"""
    
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Система инвентаризации")
        self.root.geometry("800x600")
        self.root.withdraw()
        self.current_user = None
        self.main_app = None
        self.auth_window = None
        
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)
        self.root.after(100, self.show_auth)
    
    def show_auth(self):
        """Показать окно авторизации"""
        from auth import AuthWindow
        self.auth_window = AuthWindow(self.root, callback=self.on_auth_success)
    
    def on_auth_success(self, username):
        """Обработчик успешной авторизации"""
        self.current_user = username
        self.root.deiconify()
        self.show_main_app()
    
    def show_main_app(self):
        """Показать главное приложение"""
        from app import InventoryApp
        if self.main_app:
            self.main_app = None
        self.main_app = InventoryApp(self.root, self.current_user, self.on_logout)
    
    def on_logout(self):
        """Выход из системы - показываем авторизацию"""
        self.current_user = None
        # Скрываем главное окно
        self.root.withdraw()
        # Удаляем ссылку на главное приложение
        if self.main_app:
            # Удаляем все виджеты из главного окна
            for widget in self.root.winfo_children():
                widget.destroy()
            self.main_app = None
        # Показываем окно авторизации
        self.show_auth()
    
    def on_close(self):
        """Полное закрытие приложения"""
        if messagebox.askyesno("Выход", "Вы уверены, что хотите закрыть приложение?"):
            self.root.quit()
            self.root.destroy()
    
    def run(self):
        """Запуск приложения"""
        self.root.mainloop()

def main():
    app = App()
    app.run()

if __name__ == "__main__":
    main()