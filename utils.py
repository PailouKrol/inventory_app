import csv
import os
from datetime import datetime
import tkinter as tk
from tkinter import filedialog, messagebox
from config import config

try:
    import matplotlib.pyplot as plt
    from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
    MATPLOTLIB_AVAILABLE = True
except ImportError:
    MATPLOTLIB_AVAILABLE = False

try:
    import qrcode
    from PIL import Image, ImageTk
    QR_AVAILABLE = True
except ImportError:
    QR_AVAILABLE = False

try:
    import openpyxl
    from openpyxl import Workbook
    OPENPYXL_AVAILABLE = True
except ImportError:
    OPENPYXL_AVAILABLE = False


class Utils:
    """Вспомогательные функции"""
    
    @staticmethod
    def format_date(date_str):
        """Форматировать дату"""
        if not date_str:
            return ''
        try:
            dt = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
            return dt.strftime('%d.%m.%Y %H:%M')
        except:
            return date_str
    
    @staticmethod
    def format_currency(value):
        """Форматировать валюту"""
        try:
            return f"{float(value):,.2f} ₽"
        except:
            return "0.00 ₽"
    
    @staticmethod
    def generate_qr_code(data, filename=None):
        """Сгенерировать QR-код"""
        if not QR_AVAILABLE:
            return None
        
        try:
            qr = qrcode.QRCode(
                version=1,
                error_correction=qrcode.constants.ERROR_CORRECT_L,
                box_size=10,
                border=4,
            )
            qr.add_data(data)
            qr.make(fit=True)
            
            img = qr.make_image(fill_color="black", back_color="white")
            
            if filename:
                img.save(filename)
                return filename
            return img
        except Exception as e:
            print(f"Ошибка генерации QR-кода: {e}")
            return None
    
    @staticmethod
    def export_to_csv(data, filename=None, headers=None):
        """Экспорт в CSV"""
        if not filename:
            export_path = config.get('EXPORT', 'export_path', './exports/')
            os.makedirs(export_path, exist_ok=True)
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = os.path.join(export_path, f'export_{timestamp}.csv')
        
        try:
            with open(filename, 'w', newline='', encoding='utf-8-sig') as f:
                if data and len(data) > 0:
                    if headers is None:
                        headers = list(data[0].keys())
                    writer = csv.DictWriter(f, fieldnames=headers, delimiter=';')
                    writer.writeheader()
                    writer.writerows(data)
            return filename
        except Exception as e:
            print(f"Ошибка экспорта CSV: {e}")
            return None
    
    @staticmethod
    def export_to_excel(data, filename=None, headers=None):
        """Экспорт в Excel"""
        if not OPENPYXL_AVAILABLE:
            return None
        
        if not filename:
            export_path = config.get('EXPORT', 'export_path', './exports/')
            os.makedirs(export_path, exist_ok=True)
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = os.path.join(export_path, f'export_{timestamp}.xlsx')
        
        try:
            wb = Workbook()
            ws = wb.active
            
            if data and len(data) > 0:
                if headers is None:
                    headers = list(data[0].keys())
                ws.append(headers)
                for row in data:
                    ws.append([row.get(h, '') for h in headers])
            
            wb.save(filename)
            return filename
        except Exception as e:
            print(f"Ошибка экспорта Excel: {e}")
            return None
    
    @staticmethod
    def show_chart(parent, data, chart_type='bar', title='', x_label='', y_label=''):
        """Показать диаграмму в окне Tkinter"""
        if not MATPLOTLIB_AVAILABLE:
            tk.Label(parent, text="⚠️ Matplotlib не установлен", fg='red').pack()
            return None
        
        try:
            fig, ax = plt.subplots(figsize=(6, 4))
            
            if chart_type == 'bar':
                ax.bar(list(data.keys()), list(data.values()), 
                       color=config.get('REPORTS', 'chart_colors', '#3498db').split(','))
            elif chart_type == 'pie':
                ax.pie(list(data.values()), labels=list(data.keys()), autopct='%1.1f%%')
            elif chart_type == 'line':
                ax.plot(list(data.keys()), list(data.values()), marker='o')
            
            ax.set_title(title)
            ax.set_xlabel(x_label)
            ax.set_ylabel(y_label)
            
            fig.tight_layout()
            
            canvas = FigureCanvasTkAgg(fig, parent)
            canvas.draw()
            canvas.get_tk_widget().pack(fill='both', expand=True)
            return canvas
        except Exception as e:
            tk.Label(parent, text=f"Ошибка построения графика: {e}", fg='red').pack()
            return None

utils = Utils()