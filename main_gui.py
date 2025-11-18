import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import json
import os
import base64
import hmac
import hashlib
import time
import struct
import requests
from threading import Thread
from PIL import Image, ImageTk, ImageOps, ImageDraw, ImageFont
import threading
import io
import shutil
from datetime import datetime
import sys
import webbrowser
import ctypes
import tempfile

def set_windows_taskbar_icon():
    """Установка иконки для панели задач Windows"""
    try:
        myappid = 'steam.account.manager.1.0'
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
        print(f"AppUserModelID установлен: {myappid}")
    except Exception as e:
        print(f"Не удалось установить ID приложения: {e}")

def resource_path(relative_path):
    """Получить абсолютный путь к ресурсу, работает для dev и для PyInstaller"""
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    full_path = os.path.join(base_path, relative_path)
    if 'icon' in relative_path and not os.path.exists(full_path):
        possible_names = [
            'icon_64.ico', 'icon_32.ico', 'icon_16.ico', 
            'icon_48.ico', 'icon_128.ico', 'icon_256.ico',
            'icon_64.png', 'icon_32.png'
        ]
        for name in possible_names:
            alt_path = os.path.join(base_path, 'icons', name)
            if os.path.exists(alt_path):
                print(f"Найдена иконка: {alt_path}")
                return alt_path
    return full_path

def get_app_directory():
    """Получить путь к директории приложения (рядом с EXE)"""
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    else:
        return os.path.abspath(".")

class ConfigManager:
    def __init__(self):
        self.app_dir = get_app_directory()
        self.config_file = os.path.join(self.app_dir, "config.json")
        self.config = self.load_config()

    def load_config(self):
        """Загрузка конфигурации из файла"""
        default_config = {
            "steam_api_key": "",
            "window_geometry": "1100x750"
        }
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    return {**default_config, **config}
            except Exception as e:
                print(f"Ошибка загрузки конфигурации: {e}")
                return default_config
        else:
            return default_config

    def save_config(self):
        """Сохранение конфигурации в файл"""
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=4, ensure_ascii=False)
            return True
        except Exception as e:
            print(f"Ошибка сохранения конфигурации: {e}")
            return False

    def get_api_key(self):
        """Получить API ключ"""
        return self.config.get("steam_api_key", "")

    def set_api_key(self, api_key):
        """Установить API ключ"""
        self.config["steam_api_key"] = api_key
        return self.save_config()

    def get_window_geometry(self):
        """Получить геометрию окна"""
        return self.config.get("window_geometry", "1100x750")

    def set_window_geometry(self, geometry):
        """Установить геометрию окна"""
        self.config["window_geometry"] = geometry
        return self.save_config()

class SteamAuth:
    def generate_2fa_code(self, shared_secret):
        """Генерация 2FA кода"""
        try:
            timestamp = int(time.time()) // 30
            key = base64.b64decode(shared_secret + '===')
            message = struct.pack('>Q', timestamp)
            hmac_result = hmac.new(key, message, hashlib.sha1).digest()
            start = hmac_result[19] & 0x0F
            code_int = struct.unpack('>I', hmac_result[start:start+4])[0] & 0x7FFFFFFF
            chars = '23456789BCDFGHJKMNPQRTVWXY'
            code = ''
            for _ in range(5):
                code += chars[code_int % len(chars)]
                code_int //= len(chars)
            return code
        except Exception as e:
            return f"Error: {str(e)}"

class SteamAPI:
    def __init__(self, config_manager):
        self.config_manager = config_manager
        self.api_key = self.config_manager.get_api_key()

    def set_api_key(self, api_key):
        """Установить API ключ"""
        self.api_key = api_key
        self.config_manager.set_api_key(api_key)

    def get_steam_avatar(self, steamid):
        """Получение аватара аккаунта Steam через официальный API"""
        if not self.api_key:
            return None
        try:
            app_dir = get_app_directory()
            cache_dir = os.path.join(app_dir, "accounts", "avatars")
            cache_path = os.path.join(cache_dir, f"{steamid}.jpg")
            if os.path.exists(cache_path):
                file_time = os.path.getmtime(cache_path)
                if time.time() - file_time < 24 * 3600:
                    try:
                        image = Image.open(cache_path)
                        return image
                    except Exception as e:
                        print(f"Ошибка загрузки аватара из кэша: {e}")
                        try:
                            os.remove(cache_path)
                        except:
                            pass
            url = "https://api.steampowered.com/ISteamUser/GetPlayerSummaries/v2/"
            params = {
                'key': self.api_key,
                'steamids': steamid
            }
            response = requests.get(url, params=params, timeout=10)
            if response.status_code == 200:
                data = response.json()
                players = data.get('response', {}).get('players', [])
                if players:
                    player_info = players[0]
                    avatar_urls = [
                        player_info.get('avatarfull', ''),
                        player_info.get('avatarmedium', ''),
                        player_info.get('avatar', '')
                    ]
                    avatar_url = next((url for url in avatar_urls if url), '')
                    if avatar_url:
                        if avatar_url.endswith('.jpg'):
                            png_url = avatar_url.replace('.jpg', '.png')
                            try:
                                img_response = requests.get(png_url, timeout=10)
                                if img_response.status_code == 200:
                                    avatar_url = png_url
                            except:
                                pass
                        img_response = requests.get(avatar_url, timeout=10)
                        if img_response.status_code == 200:
                            os.makedirs(cache_dir, exist_ok=True)
                            file_extension = '.png' if '.png' in avatar_url else '.jpg'
                            cache_path = os.path.join(cache_dir, f"{steamid}{file_extension}")
                            with open(cache_path, 'wb') as f:
                                f.write(img_response.content)
                            image_data = img_response.content
                            image = Image.open(io.BytesIO(image_data))
                            if image.mode in ('RGBA', 'LA', 'P'):
                                image = image.convert('RGB')
                            return image
            return None
        except Exception as e:
            print(f"Ошибка получения аватара: {e}")
            return None

    def get_player_info(self, steamid):
        """Получение дополнительной информации об игроке"""
        if not self.api_key:
            return None
        try:
            url = "https://api.steampowered.com/ISteamUser/GetPlayerSummaries/v2/"
            params = {
                'key': self.api_key,
                'steamids': steamid
            }
            response = requests.get(url, params=params, timeout=10)
            if response.status_code == 200:
                data = response.json()
                players = data.get('response', {}).get('players', [])
                if players:
                    return players[0]
            return None
        except Exception as e:
            print(f"Ошибка получения информации: {e}")
            return None

    def validate_api_key(self):
        """Проверка валидности API ключа"""
        if not self.api_key:
            return False, "API ключ не установлен"
        try:
            url = "https://api.steampowered.com/ISteamUser/GetPlayerSummaries/v2/"
            params = {
                'key': self.api_key,
                'steamids': '76561197960435530'
            }
            response = requests.get(url, params=params, timeout=10)
            if response.status_code == 200:
                return True, "API ключ валиден"
            else:
                return False, f"Ошибка API: {response.status_code}"
        except Exception as e:
            return False, f"Ошибка проверки API ключа: {e}"

class AccountManager:
    def __init__(self, accounts_dir="accounts"):
        app_dir = get_app_directory()
        self.accounts_dir = os.path.join(app_dir, accounts_dir)
        os.makedirs(self.accounts_dir, exist_ok=True)
        avatars_dir = os.path.join(self.accounts_dir, "avatars")
        os.makedirs(avatars_dir, exist_ok=True)
        self.auth = SteamAuth()

    def set_steam_api(self, steam_api):
        """Установить Steam API instance"""
        self.steam_api = steam_api

    def extract_steamid_from_mafile(self, account_data):
        """Автоматическое извлечение SteamID из данных maFile"""
        try:
            steamid = None
            if 'Session' in account_data and 'SteamID' in account_data['Session']:
                steamid = str(account_data['Session']['SteamID'])
            elif 'steamid' in account_data:
                steamid = str(account_data['steamid'])
            elif 'Session' in account_data and 'SteamLogin' in account_data['Session']:
                steam_login = account_data['Session']['SteamLogin']
                if '%7C%7C' in steam_login:
                    steamid = steam_login.split('%7C%7C')[0]
            elif 'account_name' in account_data and account_data['account_name'].isdigit():
                steamid = account_data['account_name']
            return steamid
        except Exception as e:
            print(f"Ошибка извлечения SteamID: {e}")
            return None

    def load_all_accounts(self):
        """Загрузка всех аккаунтов из maFiles"""
        accounts = {}
        if not os.path.exists(self.accounts_dir):
            print(f"Директория {self.accounts_dir} не существует")
            return accounts
        for filename in os.listdir(self.accounts_dir):
            if filename.endswith('.maFile'):
                file_path = os.path.join(self.accounts_dir, filename)
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        account_data = json.load(f)
                    account_id = filename.replace('.maFile', '')
                    if 'steamid' not in account_data or not account_data.get('steamid'):
                        steamid = self.extract_steamid_from_mafile(account_data)
                        if steamid:
                            account_data['steamid'] = steamid
                            with open(file_path, 'w', encoding='utf-8') as f:
                                json.dump(account_data, f, indent=4, ensure_ascii=False)
                    accounts[account_id] = account_data
                    print(f"Загружен аккаунт: {account_id}")
                except Exception as e:
                    print(f"Ошибка загрузки {filename}: {e}")
        print(f"Всего загружено аккаунтов: {len(accounts)}")
        return accounts

    def import_mafile(self, file_path):
        """Импорт maFile с автоматическим извлечением SteamID"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                account_data = json.load(f)
            steamid = self.extract_steamid_from_mafile(account_data)
            if steamid:
                account_data['steamid'] = steamid
            account_name = account_data.get('account_name', 'unknown')
            new_filename = f"{account_name}.maFile"
            new_path = os.path.join(self.accounts_dir, new_filename)
            with open(new_path, 'w', encoding='utf-8') as f:
                json.dump(account_data, f, indent=4, ensure_ascii=False)
            steamid_info = f" (SteamID: {steamid})" if steamid else ""
            return True, f"Аккаунт {account_name}{steamid_info} импортирован!"
        except Exception as e:
            return False, f"Ошибка импорта: {e}"

    def export_mafile(self, account_data, file_path):
        """Экспорт maFile"""
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(account_data, f, indent=4, ensure_ascii=False)
            return True, "maFile успешно экспортирован"
        except Exception as e:
            return False, f"Ошибка экспорта: {e}"

    def backup_accounts(self):
        """Создание резервной копии всех аккаунтов"""
        try:
            app_dir = get_app_directory()
            backup_dir = os.path.join(app_dir, "backups", f"backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}")
            os.makedirs(backup_dir, exist_ok=True)
            for filename in os.listdir(self.accounts_dir):
                if filename.endswith('.maFile'):
                    src = os.path.join(self.accounts_dir, filename)
                    dst = os.path.join(backup_dir, filename)
                    shutil.copy2(src, dst)
            avatars_src = os.path.join(self.accounts_dir, "avatars")
            avatars_dst = os.path.join(backup_dir, "avatars")
            if os.path.exists(avatars_src):
                shutil.copytree(avatars_src, avatars_dst)
            return True, f"Резервная копия создана: {backup_dir}"
        except Exception as e:
            return False, f"Ошибка создания резервной копии: {e}"

class IconManager:
    """Менеджер для управления иконками приложения"""
    _instance = None
    _icons_loaded = False
    _icons = {}

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(IconManager, cls).__new__(cls)
        return cls._instance

    def __init__(self):
        if not self._icons_loaded:
            self.load_icons()

    def load_icons(self):
        """Загрузка всех иконок приложения"""
        try:
            print("Загрузка иконок...")
            # Пробуем загрузить иконки из файлов
            icon_sizes = [16, 32, 48, 64, 128, 256]
            for size in icon_sizes:
                icon_path = resource_path(f"icons/icon_{size}.ico")
                if os.path.exists(icon_path):
                    try:
                        # Для Windows используем iconbitmap
                        self._icons[f'icon_{size}'] = icon_path
                        print(f"Иконка {size}x{size} найдена: {icon_path}")
                    except Exception as e:
                        print(f"Ошибка загрузки иконки {size}: {e}")
            # Если файловые иконки не загрузились, создаем временные
            if not self._icons:
                print("Создание временных иконок...")
                self.create_temp_icons()
            self._icons_loaded = True
            print("Иконки загружены успешно")
        except Exception as e:
            print(f"Ошибка загрузки иконок: {e}")
            self.create_temp_icons()
            self._icons_loaded = True

    def create_temp_icons(self):
        """Создание временных иконок в памяти"""
        try:
            sizes = [16, 32, 64]
            for size in sizes:
                # Создаем временную иконку в памяти
                icon = Image.new('RGBA', (size, size), (0, 0, 0, 0))
                draw = ImageDraw.Draw(icon)
                # Рисуем круг
                margin = max(1, size // 16)
                draw.ellipse([margin, margin, size - margin, size - margin], 
                            fill='#66c0f4', outline='#1b2838', width=max(1, size // 16))
                # Добавляем текст
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
                # Сохраняем временную иконку в файл
                temp_dir = tempfile.gettempdir()
                temp_icon_path = os.path.join(temp_dir, f'steam_manager_icon_{size}.ico')
                # Конвертируем в RGB для ICO
                rgb_icon = Image.new('RGB', (size, size), (255, 255, 255))
                rgb_icon.paste(icon, mask=icon.split()[3] if icon.mode == 'RGBA' else None)
                rgb_icon.save(temp_icon_path)
                self._icons[f'icon_{size}'] = temp_icon_path
                print(f"Создана временная иконка: {temp_icon_path}")
            print("Временные иконки созданы")
        except Exception as e:
            print(f"Ошибка создания временных иконок: {e}")

    def get_icon_path(self, size=32):
        """Получить путь к иконке указанного размера"""
        icon_key = f'icon_{size}'
        return self._icons.get(icon_key)

    def set_window_icon(self, window):
        """Установить иконку для окна"""
        try:
            print("Установка иконки для окна...")
            # Пробуем установить иконку через iconbitmap (для ICO файлов)
            icon_sizes = [64, 32, 48, 16, 128, 256]
            for size in icon_sizes:
                icon_path = self.get_icon_path(size)
                if icon_path and os.path.exists(icon_path):
                    try:
                        window.iconbitmap(icon_path)
                        print(f"Иконка установлена из файла: {icon_path}")
                        return True
                    except Exception as e:
                        print(f"Ошибка установки иконки из файла {icon_path}: {e}")
                        continue
            print("Не удалось установить иконку из файлов, пробуем создать временную...")
            # Создаем иконку на лету
            try:
                icon = Image.new('RGBA', (32, 32), (0, 0, 0, 0))
                draw = ImageDraw.Draw(icon)
                draw.ellipse([2, 2, 30, 30], fill='#66c0f4', outline='#1b2838', width=2)
                try:
                    font = ImageFont.truetype("arial.ttf", 16)
                except:
                    font = ImageFont.load_default()
                draw.text((10, 6), "S", fill='#1b2838', font=font)
                photo_image = ImageTk.PhotoImage(icon)
                window.wm_iconphoto(True, photo_image)
                # Сохраняем ссылку чтобы не удалилась сборщиком мусора
                window._icon = photo_image
                print("Иконка установлена из памяти")
                return True
            except Exception as e:
                print(f"Ошибка установки иконки из памяти: {e}")
                return False
        except Exception as e:
            print(f"Общая ошибка установки иконки: {e}")
            return False

class CustomDialog:
    def __init__(self, parent, title, width=400, height=200):
        self.parent = parent
        self.dialog = tk.Toplevel(parent)
        self.dialog.title(title)
        self.dialog.geometry(f"{width}x{height}")
        self.dialog.configure(bg='#1b2838')
        self.dialog.resizable(False, False)
        self.dialog.transient(parent)
        self.dialog.grab_set()
        # Устанавливаем иконку для диалогового окна
        self.icon_manager = IconManager()
        self.icon_manager.set_window_icon(self.dialog)
        # Центрируем диалог
        self.center_dialog()
        self.main_frame = tk.Frame(self.dialog, bg='#1b2838')
        self.main_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        self.result = None

    def center_dialog(self):
        """Центрирование диалогового окна"""
        self.dialog.update_idletasks()
        width = self.dialog.winfo_width()
        height = self.dialog.winfo_height()
        x = (self.dialog.winfo_screenwidth() // 2) - (width // 2)
        y = (self.dialog.winfo_screenheight() // 2) - (height // 2)
        self.dialog.geometry(f'+{x}+{y}')

    def create_button(self, parent, text, command, style="normal"):
        """Создание кнопки в стиле Steam"""
        bg_color = '#2a475e'
        hover_bg = '#3c5a78'
        fg_color = '#c7d5e0'
        if style == "accent":
            bg_color = '#66c0f4'
            hover_bg = '#4a9cd4'
            fg_color = 'white'
        btn = tk.Button(parent, text=text, command=command,
                      bg=bg_color, fg=fg_color, font=('Arial', 9, 'bold'),
                      relief='flat', padx=15, pady=8,
                      activebackground=hover_bg,
                      activeforeground=fg_color,
                      cursor='hand2',
                      bd=0,
                      highlightthickness=0)
        def on_enter(e):
            btn['background'] = hover_bg
        def on_leave(e):
            btn['background'] = bg_color
        btn.bind("<Enter>", on_enter)
        btn.bind("<Leave>", on_leave)
        return btn

class InfoDialog(CustomDialog):
    def __init__(self, parent, title, message, width=400, height=200):
        super().__init__(parent, title, width, height)
        self.setup_ui(message)

    def setup_ui(self, message):
        # Сообщение
        message_label = tk.Label(self.main_frame, text=message,
                               bg='#1b2838', fg='#c7d5e0', font=('Arial', 10),
                               justify=tk.LEFT, wraplength=350)
        message_label.pack(pady=(0, 20), fill=tk.BOTH, expand=True)
        # Кнопка OK
        button_frame = tk.Frame(self.main_frame, bg='#1b2838')
        button_frame.pack(fill=tk.X)
        ok_btn = self.create_button(button_frame, "OK", 
                                   command=self.dialog.destroy, style="accent")
        ok_btn.pack(side=tk.RIGHT)
        # Enter для закрытия
        self.dialog.bind('<Return>', lambda e: self.dialog.destroy())
        self.dialog.bind('<Escape>', lambda e: self.dialog.destroy())
        # Фокус на кнопке
        ok_btn.focus_set()

class ConfirmDialog(CustomDialog):
    def __init__(self, parent, title, message, width=400, height=200):
        super().__init__(parent, title, width, height)
        self.setup_ui(message)

    def setup_ui(self, message):
        # Сообщение
        message_label = tk.Label(self.main_frame, text=message,
                               bg='#1b2838', fg='#c7d5e0', font=('Arial', 10),
                               justify=tk.LEFT, wraplength=350)
        message_label.pack(pady=(0, 20), fill=tk.BOTH, expand=True)
        # Кнопки
        button_frame = tk.Frame(self.main_frame, bg='#1b2838')
        button_frame.pack(fill=tk.X)
        cancel_btn = self.create_button(button_frame, "Отмена", 
                                      command=self.cancel, style="normal")
        cancel_btn.pack(side=tk.LEFT)
        ok_btn = self.create_button(button_frame, "OK", 
                                   command=self.confirm, style="accent")
        ok_btn.pack(side=tk.RIGHT)
        # Обработка клавиш
        self.dialog.bind('<Return>', lambda e: self.confirm())
        self.dialog.bind('<Escape>', lambda e: self.cancel())
        # Фокус на кнопке OK
        ok_btn.focus_set()

    def confirm(self):
        self.result = True
        self.dialog.destroy()

    def cancel(self):
        self.result = False
        self.dialog.destroy()

    def show(self):
        self.dialog.wait_window()
        return self.result

class ApiKeyDialog(CustomDialog):
    def __init__(self, parent):
        super().__init__(parent, "Steam Web API Key", 500, 220)
        self.setup_ui()

    def setup_ui(self):
        # Информация
        info_label = tk.Label(self.main_frame, 
                             text="Для работы приложения требуется Steam Web API Key.\nПолучите ключ на сайте Steam и введите его ниже:",
                             bg='#1b2838', fg='#c7d5e0', font=('Arial', 10),
                             justify=tk.LEFT)
        info_label.pack(pady=(0, 15))
        # Поле ввода API ключа
        api_frame = tk.Frame(self.main_frame, bg='#1b2838')
        api_frame.pack(fill=tk.X, pady=10)
        tk.Label(api_frame, text="API Key:", bg='#1b2838', fg='#c7d5e0', 
                font=('Arial', 9)).pack(side=tk.LEFT)
        self.api_entry = tk.Entry(api_frame, width=40, font=('Arial', 9),
                                bg='#2a475e', fg='#c7d5e0', insertbackground='#c7d5e0',
                                relief='flat')
        self.api_entry.pack(side=tk.LEFT, padx=(10, 0), fill=tk.X, expand=True)
        # Кнопки
        buttons_frame = tk.Frame(self.main_frame, bg='#1b2838')
        buttons_frame.pack(fill=tk.X, pady=(10, 0))
        get_key_btn = self.create_button(buttons_frame, "Получить API Key", 
                                       command=self.get_api_key, style="normal")
        get_key_btn.pack(side=tk.LEFT)
        self.save_btn = self.create_button(buttons_frame, "Сохранить", 
                                         command=self.save_api_key, style="accent")
        self.save_btn.pack(side=tk.RIGHT)
        # Фокус на поле ввода
        self.api_entry.focus_set()
        # Enter для сохранения
        self.dialog.bind('<Return>', lambda e: self.save_api_key())
        self.dialog.bind('<Escape>', lambda e: self.dialog.destroy())

    def get_api_key(self):
        webbrowser.open("https://steamcommunity.com/dev/apikey")

    def save_api_key(self):
        api_key = self.api_entry.get().strip()
        if api_key:
            self.result = api_key
            self.dialog.destroy()
        else:
            # Подсветка поля ввода
            self.api_entry.config(bg='#5a2e2e')
            self.dialog.after(1000, lambda: self.api_entry.config(bg='#2a475e'))

    def show(self):
        self.dialog.wait_window()
        return self.result

class AccountStatusDialog(CustomDialog):
    def __init__(self, parent, status_info):
        super().__init__(parent, "Статус аккаунта", 450, 250)
        self.setup_ui(status_info)

    def setup_ui(self, status_info):
        # Заголовок статуса
        status_label = tk.Label(self.main_frame, text=status_info['status'],
                              bg='#1b2838', fg='#66c0f4', font=('Arial', 12, 'bold'),
                              justify=tk.LEFT)
        status_label.pack(pady=(0, 15))
        # Детальная информация
        details_text = f"Имя: {status_info['persona_name']}\n"
        details_text += f"Профиль: {'Настроен' if status_info['profile_state'] else 'Не настроен'}\n"
        details_text += f"Видимость: {status_info['visibility']}\n"
        if 'last_logoff' in status_info:
            last_online = datetime.fromtimestamp(status_info['last_logoff']).strftime('%Y-%m-%d %H:%M:%S')
            details_text += f"Последний онлайн: {last_online}"
        details_label = tk.Label(self.main_frame, text=details_text,
                               bg='#1b2838', fg='#c7d5e0', font=('Arial', 10),
                               justify=tk.LEFT)
        details_label.pack(pady=(0, 20), fill=tk.BOTH, expand=True)
        # Кнопка OK
        button_frame = tk.Frame(self.main_frame, bg='#1b2838')
        button_frame.pack(fill=tk.X)
        ok_btn = self.create_button(button_frame, "OK", 
                                   command=self.dialog.destroy, style="accent")
        ok_btn.pack(side=tk.RIGHT)
        # Обработка клавиш
        self.dialog.bind('<Return>', lambda e: self.dialog.destroy())
        self.dialog.bind('<Escape>', lambda e: self.dialog.destroy())
        # Фокус на кнопке
        ok_btn.focus_set()

class SteamManagerGUI:
    def __init__(self, root):
        self.root = root
        # Устанавливаем иконку для панели задач Windows ДО создания GUI
        if os.name == 'nt':  # Windows
            print("Установка AppUserModelID для Windows...")
            set_windows_taskbar_icon()
        # Инициализация конфигурации
        self.config_manager = ConfigManager()
        self.root.title("Steam Account Manager")
        self.root.geometry(self.config_manager.get_window_geometry())
        self.root.configure(bg='#1b2838')
        # Сохраняем геометрию при закрытии
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        # Инициализация менеджера иконок и установка иконки
        print("Инициализация менеджера иконок...")
        self.icon_manager = IconManager()
        # Пытаемся установить иконку несколько раз
        icon_set = False
        for attempt in range(3):
            if self.icon_manager.set_window_icon(self.root):
                icon_set = True
                break
            print(f"Попытка {attempt + 1} установки иконки не удалась, повторяем...")
            time.sleep(0.5)
        if not icon_set:
            print("ВНИМАНИЕ: Не удалось установить иконку приложения")
        self.set_steam_theme()
        # Инициализация API и менеджера аккаунтов
        self.steam_api = SteamAPI(self.config_manager)
        self.account_manager = AccountManager()
        self.account_manager.set_steam_api(self.steam_api)
        self.auth = SteamAuth()
        self.accounts = {}
        self.current_account = None
        self.avatar_images = {}
        self.current_account_id = None
        self.player_nicknames = {}
        self.setup_ui()
        self.load_accounts()
        self.auto_refresh()
        # Проверяем API ключ при запуске
        self.check_api_key_on_startup()

    def show_info_dialog(self, title, message):
        """Показать информационное диалоговое окно"""
        dialog = InfoDialog(self.root, title, message)

    def show_confirm_dialog(self, title, message):
        """Показать диалог подтверждения"""
        dialog = ConfirmDialog(self.root, title, message)
        return dialog.show()

    def show_api_key_dialog(self):
        """Показать диалог ввода API ключа"""
        dialog = ApiKeyDialog(self.root)
        api_key = dialog.show()
        if api_key:
            self.steam_api.set_api_key(api_key)
            success, message = self.steam_api.validate_api_key()
            if success:
                self.info_label.config(text="API ключ успешно сохранен и проверен")
            else:
                self.show_info_dialog("Ошибка", f"Неверный API ключ: {message}")
                # Показываем диалог снова если ключ невалидный
                self.show_api_key_dialog()

    def check_api_key_on_startup(self):
        """Проверка API ключа при запуске"""
        api_key = self.config_manager.get_api_key()
        if not api_key:
            self.show_api_key_dialog()
        else:
            success, message = self.steam_api.validate_api_key()
            if not success:
                self.info_label.config(text=f"Ошибка API ключа: {message}")

    def on_closing(self):
        """Сохранение геометрии окна при закрытии"""
        self.config_manager.set_window_geometry(self.root.geometry())
        self.root.destroy()

    def set_steam_theme(self):
        """Настройка темы в стиле Steam"""
        style = ttk.Style()
        style.theme_use('clam')
        self.bg_color = '#1b2838'
        self.header_color = '#171a21'
        self.panel_color = '#2a475e'
        self.accent_color = '#66c0f4'
        self.text_color = '#c7d5e0'
        self.hover_color = '#3c5a78'
        self.button_color = '#2a475e'
        style.configure(".",
                       background=self.bg_color,
                       foreground=self.text_color,
                       fieldbackground=self.panel_color,
                       selectbackground=self.accent_color,
                       selectforeground='white',
                       troughcolor=self.panel_color,
                       borderwidth=0)
        style.configure("Steam.Treeview",
                       background=self.panel_color,
                       foreground=self.text_color,
                       fieldbackground=self.panel_color,
                       borderwidth=0,
                       relief='flat')
        style.configure("Steam.Treeview.Heading",
                       background=self.header_color,
                       foreground=self.text_color,
                       relief='flat',
                       borderwidth=0,
                       font=('Arial', 10, 'bold'))
        style.map("Steam.Treeview.Heading",
                 background=[('active', self.hover_color)])
        style.map("Steam.Treeview",
                 background=[('selected', self.accent_color)],
                 foreground=[('selected', 'white')])

    def create_steam_button(self, parent, text, command, width=15, style="normal"):
        """Создание кнопки в стиле Steam"""
        if style == "normal":
            bg = self.button_color
            hover_bg = self.hover_color
            fg = self.text_color
        elif style == "accent":
            bg = self.accent_color
            hover_bg = '#4a9cd4'
            fg = 'white'
        elif style == "header":
            bg = self.header_color
            hover_bg = self.hover_color
            fg = self.text_color
        btn = tk.Button(parent, text=text, command=command,
                      bg=bg, fg=fg, font=('Arial', 9, 'bold'),
                      relief='flat', padx=20, pady=10,
                      activebackground=hover_bg,
                      activeforeground=fg,
                      width=width,
                      cursor='hand2',
                      bd=0,
                      highlightthickness=0)
        def on_enter(e):
            if btn['state'] != 'disabled':
                btn['background'] = hover_bg
        def on_leave(e):
            if btn['state'] != 'disabled':
                btn['background'] = bg
        btn.bind("<Enter>", on_enter)
        btn.bind("<Leave>", on_leave)
        return btn

    def setup_ui(self):
        main_frame = tk.Frame(self.root, bg=self.bg_color)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=0, pady=0)

        header_frame = tk.Frame(main_frame, bg=self.header_color, height=60)
        header_frame.pack(fill=tk.X, padx=0, pady=0)
        header_frame.pack_propagate(False)

        logo_frame = tk.Frame(header_frame, bg=self.header_color)
        logo_frame.pack(side=tk.LEFT, padx=20, pady=10)
        logo_label = tk.Label(logo_frame, text="⚙️", font=('Arial', 20), 
                             bg=self.header_color, fg=self.accent_color)
        logo_label.pack(side=tk.LEFT)
        title_label = tk.Label(logo_frame, text="Steam Account Manager", 
                              bg=self.header_color, fg=self.text_color, 
                              font=('Arial', 16, 'bold'))
        title_label.pack(side=tk.LEFT, padx=(10, 0))

        header_buttons_frame = tk.Frame(header_frame, bg=self.header_color)
        header_buttons_frame.pack(side=tk.RIGHT, padx=20, pady=10)
        header_buttons = [
            ("API Key", self.manage_api_key),
            ("Импорт", self.import_mafile),
            ("Обновить", self.load_accounts),
            ("Бэкап", self.create_backup),
        ]
        for text, command in header_buttons:
            btn = self.create_steam_button(header_buttons_frame, text, command, width=10, style="header")
            btn.pack(side=tk.LEFT, padx=3)

        content_frame = tk.Frame(main_frame, bg=self.bg_color)
        content_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)

        left_panel = tk.Frame(content_frame, bg=self.panel_color, relief='flat', bd=0)
        left_panel.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 15))

        table_header = tk.Frame(left_panel, bg=self.header_color, height=40)
        table_header.pack(fill=tk.X, padx=0, pady=0)
        table_header.pack_propagate(False)
        table_title = tk.Label(table_header, text="Управление аккаунтами", 
                              bg=self.header_color, fg=self.text_color, 
                              font=('Arial', 12, 'bold'))
        table_title.pack(side=tk.LEFT, padx=15, pady=10)

        table_container = tk.Frame(left_panel, bg=self.panel_color)
        table_container.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        columns = ('account_name', 'steamid', '2fa_code', 'status')
        self.tree = ttk.Treeview(table_container, columns=columns, show='headings', 
                                height=15, style="Steam.Treeview")
        self.tree.heading('account_name', text='Имя аккаунта')
        self.tree.heading('steamid', text='SteamID')
        self.tree.heading('2fa_code', text='2FA Код')
        self.tree.heading('status', text='Статус')
        self.tree.column('account_name', width=220, anchor='w')
        self.tree.column('steamid', width=200, anchor='w')
        self.tree.column('2fa_code', width=120, anchor='center')
        self.tree.column('status', width=150, anchor='center')

        scrollbar = ttk.Scrollbar(table_container, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.tree.bind('<<TreeviewSelect>>', self.on_account_select)

        right_panel = tk.Frame(content_frame, bg=self.panel_color, width=300, relief='flat', bd=0)
        right_panel.pack(side=tk.RIGHT, fill=tk.Y, padx=(15, 0))
        right_panel.pack_propagate(False)

        info_header = tk.Frame(right_panel, bg=self.header_color, height=40)
        info_header.pack(fill=tk.X, padx=0, pady=0)
        info_header.pack_propagate(False)
        info_title = tk.Label(info_header, text="Информация об аккаунте", 
                             bg=self.header_color, fg=self.text_color, 
                             font=('Arial', 12, 'bold'))
        info_title.pack(side=tk.LEFT, padx=15, pady=10)

        info_content = tk.Frame(right_panel, bg=self.panel_color)
        info_content.pack(fill=tk.BOTH, expand=True, padx=15, pady=15)

        self.avatar_frame = tk.Frame(info_content, bg=self.panel_color)
        self.avatar_frame.pack(pady=(0, 20))
        self.avatar_label = tk.Label(self.avatar_frame, bg=self.panel_color, width=120, height=120)
        self.avatar_label.pack()

        self.account_info_frame = tk.Frame(info_content, bg=self.panel_color)
        self.account_info_frame.pack(fill=tk.X, pady=(0, 20))
        self.nickname_label = tk.Label(self.account_info_frame, text="Никнейм: -", 
                                     bg=self.panel_color, fg=self.accent_color, 
                                     font=('Arial', 11, 'bold'),
                                     justify=tk.LEFT, anchor='w')
        self.nickname_label.pack(fill=tk.X, pady=(0, 5))
        self.account_name_label = tk.Label(self.account_info_frame, text="Аккаунт: -", 
                                         bg=self.panel_color, fg=self.text_color, 
                                         font=('Arial', 10),
                                         justify=tk.LEFT, anchor='w')
        self.account_name_label.pack(fill=tk.X)
        self.steamid_label = tk.Label(self.account_info_frame, text="SteamID: -", 
                                     bg=self.panel_color, fg=self.text_color, 
                                     font=('Arial', 10),
                                     justify=tk.LEFT, anchor='w')
        self.steamid_label.pack(fill=tk.X)

        self.twofa_frame = tk.Frame(self.account_info_frame, bg=self.panel_color)
        self.twofa_frame.pack(fill=tk.X, pady=(8, 0))
        self.twofa_label = tk.Label(self.twofa_frame, text="2FA Code: -", 
                                   bg=self.panel_color, fg=self.text_color, 
                                   font=('Arial', 10, 'bold'),
                                   justify=tk.LEFT, anchor='w')
        self.twofa_label.pack(side=tk.LEFT)
        self.copy_twofa_btn = tk.Button(self.twofa_frame, text="📋", 
                                       bg=self.panel_color, fg=self.accent_color, 
                                       font=('Arial', 9),
                                       relief='flat', padx=5, pady=2,
                                       activebackground=self.hover_color,
                                       activeforeground=self.accent_color,
                                       cursor='hand2',
                                       command=self.copy_2fa_from_label,
                                       bd=0,
                                       highlightthickness=0)
        def on_enter_copy(e):
            if self.copy_twofa_btn['state'] != 'disabled':
                self.copy_twofa_btn['background'] = self.hover_color
        def on_leave_copy(e):
            if self.copy_twofa_btn['state'] != 'disabled':
                self.copy_twofa_btn['background'] = self.panel_color
        self.copy_twofa_btn.bind("<Enter>", on_enter_copy)
        self.copy_twofa_btn.bind("<Leave>", on_leave_copy)
        self.copy_twofa_btn.pack(side=tk.RIGHT)
        self.copy_twofa_btn.pack_forget()

        self.status_label = tk.Label(self.account_info_frame, text="Статус: -", 
                                   bg=self.panel_color, fg=self.text_color, 
                                   font=('Arial', 10),
                                   justify=tk.LEFT, anchor='w')
        self.status_label.pack(fill=tk.X, pady=(5, 0))

        actions_frame = tk.Frame(info_content, bg=self.panel_color)
        actions_frame.pack(fill=tk.X)
        action_buttons = [
            ("Копировать 2FA", self.copy_2fa),
            ("Экспорт maFile", self.export_mafile),
            ("Открыть профиль", self.open_profile),
            ("Проверить статус", self.check_account_status),
        ]
        for text, command in action_buttons:
            btn = self.create_steam_button(actions_frame, text, command, width=25, style="normal")
            btn.pack(fill=tk.X, pady=4)

        bottom_frame = tk.Frame(main_frame, bg=self.header_color, height=40)
        bottom_frame.pack(fill=tk.X, side=tk.BOTTOM, padx=0, pady=0)
        bottom_frame.pack_propagate(False)
        self.info_label = tk.Label(bottom_frame, text="Готов к работе", 
                                  bg=self.header_color, fg=self.text_color, 
                                  font=('Arial', 9))
        self.info_label.pack(side=tk.LEFT, padx=20, pady=10)
        self.stats_label = tk.Label(bottom_frame, text="", 
                                   bg=self.header_color, fg=self.accent_color, 
                                   font=('Arial', 9, 'bold'))
        self.stats_label.pack(side=tk.RIGHT, padx=20, pady=10)

        self.default_avatar = self.create_steam_avatar()
        self.clear_avatar()

    def manage_api_key(self):
        """Управление API ключом"""
        self.show_api_key_dialog()

    def create_steam_avatar(self):
        """Создание аватара по умолчанию в стиле Steam"""
        image = Image.new('RGBA', (120, 120), (0, 0, 0, 0))
        draw = ImageDraw.Draw(image)
        draw.ellipse([5, 5, 115, 115], fill=self.panel_color, outline=self.accent_color, width=3)
        try:
            font = ImageFont.truetype("arial.ttf", 35)
        except:
            try:
                font = ImageFont.truetype("Arial", 35)
            except:
                font = ImageFont.load_default()
        draw.text((42, 32), "S", fill=self.accent_color, font=font)
        return ImageTk.PhotoImage(image)

    def load_accounts(self):
        """Загрузка аккаунтов в таблицу"""
        print("Начало загрузки аккаунтов...")
        self.accounts = self.account_manager.load_all_accounts()
        for item in self.tree.get_children():
            self.tree.delete(item)
        active_count = 0
        for acc_id, account in self.accounts.items():
            account_name = account.get('account_name', acc_id)
            steamid = account.get('steamid', 'Авто-поиск...')
            twofa = self.auth.generate_2fa_code(account.get('shared_secret', ''))
            if not account.get('shared_secret'):
                status = "❌ Нет секрета"
            elif not account.get('identity_secret'):
                status = "⚠️ Нет identity"
            else:
                status = "✅ Активен"
                active_count += 1
            self.tree.insert('', tk.END, values=(account_name, steamid, twofa, status), tags=(acc_id,))

        self.info_label.config(text=f"Загружено аккаунтов: {len(self.accounts)}")
        self.stats_label.config(text=f"Активных: {active_count} | Всего: {len(self.accounts)}")

        if self.accounts:
            first_item = self.tree.get_children()[0]
            self.tree.selection_set(first_item)
            self.tree.focus(first_item)
            self.on_account_select(None)
        else:
            self.clear_account_info()

    def on_account_select(self, event):
        selection = self.tree.selection()
        if selection:
            item = selection[0]
            acc_id = self.tree.item(item, 'tags')[0]
            self.current_account_id = acc_id
            self.current_account = self.accounts.get(acc_id)
            if self.current_account:
                self.update_account_info()
                self.load_nickname()

    def update_account_info(self):
        """Обновление информации об выбранном аккаунте"""
        if not self.current_account:
            return

        account_name = self.current_account.get('account_name', 'Неизвестно')
        steamid = self.current_account.get('steamid', 'Не найден')
        twofa_code = self.auth.generate_2fa_code(self.current_account.get('shared_secret', ''))
        
        self.account_name_label.config(text=f"Аккаунт: {account_name}")
        self.steamid_label.config(text=f"SteamID: {steamid}")
        self.twofa_label.config(text=f"2FA Code: {twofa_code}")

        if twofa_code and not twofa_code.startswith("Error"):
            self.copy_twofa_btn.pack(side=tk.RIGHT)
        else:
            self.copy_twofa_btn.pack_forget()

        if not self.current_account.get('shared_secret'):
            status = "❌ Нет секрета"
            color = "#ff6b6b"
        elif not self.current_account.get('identity_secret'):
            status = "⚠️ Нет identity"
            color = "#ffa726"
        else:
            status = "✅ Активен"
            color = "#66bb6a"
        self.status_label.config(text=f"Статус: {status}", fg=color)

        if steamid and steamid != 'Не найден' and steamid != 'Авто-поиск...':
            self.load_avatar(steamid)
        else:
            self.clear_avatar()

    def load_nickname(self):
        """Загрузка никнейма аккаунта"""
        if not self.current_account:
            return
        steamid = self.current_account.get('steamid')
        if not steamid or steamid in ['Не найден', 'Авто-поиск...']:
            self.nickname_label.config(text="Никнейм: Неизвестен")
            return

        if steamid in self.player_nicknames:
            nickname = self.player_nicknames[steamid]
            self.nickname_label.config(text=f"Никнейм: {nickname}")
            return

        Thread(target=self._load_nickname_thread, args=(steamid,), daemon=True).start()

    def _load_nickname_thread(self, steamid):
        """Поток для загрузки никнейма"""
        try:
            player_info = self.steam_api.get_player_info(steamid)
            if player_info:
                nickname = player_info.get('personaname', 'Неизвестен')
                self.player_nicknames[steamid] = nickname
                self.root.after(0, lambda: self.update_nickname(steamid, nickname))
            else:
                self.root.after(0, lambda: self.nickname_label.config(text="Никнейм: Неизвестен"))
        except Exception as e:
            print(f"Ошибка загрузки никнейма: {e}")
            self.root.after(0, lambda: self.nickname_label.config(text="Никнейм: Ошибка загрузки"))

    def update_nickname(self, steamid, nickname):
        """Обновление никнейма в UI"""
        if self.current_account and self.current_account.get('steamid') == steamid:
            self.nickname_label.config(text=f"Никнейм: {nickname}")

    def copy_2fa_from_label(self):
        """Копирование 2FA кода при клике на иконку (без всплывающих окон)"""
        if not self.current_account:
            return
        twofa_code = self.auth.generate_2fa_code(self.current_account.get('shared_secret', ''))
        if twofa_code and not twofa_code.startswith("Error"):
            self.root.clipboard_clear()
            self.root.clipboard_append(twofa_code)
            original_text = self.twofa_label.cget("text")
            self.twofa_label.config(text=f"2FA Code: ✓ Скопировано!")
            self.root.after(1000, lambda: self.twofa_label.config(text=original_text))

    def clear_account_info(self):
        """Очистка информации об аккаунте"""
        self.nickname_label.config(text="Никнейм: -")
        self.account_name_label.config(text="Аккаунт: -")
        self.steamid_label.config(text="SteamID: -")
        self.twofa_label.config(text="2FA Code: -")
        self.status_label.config(text="Статус: -", fg=self.text_color)
        self.copy_twofa_btn.pack_forget()
        self.clear_avatar()

    def clear_avatar(self):
        """Очистка аватара"""
        self.avatar_label.config(image=self.default_avatar)
        self.avatar_label.image = self.default_avatar

    def load_avatar(self, steamid):
        """Загрузка аватара из кэша или интернета"""
        app_dir = get_app_directory()
        possible_paths = [
            os.path.join(app_dir, "accounts", "avatars", f"{steamid}.png"),
            os.path.join(app_dir, "accounts", "avatars", f"{steamid}.jpg"),
            os.path.join(app_dir, "accounts", "avatars", f"{steamid}.jpeg")
        ]
        for cache_path in possible_paths:
            if os.path.exists(cache_path):
                try:
                    image = Image.open(cache_path)
                    image = image.resize((120, 120), Image.Resampling.LANCZOS)
                    image = self.make_circular_avatar(image)
                    photo_image = ImageTk.PhotoImage(image)
                    self.avatar_label.config(image=photo_image)
                    self.avatar_label.image = photo_image
                    return
                except Exception as e:
                    print(f"Ошибка загрузки аватара из кэша {cache_path}: {e}")
                    try:
                        os.remove(cache_path)
                    except:
                        pass

        Thread(target=self._load_avatar_thread, args=(steamid,), daemon=True).start()

    def _load_avatar_thread(self, steamid):
        """Поток для загрузки аватара"""
        try:
            avatar_image = self.steam_api.get_steam_avatar(steamid)
            if avatar_image:
                avatar_image = avatar_image.resize((120, 120), Image.Resampling.LANCZOS)
                avatar_image = self.make_circular_avatar(avatar_image)
                photo_image = ImageTk.PhotoImage(avatar_image)
                self.root.after(0, lambda: self.update_avatar(steamid, photo_image))
        except Exception as e:
            print(f"Ошибка загрузки аватара: {e}")

    def update_avatar(self, steamid, photo_image):
        """Обновление аватара в UI"""
        if self.current_account and self.current_account.get('steamid') == steamid:
            self.avatar_label.config(image=photo_image)
            self.avatar_label.image = photo_image

    def make_circular_avatar(self, image):
        """Создание круглого аватара с обводкой в стиле Steam"""
        mask = Image.new('L', image.size, 0)
        draw = ImageDraw.Draw(mask)
        draw.ellipse([0, 0, image.size[0], image.size[1]], fill=255)
        circular_image = Image.new('RGBA', image.size, (0, 0, 0, 0))
        circular_image.putalpha(mask)
        circular_image.paste(image, (0, 0))
        result = Image.new('RGBA', (image.size[0] + 6, image.size[1] + 6), (0, 0, 0, 0))
        draw = ImageDraw.Draw(result)
        draw.ellipse([3, 3, image.size[0] + 3, image.size[1] + 3], outline=self.accent_color, width=3)
        result.paste(circular_image, (3, 3), circular_image)
        return result

    def create_backup(self):
        """Создание резервной копии всех аккаунтов"""
        success, message = self.account_manager.backup_accounts()
        if success:
            self.show_info_dialog("Успех", message)
        else:
            self.show_info_dialog("Ошибка", message)

    def open_profile(self):
        """Открытие профиля Steam в браузере"""
        if not self.current_account:
            self.show_info_dialog("Внимание", "Выберите аккаунт")
            return
        steamid = self.current_account.get('steamid')
        if not steamid or steamid in ['Не найден', 'Авто-поиск...']:
            self.show_info_dialog("Внимание", "SteamID не найден")
            return
        webbrowser.open(f"https://steamcommunity.com/profiles/{steamid}")
        self.info_label.config(text=f"Открыт профиль: {steamid}")

    def check_account_status(self):
        """Проверка статуса аккаунта через Steam API"""
        if not self.current_account:
            self.show_info_dialog("Внимание", "Выберите аккаунт")
            return
        steamid = self.current_account.get('steamid')
        if not steamid or steamid in ['Не найден', 'Авто-поиск...']:
            self.show_info_dialog("Внимание", "SteamID не найден")
            return
        self.info_label.config(text="Проверка статуса аккаунта...")
        Thread(target=self._check_account_status_thread, args=(steamid,), daemon=True).start()

    def _check_account_status_thread(self, steamid):
        """Поток для проверки статуса аккаунта"""
        try:
            player_info = self.steam_api.get_player_info(steamid)
            if player_info:
                persona_name = player_info.get('personaname', 'Неизвестно')
                profile_state = player_info.get('profilestate', 0)
                community_visible = player_info.get('communityvisibilitystate', 1)
                last_logoff = player_info.get('lastlogoff', 0)
                status_info = {
                    'status': "✅ Аккаунт активен" + (" (приватный)" if community_visible == 1 else " (публичный)" if community_visible == 3 else ""),
                    'persona_name': persona_name,
                    'profile_state': profile_state == 1,
                    'visibility': "Приватный" if community_visible == 1 else "Публичный" if community_visible == 3 else "Друзья",
                    'last_logoff': last_logoff
                }
                self.root.after(0, lambda: AccountStatusDialog(self.root, status_info))
                self.root.after(0, lambda: self.info_label.config(text=f"Статус проверен: {persona_name}"))
            else:
                self.root.after(0, lambda: self.show_info_dialog("Внимание", "Не удалось получить информацию об аккаунте"))
        except Exception as e:
            self.root.after(0, lambda: self.info_label.config(text=f"Ошибка проверки: {e}"))

    def import_mafile(self):
        file_path = filedialog.askopenfilename(
            title="Выберите maFile",
            filetypes=[("maFiles", "*.maFile"), ("Все файлы", "*.*")]
        )
        if file_path:
            success, message = self.account_manager.import_mafile(file_path)
            if success:
                self.show_info_dialog("Успех", message)
                self.load_accounts()
            else:
                self.show_info_dialog("Ошибка", message)

    def copy_2fa(self):
        if not self.current_account:
            self.show_info_dialog("Внимание", "Выберите аккаунт")
            return
        twofa_code = self.auth.generate_2fa_code(self.current_account.get('shared_secret', ''))
        self.root.clipboard_clear()
        self.root.clipboard_append(twofa_code)
        self.show_info_dialog("Успех", f"2FA код {twofa_code} скопирован в буфер")

    def export_mafile(self):
        if not self.current_account:
            self.show_info_dialog("Внимание", "Выберите аккаунт для экспорта")
            return
        file_path = filedialog.asksaveasfilename(
            title="Экспорт maFile",
            defaultextension=".maFile",
            filetypes=[("maFiles", "*.maFile")]
        )
        if file_path:
            try:
                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump(self.current_account, f, indent=4, ensure_ascii=False)
                self.show_info_dialog("Успех", "maFile успешно экспортирован")
            except Exception as e:
                self.show_info_dialog("Ошибка", f"Ошибка экспорта: {e}")

    def auto_refresh(self):
        """Автоматическое обновление 2FA кодов в реальном времени"""
        for item in self.tree.get_children():
            acc_id = self.tree.item(item, 'tags')[0]
            if acc_id in self.accounts:
                account = self.accounts[acc_id]
                twofa = self.auth.generate_2fa_code(account.get('shared_secret', ''))
                current_values = self.tree.item(item, 'values')
                new_values = (
                    current_values[0],
                    current_values[1],
                    twofa,
                    current_values[3]
                )
                self.tree.item(item, values=new_values)

        if self.current_account_id and self.current_account_id in self.accounts:
            self.current_account = self.accounts[self.current_account_id]
            self.update_account_info()

        self.root.after(30000, self.auto_refresh)

def main():
    print("Запуск Steam Account Manager...")
    # Устанавливаем иконку для панели задач Windows
    if os.name == 'nt':
        set_windows_taskbar_icon()
    root = tk.Tk()
    app = SteamManagerGUI(root)
    print("Приложение запущено")
    root.mainloop()

if __name__ == "__main__":
    main()