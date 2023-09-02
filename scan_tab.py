from PyQt5.QtWidgets import (QAbstractItemView, QCheckBox, QDialog, QFileDialog, QHBoxLayout, 
                             QHeaderView, QMessageBox, QLabel, QProgressBar, QPushButton, QScrollArea, 
                             QSizePolicy, QSpacerItem, QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QTimer, QUrl
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
from monitor_tab import MonitorTab
from PyQt5.QtWidgets import QTableWidgetItem






class ScanTab(QWidget):
    update_table_signal = pyqtSignal(dict, int)
    monitoring_data_signal = pyqtSignal(dict)  # Сигнал для передачи данных мониторинга
    ip_processed_signal = pyqtSignal(dict, int)



    def __init__(self, parent=None):
        super(ScanTab, self).__init__(parent)

        self.scan_thread = None

        self.miner_rows = {}
        self.open_ports = {}
        self.row_count = 0

        self.ip_order = []  # Список для отслеживания порядка IP-адресов

         # Create MonitorTab instance
        self.monitor_tab = MonitorTab(scan_tab_reference=self)
       

        # Monitoring state
        self.monitor_enabled = False

       
        layout = QVBoxLayout()

        button_layout = QHBoxLayout()
        button_layout.setContentsMargins(0, -10, 0, 0)

        self.scan_button = QPushButton("Scan")
        self.scan_button.clicked.connect(self.start_scan_and_get_data)

        self.monitor_button = QPushButton("Monitor")
        self.monitor_button.clicked.connect(self.start_stop_monitor)

        self.scan_timer = QTimer(self)
        self.scan_timer.timeout.connect(self.start_scan_and_get_data)

        self.asic_search_button = QPushButton("ASIC Save")

        self.update_button = QPushButton("Update")
        self.update_button.clicked.connect(self.show_upgrade_dialog)

        self.setStyleSheet("""
            QPushButton { 
                color: white;
                border: 2px solid #555555;
                border-radius: 10px;
                background: #05B8CC;
                padding: 5px;
            }
            QPushButton:hover {
                background: #555555;
            }
            QPushButton:pressed {
                background: #777777;
            }
        """)

       
        button_layout.addWidget(self.scan_button)
        button_layout.addWidget(self.monitor_button)
        button_layout.addWidget(self.asic_search_button)
        button_layout.addWidget(self.update_button)
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

        self.table = QTableWidget(254, 34, self)
        self.table.setSortingEnabled(True)

        self.table.horizontalHeader().setSectionsMovable(True)
        self.load_header_state()


        self.table.verticalHeader().setVisible(False)


         # Сделать таблицу нередактируемой
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)

        self.table.setFixedWidth(3000)
        self.scrollArea = QScrollArea(self)
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

        self.scrollArea.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOn)
        # Connect cell click event to a method
        self.table.cellClicked.connect(self.open_web_interface)

        layout.addWidget(self.scrollArea)

        self.table.setHorizontalHeaderLabels(["", "IP", "Status", "Type", "Ths avg", "Ths rt", "Elapsed", "fan_speed", "%pwm%", "Temp PCB", "Temp Chip" , "CompileTime", "power", "V/Mhz", "URL1", "User1", "Status1", "LStime1", "URL2", "User2", "Status2", "LStime2", "URL3", "User3", "Status3", "LStime3", ])
        self.table.setColumnWidth(0, 30)
        self.table.setColumnWidth(1, 100)
        self.table.setColumnWidth(2, 50)
        self.table.setColumnWidth(8, 50)
        self.table.setColumnWidth(13, 80)
        self.table.setColumnWidth(8, 50)
        self.table.setColumnWidth(16, 50)
        self.table.setColumnWidth(20, 50)
        self.table.setColumnWidth(24, 50)
        self.table.setColumnWidth(28, 50)
        self.table.setColumnWidth(32, 50)
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
                background-color: #424242;
                color: #f0f0f0;
            }
        """)
        # Подключение сигнала к слоту
        self.ip_processed_signal.connect(self.update_table)
        self.update_table_signal.connect(self.update_table)
       


        # Устанавливаем основной макет
        self.setLayout(layout)

    def show_upgrade_dialog(self):
        upgrade_dialog = UpgradeDialog(self)
        upgrade_dialog.exec_()

    
    def start_stop_monitor(self):
        """Start or stop the monitoring process."""
        if self.monitor_enabled:
            self.monitor_button.setStyleSheet("background-color: red")
            self.monitor_tab.stop_monitor()
        else:
            self.monitor_button.setStyleSheet("background-color: green")
            self.monitor_tab.start_monitor()
        self.monitor_enabled = not self.monitor_enabled

    def start_scan_and_get_data(self):
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
        # Удаление дубликатов
        ip_list = list(set(ip_list))
        self.scan_thread = ScanThread(ip_list)
        
         # Подключение сигналов
        self.scan_thread.ip_processed_signal.connect(self.update_table)


        self.scan_thread.monitoring_data_signal.connect(self.monitoring_data_signal.emit)
        #  self.scan_thread.finished.connect(self.on_scan_completed)
    
        self.scan_thread.start()

        print("Конец функции start_scan_and_get_data")
  


    def find_or_create_row(self, ip):
        # Поиск строки с указанным IP-адресом
        for row in range(self.table.rowCount()):
            item = self.table.item(row, 1)
            if item and item.text() == ip:
                return row
        # Если строка не найдена, создание новой строки
        row_for_ip = 0
        self.table.insertRow(row_for_ip)
        return row_for_ip
    



    @pyqtSlot(dict)
    def update_table(self, data):
        print("update_table called!")
        print("Data:", data)

        if not data:
            print("No data provided to update_table.")
            return

        for ip, miner_data in data.items():
            print(f"Processing data for IP {ip}: {miner_data}")

            model = miner_data.get('model', '').upper()
            if not model:
                print(f"No model found for IP {ip}. Skipping...")
                continue

            print(f"Identified model for IP {ip} is: {model}")
    
            if "ANTMINER" in model:
                print(f"IP {ip} is an Antminer. Processing...")
                self.process_antminer_data(ip, miner_data)
            elif "AVALON" in model:
                print(f"IP {ip} is an Avalon. Processing...")
                self.process_avalon_data(ip, miner_data)
            else:
                print(f"Unknown model '{model}' for IP {ip}")




    def convert_string_to_dict(self, data_str):
        data_list = data_str.split(',')
        data_dict = {}
        for item in data_list:
            parts = item.split('=')
            key = parts[0]
            value = "=".join(parts[1:])
            data_dict[key] = value
        return data_dict
    

    def extract_pool_data(self, data):
        """
        Extracts pool data from the provided data dictionary.
        """
        command_data = data.get('command_data', {})
        pool_string = command_data.get('pools', '')
    
        # Print the entire pool string for debugging
        print(f"Entire pool_string: {pool_string}")  # Для диагностики
    
        pool_items = pool_string.split('|')
        pool_list = []

        for item in pool_items:
            if not item.startswith("POOL="):  # Проверяем, чтобы элемент начинался с "POOL="
                continue
            pool_dict = self.convert_string_to_dict(item.replace("POOL=", ""))  # Удаляем "POOL=" из начала строки
            if pool_dict:
                pool_list.append(pool_dict)

        print(f"Returning pool_list: {pool_list}")  # Для диагностики
        return pool_list


 



    def extract_stats_data(self, data):
        """
        Extracts statistics data from the provided data dictionary.
        """
        estats_data = data.get('estats', '')
  
        # Find the start of the stats section for Avalon
        start_index_avalon = estats_data.find('STATS=0,ID=AVA100,Elapsed')

        start_index = start_index_avalon

        # If the keyword isn't found, return an empty dict
        if start_index == -1:
            return {}
  
        # Extract everything from the start keyword to the next pipe character
        stats_string = estats_data[start_index:].split('|')[0]
  
        print(f"Extracted stats_string: {stats_string}")  # Diagnostic print
  
        stats_items = stats_string.split(',')
        stats_dict = {}
        for item in stats_items:
            print(f"Processing item: {item}")  # Diagnostic print
            parts = item.split('=')
            if len(parts) == 2:
                key, value = parts
                stats_dict[key] = value

        # Extracting additional keys specific for Avalon
        avalon_keys = ['GHSspd', 'GHSmm', 'GHSavg', 'Temp', 'Fan1', 'Fan2', 'Fan3', 'Fan4', 'Elapsed', 'DH', 'Vo', 'PS', 'Freq']
        for key in avalon_keys:
            stats_dict[key] = stats_dict.get(key, 'N/A')  # Use 'N/A' as default value if the key is not found
   
        print(f"Returning stats_dict: {stats_dict}")  # Diagnostic print
        return stats_dict





    def extract_version_data(self, data):
        """
        Extracts version data from the provided data dictionary.
        """
        version_data = data.get('model', '')
        version_items = version_data.split('|')
        version_dict = {}
        for item in version_items:
            parts = item.split('=')
            if len(parts) == 2:
                key, value = parts
                version_dict[key] = value

        print(f"Returning version_dict: {version_dict}")  # Diagnostic print
        return version_dict



    def process_avalon_data(self, ip, data):
        print(f"--- Start Processing Avalon data for IP {ip} ---")
    
        print(f"Received data for IP {ip}: {data}")

        # Check if data is a dictionary
        if not isinstance(data, dict):
            print(f"Data for IP {ip} is not a dictionary. Received data: {data}")
            return  # Exit the function if data is not a dictionary

        row_for_ip = self.find_or_create_row(ip)
        print(f"Row for IP {ip}: {row_for_ip}")

        # Extracting statistics data
        stats_data = self.extract_stats_data(data)
        print(f"Extracted stats data for IP {ip}: {stats_data}")

        detailed_stats = stats_data if stats_data else {}
        if not detailed_stats:
            print(f"No detailed stats found for IP {ip}. Exiting function.")
            return

        # Extracting pool data
        pool_data, pool_info = self.extract_pool_data(data)
        print(f"Extracted pool data for IP {ip}: {pool_data}")


        def add_table_item(row, col, value, alignment=Qt.AlignCenter):
            """Helper function to reduce redundancy."""
            item = QTableWidgetItem(str(value))
            item.setTextAlignment(alignment)
            self.table.setItem(row, col, item)
            print(f"Added table item at row {row}, col {col} with value {value}")


            # Add checkbox only for a new row
            item = QTableWidgetItem()
            item.setFlags(Qt.ItemIsUserCheckable | Qt.ItemIsEnabled)
            item.setCheckState(Qt.Unchecked)
            self.table.setItem(row_for_ip, 0, item)
            print(f"Added checkbox for IP {ip} at row {row_for_ip}")


        # Type ID0
        if 'PROD' in data:
            add_table_item(row_for_ip, 3, data['PROD'])

        # GHSavg
        if 'GHSavg' in detailed_stats:
            add_table_item(row_for_ip, 4, detailed_stats['GHSavg'])

        # GHSmm
        if 'GHSmm' in detailed_stats:
            add_table_item(row_for_ip, 5, detailed_stats['GHSmm'])

        # Elapsed
        if 'Elapsed' in detailed_stats:
            elapsed_seconds = int(detailed_stats['Elapsed'])
            elapsed_time = convert_seconds_to_time_string(elapsed_seconds)
            add_table_item(row_for_ip, 6, elapsed_time)

        # Fan1 - Fan4
        for i in range(1, 5):
            fan_key = f"Fan{i}"
            if fan_key in detailed_stats:
                add_table_item(row_for_ip, 7 + i - 1, detailed_stats[fan_key])

        # FanR
        if 'FanR' in detailed_stats:
            add_table_item(row_for_ip, 8, detailed_stats['FanR'])

        # MTavg
        if 'MTavg' in detailed_stats:
            add_table_item(row_for_ip, 10, detailed_stats['MTavg'])

        # PS
        if 'PS' in detailed_stats:
            add_table_item(row_for_ip, 11, detailed_stats['PS'])

        # Check for Avalon ID and if we have data from the pool file
        detailed_stats = stats_data[1] if len(stats_data) > 1 else {}
        if 'ID' in detailed_stats and detailed_stats['ID'].startswith('AVA') and pool_info:
            for pool in pool_info:
                pool_number = pool.get('POOL')
                base_column = 14 + pool_number * 4

                add_table_item(row_for_ip, base_column, pool.get('URL', 'N/A'))
                add_table_item(row_for_ip, base_column + 1, pool.get('User', 'N/A'))
                add_table_item(row_for_ip, base_column + 2, pool.get('Status', 'N/A'))
                add_table_item(row_for_ip, base_column + 3, pool.get('Last Share Time', 'N/A'))
         

            print(f"--- Finished Processing Avalon data for IP {ip} ---")


    def process_antminer_data(self, ip, data):
        print(f"--- Start Processing Antminer data for IP {ip} ---")

        # Check if data is a dictionary
        if not isinstance(data, dict):
            print(f"Error: Data for IP {ip} is not a dictionary. Received data: {data}")
            return

        row_for_ip = self.find_or_create_row(ip)
        print(f"Row for IP {ip}: {row_for_ip}")

        # Преобразование строки 'response' в словарь
        response_str = data.get('response', '')
        stats_data = self.convert_string_to_dict(response_str)

        print(f"Extracted stats data for IP {ip}: {stats_data}")

        detailed_stats = stats_data
   
        if not detailed_stats:
            print(f"No detailed stats found for IP {ip}. Exiting function.")
            return

        # Extracting pool data
        pool_data = self.extract_pool_data(data)
        print(f"Extracted pool data for IP {ip}: {pool_data}")

        # Add checkbox only for a new row
        item = QTableWidgetItem()
        item.setFlags(Qt.ItemIsUserCheckable | Qt.ItemIsEnabled)
        item.setCheckState(Qt.Unchecked)
        self.table.setItem(row_for_ip, 0, item)
        print(f"Checkbox added for IP {ip} at row {row_for_ip}")

        # IP
        item = QTableWidgetItem(ip)
        item.setTextAlignment(Qt.AlignCenter)  # Align text center
        item.setToolTip(ip)  # Set tooltip
        self.table.setItem(row_for_ip, 1, item)
        print(f"IP address {ip} set in the table for row {row_for_ip}")

        if 'Type' in stats_data:
            self.table.setItem(row_for_ip, 3, QTableWidgetItem(stats_data['Type']))
            item.setTextAlignment(Qt.AlignCenter)  # Выровнять текст по центру

        # GHS av
        if 'GHS av' in detailed_stats:
            item = QTableWidgetItem(str(detailed_stats['GHS av']))
            item.setTextAlignment(Qt.AlignCenter)  # Выровнять текст по центру
            self.table.setItem(row_for_ip, 4, item)

        # GHS 5s
        if 'GHS 5s' in detailed_stats:
            item = QTableWidgetItem(str(detailed_stats['GHS 5s']))
            item.setTextAlignment(Qt.AlignCenter)  # Выровнять текст по центру
            self.table.setItem(row_for_ip, 5, item)

        if 'Elapsed' in detailed_stats:
            elapsed_seconds = int(detailed_stats['Elapsed'])
            elapsed_time = convert_seconds_to_time_string(elapsed_seconds)
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

        if 'temp1' in detailed_stats and 'temp2' in detailed_stats and 'temp3' in detailed_stats:
            temps = [detailed_stats['temp1'], detailed_stats['temp2'], detailed_stats['temp3']]
            item = QTableWidgetItem(f"{temps[0]}/{temps[1]}/{temps[2]}")
            item.setTextAlignment(Qt.AlignCenter)
            self.table.setItem(row_for_ip, 9, item)

        if 'temp2_1' in detailed_stats and 'temp2_2' in detailed_stats and 'temp2_3' in detailed_stats:
            temps = [detailed_stats['temp2_1'], detailed_stats['temp2_2'], detailed_stats['temp2_3']]
            item = QTableWidgetItem(f"{temps[0]}/{temps[1]}/{temps[2]}")
            item.setTextAlignment(Qt.AlignCenter)
            self.table.setItem(row_for_ip, 10, item)

        if 'CompileTime' in stats_data:
            self.table.setItem(row_for_ip, 11, QTableWidgetItem(stats_data['CompileTime']))

        # Define function to get the pool status symbol
        def get_pool_status_symbol(status):
            if status == "Alive":
                return "✅"
            elif status in ["Dead", "Stopped"]:
                return "❌"
            else:
                return status

        # If no pool data is found, print a message and return
        if not pool_data:
            print(f"Missing pools_data for IP {ip}")
            return

        # Since pool_data itself is the list of pools, you don't need to extract 'POOLS' from it
        pools_list = pool_data
        if not pools_list:
            print(f"Missing POOLS list for IP {ip}")
            return

        for i, pool in enumerate(pools_list):
            pool_url_item = QTableWidgetItem(pool.get('URL', 'N/A'))
            pool_url_item.setTextAlignment(Qt.AlignCenter)
            worker_item = QTableWidgetItem(pool.get('User', 'N/A'))
            worker_item.setTextAlignment(Qt.AlignCenter)
            status_symbol = get_pool_status_symbol(pool.get('Status', 'N/A'))
            status_item = QTableWidgetItem(status_symbol)
            status_item.setTextAlignment(Qt.AlignCenter)
            last_share_time_item = QTableWidgetItem(pool.get('Last Share Time', 'N/A'))
            last_share_time_item.setTextAlignment(Qt.AlignCenter)

            base_column = 14 + i * 4
            self.table.setItem(row_for_ip, base_column, pool_url_item)
            self.table.setItem(row_for_ip, base_column + 1, worker_item)
            self.table.setItem(row_for_ip, base_column + 2, status_item)
            self.table.setItem(row_for_ip, base_column + 3, last_share_time_item)



    def open_web_interface(self, row, col):
        # Check if the clicked cell is the IP cell
        if col == 1:
            item = self.table.item(row, col)
            if item:
                ip = item.text()
                # Open the web interface
                webbrowser.open(f"http://{ip}")



    def on_scan_completed(self, open_ports, total_miners):
        # Убрали уведомление об окончании сканирования
        # QMessageBox.information(self, "Scan Finished", f"Scanning finished. Found {total_miners} devices.")
      
       pass  # Пустое тело функции; добавьте здесь другой код, если необходимо



    def save_values(self):
        self.asic_values = []
        for row in range(self.table.rowCount()):
            item = self.table.item(row, 0)
            if item is not None:
                self.asic_values.append(item.text())

    def hideEvent(self, event):
        super().hideEvent(event)
        self.save_values()

    def save_header_state(self):
        header = self.table.horizontalHeader()
        state = header.saveState()
        with open('header_state.pkl', 'wb') as f:
            pickle.dump(state, f)

    def load_header_state(self):
        if os.path.exists('header_state.pkl'):
            with open('header_state.pkl', 'rb') as f:
                state = pickle.load(f)
                self.table.horizontalHeader().restoreState(state)

    def header_checkbox_state_changed(self, state):
        # Set the state of all checkboxes in the column
        for i in range(self.table.rowCount()):
            item = self.table.item(i, 0)
            if item is not None:
               item.setCheckState(state)


    def load_data(self):
        self.data = 'Data for ScanTab'

    def save_data(self):
        print(f"Saving data: {self.data}")           


def convert_seconds_to_time_string(seconds):
    days, remainder = divmod(seconds, 86400)
    hours, remainder = divmod(remainder, 3600)
    minutes, seconds = divmod(remainder, 60)
    return f"{days} d {hours} h {minutes} m {seconds} s"


class UpgradeDialog(QDialog):
    def __init__(self, parent=None):
        super(UpgradeDialog, self).__init__(parent)
        self.label = QLabel(self)
        self.label.move(10, 10)
        self.button = QPushButton('Upgrade', self)
        self.button.move(10, 50)
        self.button.clicked.connect(self.on_upgrade_button_clicked)
        self.setWindowTitle("Firmware Upgrade")
        self.setFixedSize(300, 100)

    def on_upgrade_button_clicked(self):
        firmware_file = QFileDialog.getOpenFileName(self, 'Open Firmware File', '', 'Firmware Files (*.bin)')[0]
        if firmware_file:
            print(f"Upgrading with {firmware_file}.")
            QMessageBox.information(self, "Upgrade", f"Upgrading with {firmware_file}.")
            # Here goes the firmware upgrade code    