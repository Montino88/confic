from PyQt5.QtWidgets import (QAbstractItemView, QCheckBox, QDialog, QFileDialog, QHBoxLayout, 
                             QHeaderView, QMessageBox, QLabel, QProgressBar, QPushButton, QScrollArea, 
                             QSizePolicy, QSpacerItem, QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QTimer
from PyQt5.QtWidgets import QLineEdit, QComboBox
from PyQt5.QtGui import QColor, QDesktopServices, QPalette
import traceback
from scan_thread import ScanThread
import ipaddress
import json
import webbrowser
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QUrl, QTimer
from PyQt5.QtCore import QObject, pyqtSlot
import os
import pickle
from PyQt5 import QtWidgets
from PyQt5.QtCore import QPropertyAnimation, Qt
from PyQt5.QtWidgets import QGraphicsOpacityEffect
from PyQt5.QtWidgets import QTableWidgetItem
import re
import socket
import time
import requests



class CommandExecutor:
    def __init__(self):
        self.credentials = {}  # Словарь для хранения учетных данных

    def set_credentials(self, model, login, password):
        # Установка учетных данных для модели устройства
        self.credentials[model] = {'login': login, 'password': password}
        # Вывод информации о сохраненных учетных данных
        print(f"Учетные данные для модели {model} установлены: логин {login}, пароль {password}")
        
    def get_credentials(self, model):
        # Получение учетных данных для модели майнера
        return self.credentials.get(model, {})

# Функция convert_seconds_to_time_string: Отвечает за конверт емплас
def convert_seconds_to_time_string(seconds):
    days, remainder = divmod(seconds, 86400)
    hours, remainder = divmod(remainder, 3600)
    minutes, seconds = divmod(remainder, 60)
    return f"{days} d {hours} h {minutes} m {seconds} s"

class ScanTab(QWidget):
    # Создание сигнала для взаимодействия между потоками и главным окном
    update_table_signal = pyqtSignal(dict, int)
    ip_processed_signal = pyqtSignal(dict, int)  
    scan_finished_signal = pyqtSignal()  # Сигнал, испускаться при завершении сканирования
    # В ScanTab, замените сигнал на этот
    update_control_tab_signal = pyqtSignal(list)

     
    def __init__(self, parent=None):
        super(ScanTab, self).__init__(parent)
        self.global_ip_set = set()  # Инициализация множества для хранения активных IP-адресов
        self.led_status = {}
        self.threads = []
       
        
        self.led_state = False  # Состояние светодиода: False - выключен, True - включен

        self.monitor_enabled = False  # флаг для отслеживания мониторинга

        self.scan_thread = None

        self.miner_rows = {}
        self.open_ports = {}
        self.row_count = 0

        # Сбор IP-адресов
        self.command_executor = CommandExecutor()
        self.scan_thread = ScanThread(self)

        layout = QVBoxLayout()

        button_layout = QHBoxLayout()
        button_layout.setContentsMargins(0, -10, 0, 0)

        #  кнопки
        self.scan_button = QPushButton("Scan")
        self.scan_button.clicked.connect(self.start_scan_and_get_data)

        self.monitor_button = QPushButton("Monitor", self)
        self.monitor_button.clicked.connect(self.start_stop_monitor)

        self.asic_search_button = QPushButton("Ip list")
        self.asic_search_button.clicked.connect(self.save_ips_to_file)

      
       
        # Стилизация кнопок (применяется ко всем кнопкам)
        self.setStyleSheet("""
            QPushButton { 
                color: white;
                border: 2px solid #555555;
                border-radius: 10px;
                background: #20B2AA;
                padding: 5px;
            } 
            QPushButton:hover {
                background: #0C75F5;
            }
            QPushButton:pressed {
                background: #20B2AA;
            }
        """)

        # Добавление кнопок в макет
        button_layout.addWidget(self.scan_button)
        button_layout.addWidget(self.monitor_button)
        button_layout.addWidget(self.asic_search_button)
        
        button_layout.addItem(QSpacerItem(20, 20, QSizePolicy.Expanding, QSizePolicy.Minimum))

        layout.addLayout(button_layout)

        self.progress_bar = QProgressBar(self)
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                border: 2px solid 262F34;
                border-radius: 5px;
                text-align: center;
            }
            QProgressBar::chunk {
               background-color: #05B8CC;
               width: 20px;
            }""")
        layout.addWidget(self.progress_bar)

        self.table = QTableWidget(2000, 20, self)
        # Инициализация виджета для отображения таблицы
        self.table.setSortingEnabled(True)

        self.table.horizontalHeader().setSectionsMovable(True)
        self.load_header_state()

        self.table.verticalHeader().setVisible(False)

        # Сделать таблицу нередактируемой
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        # Инициализация виджета для отображения таблицы

        
        self.table.cellClicked.connect(self.open_web_interface)
        self.scrollArea = QScrollArea(self)

        self.scrollArea.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)

        self.scrollArea.setWidgetResizable(True)
        self.scrollArea.setWidget(self.table)
        self.scrollArea.setStyleSheet("""
        QScrollBar:horizontal {
            border: none;
            background: lightgray;
            height: 14px;
            margin: 0px 21px 0 21px;
        }
        QScrollBar::handle:horizontal {
            background: gray;
            min-width: 20px;
        }
        QScrollBar::add-line:horizontal {
           border: none;
           background: none;
           width: 20px;
           subcontrol-position: right;
           subcontrol-origin: margin;
        }  
        QScrollBar::sub-line:horizontal {
           border: none;
           background: none;
           width: 20px;
           subcontrol-position: left;
           subcontrol-origin: margin;
        }
    """)

        # Connect cell click event to a method
        layout.addWidget(self.scrollArea)


        self.table.setHorizontalHeaderLabels(["", "IP", "Status", "Type", "Ths avg", "Ths rt", "Elapsed", "fan_speed", "Temp Chip" , "power", "CompileTime", "URL1", "User1", "Status1", "URL2", "User2", "Status2", "URL3", "User3", "Status3", ])
        self.table.setColumnWidth(0, 30)
        self.table.setColumnWidth(1, 100)
        self.table.setColumnWidth(2, 50)
        self.table.setColumnWidth(8, 100)
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Fixed)
        self.table.horizontalHeader().setSectionsClickable(True)
        self.table.horizontalHeader().setSectionResizeMode(0, QtWidgets.QHeaderView.Fixed)
        vertical_header = self.table.verticalHeader()
        vertical_header.setStyleSheet("QHeaderView::section { background-color: #333333 }")
        vertical_palette = vertical_header.palette()
        vertical_palette.setColor(QPalette.Text, QColor("#ffffff"))
        vertical_header.setPalette(vertical_palette)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.setSelectionMode(QAbstractItemView.NoSelection)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)

        self.table.setStyleSheet("""
          
            QTableWidget::item {
        # Инициализация виджета для отображения таблицы
                background-color: #333333;
                color: #ffffff;
            }
            QTableWidget::item:selected {
                background-color: #333333;
                color: #ffffff;
            }
            QTableWidget::item:hover {
                background-color: #333333;
                color: #ffffff;
            }
            QCheckBox::indicator {
                width: 13px;
                height: 13px;
            }
            QCheckBox::indicator:unchecked {
                image: url(/path/to/your/unchecked/image);
            }
            QCheckBox::indicator:checked {
                image: url(/path/to/your/checked/image);
            }
        """)
       # Изменение цвета заголовка столбца
        header = self.table.horizontalHeader()

        header.setStyleSheet("""
            QHeaderView::section {
                background-color: #20B2AA ;
                color: #f0f0f0;
            }
        """)
        # Подключение сигнала к слоту
        self.ip_processed_signal.connect(self.update_table)
        # Устанавливаем основной макет
        self.setLayout(layout)
        # Инициализация атрибута для отслеживания состояния мониторинга
        self.monitor_enabled = False
        # Инициализация таймера для регулярного сканирования
        self.monitor_timer = QTimer(self)
        # Инициализация таймера для периодического выполнения задач мониторинг 
        self.monitor_timer.timeout.connect(self.start_scan_and_get_data)
        self.monitor_timer.setInterval(120 * 1000)  # сек
        
    def update_credentials(self, credentials):
        for model, data in credentials.items():
            self.command_executor.set_credentials(model, data['login'], data['password'])
        self.scan_thread.set_credentials(credentials)

  

    
   # Функция start_stop_monitor: стиль кнопки + запус и отключение мониторинга 
    def start_stop_monitor(self):
        if self.monitor_enabled:
            self.monitor_button.setStyleSheet("background-color: red")
            self.monitor_timer.stop()
        else:
            self.monitor_button.setStyleSheet("background-color: green")
            self.monitor_timer.start()
            self.start_scan_and_get_data()  # Запустим первое сканирование немедленно
        self.monitor_enabled = not self.monitor_enabled

    def get_ip_list(self):
        ip_list = []
        # Чтение IP из файлов
        for idx in range(5):  # Предполагая, что у вас максимум 5 файлов
            filename = f"ip{idx+1}.txt"
            try:
                with open(filename, 'r') as f:
                    ip = f.read().strip()
                    if ip:
                        ip_list.append(ip)
            except FileNotFoundError:
                continue
        return list(set(ip_list))
    
    # Функция start_scan_and_get_data: запус сканирования 
    def start_scan_and_get_data(self):
        
        print("Метод start_scan_and_get_data вызван.")
        ip_list = []
        # Чтение IP из файлов
        for idx in range(5):  # Предполагая, что у вас максимум 5 файлов
            filename = f"ip{idx+1}.txt"
            try:
                with open(filename, 'r') as f:
                    ip = f.read().strip()
                    if ip:
                        ip_list.append(ip)
            except FileNotFoundError:
                continue

        print(f"[DEBUG] Извлечённые IP-адреса: {ip_list}")

        # Если поток уже запущен, нужно его корректно завершить
        if hasattr(self, 'scan_thread') and self.scan_thread.isRunning():
            print("Ожидание завершения текущего сканирования...")
            self.scan_thread.wait()  # Ждём завершения текущего потока

        # По # Подключение сигналов
        ip_list = list(set(ip_list))
         # Передаем учетные данные в ScanThread
        self.scan_thread = ScanThread(ip_list, self.command_executor.credentials)
        print(f"Запуск ScanThread с IP-адресами: {ip_list} и учетными данными: {self.command_executor.credentials}")



        self.scan_thread.start()

        self.scan_thread.ip_processed_signal.connect(self.update_table)
        self.scan_thread.scan_finished_signal.connect(self.scan_finished)
        print(f"[DEBUG] Извлечённые IP-адреса для сканирования: {ip_list}")

  
  
     
    
    
    @pyqtSlot(dict)
    def update_table(self, data):
      
        if not data:
            print("No data provided to update_table.")
            return

        for ip, miner_data in data.items():
            if miner_data is None:
                print(f"No miner model found at {ip}")
                continue

            row, is_new_row = self.find_or_create_row(ip)
            if is_new_row:
                self.global_ip_set.add(ip)  # Добавляем новый IP в глобальное множество

            # Обработка данных в зависимости от модели устройства
            identification_key = miner_data.get('model', miner_data.get('driver', '')).upper()
            if "ANTMINER" in identification_key:
                self.process_antminer_data(ip, miner_data, row)
            elif "AVALON" in identification_key:
                self.process_avalon_data(ip, miner_data, row)
           # elif 'BITMICRO' in identification_key:
              #  self.process_bitmicro_data(ip, miner_data, row)
               # self.process_bitmicro_data(ip, miner_data, row)
            if 'Vnish' in miner_data.get('fw_name', ''):
                self.process_vnish_data(ip, miner_data)
                print(f"Unknown model 'model' for IP {ip}")

             

    # Функция find_or_create_row: ищет дубликаты 
    def find_or_create_row(self, ip):
        for row in range(self.table.rowCount()):
            if self.table.item(row, 1).text() == ip:
                return row, False  # Строка не новая

        self.table.insertRow(0)
        self.table.setItem(0, 1, QTableWidgetItem(ip))
        return 0, True  # Строка новая
        print(f"[DEBUG] Обработка IP {ip}: {'Новая строка' if is_new_row else 'Обновление существующей строки'}")

    @pyqtSlot(list)
    def on_ip_range_saved(self, ip_list):
        print(f"[DEBUG] Получен новый список IP-адресов: {ip_list}")
        self.clear_table_and_dict()  # Вызов метода для очистки

    def clear_table_and_dict(self):
        print("[DEBUG] Очистка таблицы и глобальной переменной")
        self.table.clearContents()
        self.table.setRowCount(0)
        self.global_ip_set.clear()



 

    # Функция convert_string_to_dict: антмайнер   
    def convert_string_to_dict(self, data_str):
        data_list = data_str.split(',')
        data_dict = {}
        for item in data_list:
            parts = item.split('=')
            key = parts[0]
            value = "=".join(parts[1:])
            data_dict[key] = value
        return data_dict
    
    # Функция convert_string_to_dict2: ватсы
    def convert_string_to_dict2(self, data_str):
        if isinstance(data_str, dict):
            return data_str
        try:
            return json.loads(data_str)
        except json.JSONDecodeError:
            return None


        
    def extract_pool_data(self, data):
        """
        Извлекает данные о пулах 1, 2 и 3 из предоставленного словаря данных.
        """
        command_data = data.get('command_data', {})
        pool_string = command_data.get('pools', '')


        pool_items = pool_string.split('|')
        pool_list = []

        for item in pool_items:
            # Убираем запятую в начале, если она есть
            item = item.lstrip(',')

            if not item.startswith("POOL="):
                continue

            pool_number = item.split(',')[0].split('=')[1]

            if pool_number in ["0", "1", "2"]:
                pool_data = item.replace("POOL=", "", 1)
                pool_dict = self.convert_string_to_dict(pool_data)
                if pool_dict:
                    pool_list.append(pool_dict)

        
       

        return pool_list



    
   # Функция process_estats:авалоны 
    def process_estats(self, data):
        """
        Обрабатывает данные estats, возвращая словарь с данными от начала до "POOLS[0]".
        """

        # Extracting the 'response' for VERSION data
        version_data = data.get('response', '')
        # Splitting the version data based on '|'
        version_sections = version_data.split('|')
        # Extracting the first section for VERSION
        version_string = version_sections[0]
        version_items = version_string.split(',')
        version_dict = {}
        for item in version_items:
            parts = item.split('=')
            if len(parts) == 2:
                key, value = parts
                version_dict[key] = value

        # Extracting estats data
        estats_data = data.get('command_data', {}).get('estats', '')
        estats_sections = estats_data.split('|')
        # We are focusing on the first section that starts with 'STATS=0'
        estats_string = next((section for section in estats_sections if section.startswith('STATS=0')), '')
        estats_dict = self.parse_estats_data(estats_string)

        # Remove PVT_T0, PVT_T1, PVT_T2 and everything after it
        keys_after_pvts = False
        for key in list(estats_dict.keys()):
            if key in ['PVT_T0', 'PVT_T1', 'PVT_T2'] or keys_after_pvts:
                del estats_dict[key]
                keys_after_pvts = True

        # Combining version and estats data
        combined_data = {**version_dict, **estats_dict}

        return combined_data

    # Функция parse_section: авалоны 
    def parse_section(self, section):  
        """
        Parses a section and returns a dictionary.
        """
        items = section.split(',')
        parsed_dict = {}
        for item in items:
            parts = item.split('=')
            if len(parts) == 2:
                key, value = parts
                parsed_dict[key] = value
        return parsed_dict

    # Функция parse_estats_data: авалоны 
    def parse_estats_data(self, estats_string):
        """
        Improved function to extract estats data from the provided estats_string.
        """
        # Regular expression patterns
        bracket_pattern = re.compile(r'(\w+)\[(.*?)\]')
        kv_pattern = re.compile(r'(\w+)=([\w.]+)')

        data_dict = {}

        # Extract bracketed values
        for match in bracket_pattern.finditer(estats_string):
            key, value = match.groups()
            if ',' in value or '=' in value:
                # Nested key-values
                nested_data = {}
                for m in kv_pattern.finditer(value):
                    nested_key, nested_value = m.groups()
                    nested_data[nested_key] = nested_value
                data_dict[key] = nested_data
            else:
                data_dict[key] = value

        # Extract regular key-values
        for match in kv_pattern.finditer(estats_string):
            key, value = match.groups()
            if key not in data_dict:
                data_dict[key] = value

        return data_dict

    # Функция extract_bracket_values:авалоны 
    def extract_bracket_values(self, data):
        pattern = re.compile(r'(\w+)\[(\d+\.\d+)]')  # Регулярное выражение для извлечения пар ключ-значение
        return {match.group(1): match.group(2) for match in pattern.finditer(data)}

    # Функция process_bitmicro_data_helper: ватсы 
    def process_bitmicro_data_helper(self, data):
    # Initialize an empty dictionary to hold the processed data
        processed_data = {}

    # Process 'devdetails' section
        devdetails_str = data.get('command_data', {}).get('devdetails', '')
        if devdetails_str:
            try:
                devdetails_data = json.loads(devdetails_str)
                processed_data['devdetails'] = devdetails_data.get('DEVDETAILS', [])
            except json.JSONDecodeError as e:
                print(f"Ошибка декодирования JSON в devdetails: {e}")
            else:
                processed_data['devdetails'] = []

        # Process 'edevs' section
        edevs_str = data.get('command_data', {}).get('edevs', '')
        if edevs_str:
            try:
                edevs_data = json.loads(edevs_str)
                processed_data['edevs'] = edevs_data.get('DEVS', [])
            except json.JSONDecodeError as e:
                print(f"Ошибка декодирования JSON в edevs: {e}")
            else:
                processed_data['edevs'] = []

           # Process 'pools' section
        pools_str = data.get('command_data', {}).get('pools', '')
        if pools_str:
            try:
                pools_data = json.loads(pools_str)
                processed_data['pools'] = pools_data.get('POOLS', [])
            except json.JSONDecodeError as e:
                print(f"Ошибка декодирования JSON в pools: {e}")
            else:
                processed_data['pools'] = []
        
        return processed_data
    
    # Функция process_common_data: ватсы 
    def process_common_data(self, row_for_ip, is_new_row, ip, detailed_stats):
        if is_new_row:
            # Добавляем флажок и IP только для новых строк
            item = QTableWidgetItem()
        # Инициализация виджета для отображения таблицы
            item.setFlags(Qt.ItemIsUserCheckable | Qt.ItemIsEnabled)
            item.setCheckState(Qt.Unchecked)
            self.table.setItem(row_for_ip, 0, item)

            item = QTableWidgetItem(ip)
        # Инициализация виджета для отображения таблицы
            item.setTextAlignment(Qt.AlignCenter)  # Выравниваем текст по центру
            item.setToolTip(ip)  # Устанавливаем всплывающую подсказку
            self.table.setItem(row_for_ip, 1, item)

# Функция process_avalon_data:  обробатыват авалон
    def process_avalon_data(self, ip, data, row):

        if not isinstance(data, dict):
            return

    
        # Обработка данных estats
        estats_results = self.process_estats(data)
       
         # Преобразование строки 'response' в словарь
        response_str = data.get('response', '')
        stats_data = self.convert_string_to_dict(response_str)

        # Combine estats_results and stats_data
        detailed_stats = {**estats_results, **stats_data}
        
          # Извлекаем данные в квадратных скобках и добавляем их в detailed_stats
        bracket_values = self.extract_bracket_values(str(detailed_stats))
        detailed_stats = {**detailed_stats, **bracket_values}

        if not detailed_stats:
            return
   
        # Извлекаем данные о пуле
        pool_data = self.extract_pool_data(data)

        row_for_ip, is_new_row = self.find_or_create_row(ip)  # Распаковываем кортеж
        self.process_common_data(row_for_ip, is_new_row, ip, detailed_stats)


        # Add checkbox only for a new row
        item = QTableWidgetItem()
        item.setFlags(Qt.ItemIsUserCheckable | Qt.ItemIsEnabled)
        item.setCheckState(Qt.Unchecked)
        self.table.setItem(row_for_ip, 0, item)
        

        if is_new_row:
            item = QTableWidgetItem()
            item.setFlags(Qt.ItemIsUserCheckable | Qt.ItemIsEnabled)
            item.setCheckState(Qt.Unchecked)
            self.table.setItem(row_for_ip, 0, item)
    

        if 'PROD' in stats_data:
            self.table.setItem(row_for_ip, 3, QTableWidgetItem(stats_data['PROD']))
            item.setTextAlignment(Qt.AlignCenter)  # Выровнять текст по центру
        
        if 'GHSmm' in detailed_stats:
            item = QTableWidgetItem(detailed_stats['GHSmm'])
            item.setTextAlignment(Qt.AlignCenter)  # Выровнять текст по центру
            self.table.setItem(row_for_ip, 4, item)
     
        if 'GHSavg' in detailed_stats:
            item = QTableWidgetItem(detailed_stats['GHSavg'])
            item.setTextAlignment(Qt.AlignCenter)  # Выровнять текст по центру
            self.table.setItem(row_for_ip, 5, item)

        if 'Elapsed' in detailed_stats:
            elapsed_seconds = int(detailed_stats['Elapsed'])
            elapsed_time = convert_seconds_to_time_string(elapsed_seconds)
            item.setTextAlignment(Qt.AlignCenter)  # Выровнять текст по центру
            self.table.setItem(row_for_ip, 6, QTableWidgetItem(elapsed_time))

        fan_keys = ['Fan1', 'Fan2', 'Fan3', 'Fan4']
        fan_values = [detailed_stats[key] for key in fan_keys if key in detailed_stats]
        fan_str = " / ".join(fan_values)
    

        if fan_str:
            item = QTableWidgetItem(fan_str)
            item.setTextAlignment(Qt.AlignCenter)  # Выровнять текст по центру
            self.table.setItem(row_for_ip, 7, item)

        if 'MTavg' in detailed_stats:
            mtavg_values = [detailed_stats[key] for key in ['MTavg'] if key in detailed_stats]
            mtavg_str = ' / '.join(mtavg_values)
    
            if mtavg_str:
               item = QTableWidgetItem(mtavg_str)
               item.setTextAlignment(Qt.AlignCenter)  # Выровнять текст по центру
               self.table.setItem(row_for_ip, 8, item) 
        
        if 'PS' in detailed_stats:
            ps_values = re.findall(r'\d+', detailed_stats['PS'])  # Используем регулярные выражения для извлечения всех чисел
            last_value = ps_values[-1] if ps_values else 'N/A'  # Берем последнее число или 'N/A', если список пуст
    

            item = QTableWidgetItem(last_value)
            item.setTextAlignment(Qt.AlignCenter)  # Выровнять текст по центру
            item.setToolTip(detailed_stats['PS'])  # Устанавливаем полную строку в качестве всплывающей подсказки
            self.table.setItem(row_for_ip, 9, item)


        if 'Ver' in detailed_stats:
            item = QTableWidgetItem(detailed_stats['Ver'])
            item.setTextAlignment(Qt.AlignCenter)  # Выровнять текст по центру
            self.table.setItem(row_for_ip, 10, item)  


        # Функция get_pool_status_symbol
        def get_pool_status_symbol(status):
            if status == "Alive":
                return "✅"
            elif status in ["Dead", "Stopped"]:
                return "❌"
            else:
                return status

        # If no pool data is found, print a message and return
        if not pool_data:
            return

        # Since pool_data itself is the list of pools, you don't need to extract 'POOLS' from it
        pools_list = pool_data
        if not pools_list:
            return

        # Limit the iteration to only 3 pools
        for i, pool in enumerate(pools_list[:3]):
            pool_url_item = QTableWidgetItem(pool.get('URL', 'N/A'))
            # Инициализация виджета для отображения таблицы
            pool_url_item.setTextAlignment(Qt.AlignCenter)
    
            worker_item = QTableWidgetItem(pool.get('User', 'N/A'))
             # Инициализация виджета для отображения таблицы
            worker_item.setTextAlignment(Qt.AlignCenter)
    
            status_symbol = get_pool_status_symbol(pool.get('Status', 'N/A'))
            status_item = QTableWidgetItem(status_symbol)
            # Инициализация виджета для отображения таблицы
            status_item.setTextAlignment(Qt.AlignCenter)

            base_column = 11 + i * 3  # Only 3 columns per pool now
            self.table.setItem(row_for_ip, base_column, pool_url_item)
            self.table.setItem(row_for_ip, base_column + 1, worker_item)
            self.table.setItem(row_for_ip, base_column + 2, status_item)

    def process_vnish_data(self, ip, data):
        if not isinstance(data, dict):
            print(f"Данные для IP {ip} не являются словарем")
            return

        info_data = data.get('command_data', {}).get('info', {})
        system_data = info_data.get('system', {})
        summary_data = data.get('command_data', {}).get('summary', {})
        miner_data = summary_data.get('miner', {}) if summary_data and summary_data.get('miner') is not None else info_data
        
        
        pools = miner_data.get('pools', []) if miner_data else []

        row_for_ip, is_new_row = self.find_or_create_row(ip)
        # Функция для получения символа статуса пула
        def get_pool_status_symbol(status):
            if status == "active":
                return "✅"
            elif status == "working":
                return "♻️"
            elif status in ["Dead", "Stopped"]:
                return "❌"
            else:
                return status
            
        
        # Add checkbox only for a new row
        item = QTableWidgetItem()
        item.setFlags(Qt.ItemIsUserCheckable | Qt.ItemIsEnabled)
        item.setCheckState(Qt.Unchecked)
        self.table.setItem(row_for_ip, 0, item)
        

        if is_new_row:
            item = QTableWidgetItem()
            item.setFlags(Qt.ItemIsUserCheckable | Qt.ItemIsEnabled)
            item.setCheckState(Qt.Unchecked)
            self.table.setItem(row_for_ip, 0, item)

       
       # Обработка данных из info
        if info_data:
            if 'platform' in info_data and 'install_type' in info_data and 'build_time' in info_data:
                platform_info = f"{info_data.get('platform', '')}/{info_data.get('install_type', '')}/{info_data.get('build_time', '')}"
                platform_item = QTableWidgetItem(platform_info)
                platform_item.setTextAlignment(Qt.AlignCenter)
                self.table.setItem(row_for_ip, 10, platform_item)
  
            if 'uptime' in system_data:
                uptime_item = QTableWidgetItem(system_data['uptime'])
                uptime_item.setTextAlignment(Qt.AlignCenter)
                self.table.setItem(row_for_ip, 6, uptime_item)
            
            miner_info = ""
            if 'miner' in miner_data:
                miner_info += miner_data['miner']

            if 'fw_name' in miner_data:
                miner_info += f" {miner_data['fw_name']}"

            if 'fw_version' in miner_data:
                miner_info += f" {miner_data['fw_version']}"

            if miner_info:
                miner_item = QTableWidgetItem(miner_info)
                miner_item.setTextAlignment(Qt.AlignCenter)
                self.table.setItem(row_for_ip, 3, miner_item)

        # Обработка данных из summary
        if miner_data:
            if 'miner_type' in miner_data:
                miner_type_item = QTableWidgetItem(miner_data['miner_type'])
                miner_type_item.setTextAlignment(Qt.AlignCenter)
                self.table.setItem(row_for_ip, 3, miner_type_item)

            if 'hr_average' in miner_data:
                hr_average_item = QTableWidgetItem(str(miner_data['hr_average']))
                hr_average_item.setTextAlignment(Qt.AlignCenter)
                self.table.setItem(row_for_ip, 4, hr_average_item)

            if 'hr_realtime' in miner_data:
                hr_realtime_item = QTableWidgetItem(str(miner_data['hr_realtime']))
                hr_realtime_item.setTextAlignment(Qt.AlignCenter)
                self.table.setItem(row_for_ip, 5, hr_realtime_item)

            if 'cooling' in miner_data and 'fans' in miner_data['cooling']:
                fan_speeds = '/'.join(str(fan['rpm']) for fan in miner_data['cooling']['fans'])
                fan_speeds_item = QTableWidgetItem(fan_speeds)
                fan_speeds_item.setTextAlignment(Qt.AlignCenter)
                self.table.setItem(row_for_ip, 7, fan_speeds_item)
   
            if 'chip_temp' in miner_data:
                chip_temp = f"{miner_data['chip_temp']['max']}/{miner_data['chip_temp']['min']}"
                chip_temp_item = QTableWidgetItem(chip_temp)
                chip_temp_item.setTextAlignment(Qt.AlignCenter)
                self.table.setItem(row_for_ip, 8, chip_temp_item)
  
            if 'power_consumption' in miner_data:
                power_consumption_item = QTableWidgetItem(str(miner_data['power_consumption']))
                power_consumption_item.setTextAlignment(Qt.AlignCenter)
                self.table.setItem(row_for_ip, 9, power_consumption_item)

            # Обработка данных пула
        for i, pool in enumerate(pools[:3]):  # Проходим только по первым трем пулам
            base_column = 11 + i * 3
    
            self.table.setItem(row_for_ip, base_column, QTableWidgetItem(pool.get('url', 'no data')))
            self.table.setItem(row_for_ip, base_column + 1, QTableWidgetItem(pool.get('user', 'no data')))
      
            status_symbol = get_pool_status_symbol(pool.get('status', 'no data'))
            status_item = QTableWidgetItem(status_symbol)
            status_item.setTextAlignment(Qt.AlignCenter)
            self.table.setItem(row_for_ip, base_column + 2, status_item)

        # Добавить пустые значения для оставшихся пулов, если они не представлены
        for j in range(len(pools), 3):
            base_column = 11 + j * 3
            print(f"Добавление 'no data' для пула {j}")
            self.table.setItem(row_for_ip, base_column, QTableWidgetItem("no data"))
            self.table.setItem(row_for_ip, base_column + 1, QTableWidgetItem("no data"))
            self.table.setItem(row_for_ip, base_column + 2, QTableWidgetItem("no data"))



 # Функция process_antminer_data:обробатывает антмайнер сток + вниш 17 с9 л3 
    def process_antminer_data(self, ip, data, row):
       
        # Check if data is a dictionary
        if not isinstance(data, dict):
            return
        
        
      
        # Преобразование строки 'response' в словарь
        response_str = data.get('response', '')
        stats_data = self.convert_string_to_dict(response_str)
 
        detailed_stats = stats_data
   
        if not detailed_stats:
            return

        # Extracting pool data
        pool_data = self.extract_pool_data(data)

        row_for_ip, is_new_row = self.find_or_create_row(ip)  # Распаковываем кортеж
        self.process_common_data(row_for_ip, is_new_row, ip, detailed_stats)

        # Add checkbox only for a new row
        item = QTableWidgetItem()
        item.setFlags(Qt.ItemIsUserCheckable | Qt.ItemIsEnabled)
        item.setCheckState(Qt.Unchecked)
        self.table.setItem(row_for_ip, 0, item)
       

        if is_new_row:
            item = QTableWidgetItem()
            item.setFlags(Qt.ItemIsUserCheckable | Qt.ItemIsEnabled)
            item.setCheckState(Qt.Unchecked)
            self.table.setItem(row_for_ip, 0, item)
    

        # Обработка данных из stats
        if 'Type' in stats_data:
            # Извлечение количества активных чипов на каждой плате
            chain_acn1 = int(stats_data.get('chain_acn1', 0))
            chain_acn2 = int(stats_data.get('chain_acn2', 0))
            chain_acn3 = int(stats_data.get('chain_acn3', 0))

        # Выбор максимального количества активных чипов
            max_chips_count = max(chain_acn1, chain_acn2, chain_acn3)
  
        # Формирование строки с моделью и максимальным количеством чипов
            model_with_chips = f"{stats_data['Type']} ({max_chips_count})"

        # Установка значения в таблицу
            model_item = QTableWidgetItem(model_with_chips)
            model_item.setTextAlignment(Qt.AlignCenter)
            self.table.setItem(row_for_ip, 3, model_item)
       
        if 'GHS av' in detailed_stats:
            item = QTableWidgetItem(str(detailed_stats['GHS av']))
            item.setTextAlignment(Qt.AlignCenter)  # Выровнять текст по центру
            self.table.setItem(row_for_ip, 4, item)

    
        if 'GHS 5s' in detailed_stats:
            item = QTableWidgetItem(str(detailed_stats['GHS 5s']))
            item.setTextAlignment(Qt.AlignCenter)  # Выровнять текст по центру
            self.table.setItem(row_for_ip, 5, item)

        if 'Elapsed' in detailed_stats:
            elapsed_seconds = int(detailed_stats['Elapsed'])
            elapsed_time = convert_seconds_to_time_string(elapsed_seconds)
            item.setTextAlignment(Qt.AlignCenter)  # Выровнять текст по центру

            self.table.setItem(row_for_ip, 6, QTableWidgetItem(elapsed_time))

        if 'fan_num' in detailed_stats:
            fan_num = int(detailed_stats['fan_num'])
            fans = []
            for i in range(1, fan_num + 1):
                fan_key = f"fan{i}"
                if fan_key in detailed_stats:
                    fans.append(str(detailed_stats[fan_key]))
            fans_str = "/".join(fans)
            item = QTableWidgetItem(fans_str)
            item.setTextAlignment(Qt.AlignCenter)
            self.table.setItem(row_for_ip, 7, item)
            self.table.setColumnWidth(7, 125)

        if 'temp2_1' in detailed_stats and 'temp2_2' in detailed_stats and 'temp2_3' in detailed_stats:
            temps = [detailed_stats['temp2_1'], detailed_stats['temp2_2'], detailed_stats['temp2_3']]
            item = QTableWidgetItem(f"{temps[0]}/{temps[1]}/{temps[2]}")
            item.setTextAlignment(Qt.AlignCenter)
            self.table.setItem(row_for_ip, 8, item)

        # Извлечение и сложение значений
        chain_consumption_keys = ['chain_consumption1', 'chain_consumption2', 'chain_consumption3']
        chain_consumption_values = [int(detailed_stats[key]) for key in chain_consumption_keys if key in detailed_stats]
        total_chain_consumption = sum(chain_consumption_values)

            # Отображение полученного значения в таблице
        if total_chain_consumption:
            item = QTableWidgetItem(str(total_chain_consumption))
            item.setTextAlignment(Qt.AlignCenter)  # Выровнять текст по центру
            self.table.setItem(row_for_ip, 9, item)  # Замените COLUMN_INDEX на соответствующий индекс столбца

        if 'CompileTime' in stats_data:
            self.table.setItem(row_for_ip, 10, QTableWidgetItem(stats_data['CompileTime']))
        
        
        def get_pool_status_symbol(status):
            if status == "Alive":
                return "✅"
            elif status in ["Dead", "Stopped"]:
                return "❌"
            else:
                return status

        # If no pool data is found, print a message and return
        if not pool_data:
            return

        # Since pool_data itself is the list of pools, you don't need to extract 'POOLS' from it
        pools_list = pool_data
        if not pools_list:
           return

       # Limit the iteration to only 3 pools
        for i, pool in enumerate(pools_list[:3]):
            pool_url_item = QTableWidgetItem(pool.get('URL', 'N/A'))
            pool_url_item.setTextAlignment(Qt.AlignCenter)
            worker_item = QTableWidgetItem(pool.get('User', 'N/A'))
            worker_item.setTextAlignment(Qt.AlignCenter)
            status_symbol = get_pool_status_symbol(pool.get('Status', 'N/A'))
            status_item = QTableWidgetItem(status_symbol)
            status_item.setTextAlignment(Qt.AlignCenter)

            base_column = 11 + i * 3  # Only 3 columns per pool now
            self.table.setItem(row_for_ip, base_column, pool_url_item)
            self.table.setItem(row_for_ip, base_column + 1, worker_item)
            self.table.setItem(row_for_ip, base_column + 2, status_item)


    def process_bitmicro_data(self, ip, data, row):
        
        detailed_stats = {}

        # Инициализация response_str
        response_str = data.get('response', '')

        # Преобразование response_str в словарь
        stats_data = self.convert_string_to_dict(response_str)

        if not isinstance(stats_data, dict):
            return

        
        
        # Извлечение command_data
        command_data_str = data.get('command_data', '')
        command_data = self.convert_string_to_dict2(command_data_str)

        # Вызов process_bitmicro_data
        processed_data = self.process_bitmicro_data_helper(data)

        row_for_ip, is_new_row = self.find_or_create_row(ip)  # Распаковываем кортеж
        self.process_common_data(row_for_ip, is_new_row, ip, detailed_stats)


        # Add checkbox only for a new row
        item = QTableWidgetItem()
        item.setFlags(Qt.ItemIsUserCheckable | Qt.ItemIsEnabled)
        item.setCheckState(Qt.Unchecked)
        self.table.setItem(row_for_ip, 0, item)
        

         # IP
        if is_new_row:
            item = QTableWidgetItem(ip)
            item.setTextAlignment(Qt.AlignCenter)  # Align text center
            item.setToolTip(ip)  # Set tooltip
            self.table.setItem(row_for_ip, 1, item)
        

        # Model (3rd column)
        if 'devdetails' in processed_data:
            model_data = processed_data['devdetails'][0].get('Model', '')
            # Добавьте 'WhatsMiner' перед моделью
            full_model_data = f'WhatsMiner {model_data}' if model_data else 'WhatsMiner'
            item = QTableWidgetItem(str(full_model_data))
            item.setTextAlignment(Qt.AlignCenter)
            self.table.setItem(row_for_ip, 3, item)
            detailed_stats['Model'] = full_model_data



       # MHS 5s (4th column)
        if 'summary' in processed_data:
            mhs_5s_mhs = processed_data['summary'].get('MHS 5s', 0)  # Здесь, я предполагаю, что если данных нет, то значение равно 0
            mhs_5s_ghs = mhs_5s_mhs / 1e3  # Преобразование в гигахэши
            item = QTableWidgetItem(f"{mhs_5s_ghs:.2f} GH/s")  # Округление до двух знаков после запятой и добавление "GH/s"
            item.setTextAlignment(Qt.AlignCenter)
            self.table.setItem(row_for_ip, 4, item)
            detailed_stats['MHS_5s'] = mhs_5s_ghs

         # HS RT (5th column)
        hs_rt_mhs = processed_data['summary'].get('HS RT', 0)  # Здесь, я предполагаю, что если данных нет, то значение равно 0
        hs_rt_ghs = hs_rt_mhs / 1e3  # Преобразование в гигахэши
        item = QTableWidgetItem(f"{hs_rt_ghs:.2f} GH/s")  # Округление до двух знаков после запятой и добавление "GH/s"
        item.setTextAlignment(Qt.AlignCenter)
        self.table.setItem(row_for_ip, 5, item)
        detailed_stats['HS_RT'] = hs_rt_ghs


        
        if 'Elapsed' in processed_data.get('summary', {}):
            elapsed_time = processed_data['summary']['Elapsed']
            elapsed_time = convert_seconds_to_time_string(elapsed_time)
            item = QTableWidgetItem(str(elapsed_time))
            item.setTextAlignment(Qt.AlignCenter)
            self.table.setItem(row_for_ip, 6, item)  # Предположим, что 5 - это индекс колонки "Время работы"
            detailed_stats['Elapsed'] = elapsed_time

        # Fan Speed (7th column)
        fan_in = processed_data['summary'].get('Fan Speed In', '')
        fan_out = processed_data['summary'].get('Fan Speed Out', '')
        item = QTableWidgetItem(f"{fan_in}/{fan_out}")
        item.setTextAlignment(Qt.AlignCenter)
        self.table.setItem(row_for_ip, 7, item)
        detailed_stats['Fan_In'] = fan_in
        detailed_stats['Fan_Out'] = fan_out

    
        # Temperatures (10th column)
        if 'edevs' in processed_data:
            temps = [str(dev.get('Temperature', '')) for dev in processed_data['edevs']]
            detailed_stats['Temps'] = temps
            item = QTableWidgetItem('/'.join(temps))
            item.setTextAlignment(Qt.AlignCenter)
            self.table.setItem(row_for_ip, 8, item)


        # Power (13th column)
        power = processed_data['summary'].get('Power', '')
        item = QTableWidgetItem(str(power))
        item.setTextAlignment(Qt.AlignCenter)
        self.table.setItem(row_for_ip, 9, item)
        detailed_stats['Power'] = power

        
        # Получение данных пула
        pool_data = processed_data.get('pools', [])
        detailed_stats['Pools'] = pool_data

    
        # Функция для получения символа статуса пула
        def get_pool_status_symbol(status):
            if status == "Alive":
                return "✅"
            elif status in ["Dead", "Stopped"]:
                return "❌"
            else:
                return status

         # Limit the iteration to only 3 pools
        for i, pool in enumerate(pool_data[:3]):
            pool_url_item = QTableWidgetItem(pool.get('URL', 'N/A'))
            pool_url_item.setTextAlignment(Qt.AlignCenter)
            worker_item = QTableWidgetItem(pool.get('User', 'N/A'))
            worker_item.setTextAlignment(Qt.AlignCenter)
            status_symbol = get_pool_status_symbol(pool.get('Status', 'N/A'))
            status_item = QTableWidgetItem(status_symbol)
            status_item.setTextAlignment(Qt.AlignCenter)

            base_column = 11 + i * 3  # Only 3 columns per pool now
            self.table.setItem(row_for_ip, base_column, pool_url_item)
            self.table.setItem(row_for_ip, base_column + 1, worker_item)
            self.table.setItem(row_for_ip, base_column + 2, status_item)
      
      

  
    def save_ips_to_file(self):
        filename, _ = QFileDialog.getSaveFileName(self, "Save IPs", "", "Text Files (*.txt)")
        if filename:
            with open(filename, 'w') as file:
                for row in range(self.table.rowCount()):
                    ip_item = self.table.item(row, 1)  # Предполагая, что IP адрес находится в столбце с индексом 2
                    if ip_item:
                        file.write(ip_item.text() + '\n')


    
# Функция scan_finished: вывод сообщения о завершении 
    def scan_finished(self, row_count):
        print(f"Завершение работы потока ScanThread {id(self)}")
        QMessageBox.information(self, 'Сканирование завершено', f'Найдено {row_count} устройств.')
        # В ScanTab после завершения сканирования
        self.update_control_tab_signal.emit(self.collect_data_for_control_tab())    


# Функция open_web_interface: открывает айпи по нажатию 
    def open_web_interface(self, row, col):
        # Check if the clicked cell is the IP cell
        if col == 1:
            item = self.table.item(row, col)
            if item:
                ip = item.text()
                # Open the web interface
                webbrowser.open(f"http://{ip}")


    # Функция для сбора данных из таблицы
    def collect_data_for_control_tab(self):
        data_for_control_tab = []
        for row in range(self.table.rowCount()):
            ip = self.table.item(row, 1).text() if self.table.item(row, 1) else ""
            model = self.table.item(row, 3).text() if self.table.item(row, 3) else ""
            compile_time = self.table.item(row, 10).text() if self.table.item(row, 10) else ""
            data_for_control_tab.append((ip, model, compile_time))
        return data_for_control_tab
    

   # Функция save_values: Отвечает за ... (детальное описание)
    def save_values(self):
        self.asic_values = []
        for row in range(self.table.rowCount()):
            item = self.table.item(row, 0)
            if item is not None:
                self.asic_values.append(item.text())


      # Функция hideEvent: Отвечает за ... (детальное описание)
    def hideEvent(self, event):
        super().hideEvent(event)
        self.save_values()

# Функция save_header_state: Отвечает за ... (детальное описание)
    def save_header_state(self):
        header = self.table.horizontalHeader()
        state = header.saveState()
        with open('header_state.pkl', 'wb') as f:
            pickle.dump(state, f)

# Функция load_header_state: Отвечает за ... (детальное описание)
    def load_header_state(self):
        if os.path.exists('header_state.pkl'):
            with open('header_state.pkl', 'rb') as f:
                state = pickle.load(f)
                self.table.horizontalHeader().restoreState(state)

    # Функция header_checkbox_state_changed: Отвечает за ... (детальное описание)
    def header_checkbox_state_changed(self, state):
        # Set the state of all checkboxes in the column
        for i in range(self.table.rowCount()):
            item = self.table.item(i, 0)
            if item is not None:
               item.setCheckState(state)
      
 

   


     # Функция load_data: Отвечает за ... (детальное описание)
    def load_data(self):
        self.data = 'Data for ScanTab'

# Функция save_data: Отвечает за ... (детальное описание)
    def save_data(self):
        print(f"Saving data: {self.data}")           







       