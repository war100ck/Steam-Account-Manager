import os
import sys
from PIL import Image, ImageDraw, ImageFont
import PyInstaller.__main__

def create_icons():
    """Создание иконок для приложения"""
    if not os.path.exists('icons'):
        os.makedirs('icons')
    
    sizes = [16, 32, 48, 64, 128, 256]
    
    for size in sizes:
        # Создаем иконку
        icon = Image.new('RGBA', (size, size), (0, 0, 0, 0))
        draw = ImageDraw.Draw(icon)
        
        margin = max(1, size // 16)
        draw.ellipse([margin, margin, size - margin, size - margin], 
                    fill='#66c0f4', outline='#1b2838', width=max(1, size // 16))
        
        try:
            font_size = max(8, size // 2)
            font = ImageFont.truetype("arial.ttf", font_size)
        except:
            try:
                font = ImageFont.truetype("Arial", font_size)
            except:
                font = ImageFont.load_default()
        
        text = "S"
        bbox = draw.textbbox((0, 0), text, font=font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]
        x = (size - text_width) // 2
        y = (size - text_height) // 2 - size // 16
        
        draw.text((x, y), text, fill='#1b2838', font=font)
        
        # Сохраняем как PNG
        icon.save(f'icons/icon_{size}.png')
        
        # Для ICO создаем отдельно с правильным форматом
        if size in [16, 32, 48, 64]:
            ico_icon = Image.new('RGBA', (size, size), (0, 0, 0, 0))
            ico_draw = ImageDraw.Draw(ico_icon)
            ico_draw.ellipse([margin, margin, size - margin, size - margin], 
                           fill='#66c0f4', outline='#1b2838', width=max(1, size // 16))
            ico_draw.text((x, y), text, fill='#1b2838', font=font)
            
            # Конвертируем в RGB для ICO
            rgb_icon = Image.new('RGB', (size, size), (255, 255, 255))
            rgb_icon.paste(ico_icon, mask=ico_icon.split()[3] if ico_icon.mode == 'RGBA' else None)
            rgb_icon.save(f'icons/icon_{size}.ico')
            print(f"Создана иконка: icons/icon_{size}.ico")

def build_exe():
    """Сборка EXE файла"""
    try:
        print("Создание иконок...")
        create_icons()
        
        # Проверяем наличие иконки
        if not os.path.exists('icons/icon_64.ico'):
            raise FileNotFoundError("Иконка icon_64.ico не найдена.")
        
        print("Начинаем сборку EXE...")
        
        # Определяем разделитель пути в зависимости от ОС
        if os.name == 'nt':  # Windows
            path_sep = ';'
        else:  # Linux/Mac
            path_sep = ':'
        
        params = [
            'main_gui.py',
            '--name=Steam Account Manager',
            '--onefile',
            '--windowed',
            '--icon=icons/icon_64.ico',
            f'--add-data=icons{path_sep}icons',
            '--noconsole',
            '--clean',
            '--noconfirm',
        ]
        
        # Добавляем дополнительные скрытые импорты
        hidden_imports = [
            'PIL',
            'PIL._tkinter_finder',
            'PIL.Image',
            'PIL.ImageTk',
            'PIL.ImageOps',
            'PIL.ImageDraw',
            'PIL.ImageFont',
            'tkinter',
            'tkinter.ttk',
            'json',
            'base64',
            'hmac',
            'hashlib',
            'time',
            'struct',
            'requests',
            'threading',
            'io',
            'shutil',
            'datetime',
            'webbrowser',
            'ctypes',
        ]
        
        for imp in hidden_imports:
            params.append(f'--hidden-import={imp}')
        
        PyInstaller.__main__.run(params)
        print("Сборка завершена! EXE файл находится в папке 'dist'")
        
    except Exception as e:
        print(f"Ошибка при сборке: {e}")
        import traceback
        traceback.print_exc()
        input("Нажмите Enter для выхода...")

if __name__ == "__main__":
    build_exe()