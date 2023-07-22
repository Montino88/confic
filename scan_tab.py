from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QSpacerItem, QSizePolicy, QTableWidget, QHeaderView, QAbstractItemView, QCheckBox, QLabel, QProgressBar
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QDialog, QVBoxLayout, QLabel, QPushButton, QFileDialog
from PyQt5.QtWidgets import QLabel
from PyQt5.QtWidgets import QLabel
from PyQt5.QtGui import QPalette, QColor
from PyQt5.QtWidgets import QTableWidgetItem
from PyQt5.QtCore import QThread, pyqtSignal
from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import QTimer
from PyQt5.QtWidgets import QMessageBox
from PyQt5.QtWidgets import QCheckBox
import traceback
from scan_thread import ScanThread
import ipaddress
from PyQt5.QtWidgets import QScrollArea
import json
from PyQt5.QtGui import QColor


class UpgradeDialog(QDialog):
    def __init__(self, parent=None):
        super(UpgradeDialog, self).__init__(parent)

        layout = QVBoxLayout()

        self.label = QLabel("Selected rows: 0")
        layout.addWidget(self.label)

        self.upgrade_button = QPushButton("Start Upgrade")
        self.upgrade_button.clicked.connect(self.upgrade_firmware)
        layout.addWidget(self.upgrade_button)

        self.setLayout(layout)

    def upgrade_firmware(self):
        firmware_file, _ = QFileDialog.getOpenFileName(self, "Open Firmware File")
        if not firmware_file:
            return

        QMessageBox.information(self, "Upgrade", f"Upgrading with {firmware_file}.")
        # Здесь вы можете добавить код для обновления прошивки


def expand_cidr_range(cidr):
        try:
            network = ipaddress.ip_network(cidr, strict=False)
            return [str(ip) for ip in network.hosts()]
        except ValueError:
            # В случае некорректного ввода, возвращаем пустой список
            return []
        
def convert_seconds_to_time_string(seconds):
        days, remainder = divmod(seconds, 86400)
        hours, remainder = divmod(remainder, 3600)
        minutes, seconds = divmod(remainder, 60)
        return f"{days} d {hours} h {minutes} m {seconds} s"


class ScanTab(QWidget):
    update_table_signal = pyqtSignal(dict, int)  # Новый сигнал

    def __init__(self, parent=None):
        super(ScanTab, self).__init__(parent)
        
        # Инициализации и определения
        self.scan_thread = None
        self.miner_rows = {}  
        self.open_ports = {} 
        self.row_count = 0

        layout = QVBoxLayout()

        # Кнопки
        button_layout = QHBoxLayout()
        button_layout.setContentsMargins(0, -10, 0, 0)

        self.scan_button = QPushButton("Scan")
        self.scan_button.clicked.connect(self.start_scan_and_get_data)
        self.monitor_button = QPushButton("Monitor")
        self.asic_search_button = QPushButton("ASIC Search")
        self.update_button = QPushButton("Update")
        self.update_button.clicked.connect(self.show_upgrade_dialog)

        self.setStyleSheet("""
            QTableWidget {
                background-color: white;
                color: black;
            }
            QTableWidget::item {
                background-color: white;
                color: black;
            }
        """)


        button_style = """
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
            """
        
        self.scan_button.setStyleSheet(button_style)
        self.monitor_button.setStyleSheet(button_style)
        self.asic_search_button.setStyleSheet(button_style)
        self.update_button.setStyleSheet(button_style)
        
        button_layout.addWidget(self.scan_button)
        button_layout.addWidget(self.monitor_button)
        button_layout.addWidget(self.asic_search_button)
        button_layout.addWidget(self.update_button)
        button_layout.addItem(QSpacerItem(20, 20, QSizePolicy.Expanding, QSizePolicy.Minimum))

        layout.addLayout(button_layout)
        
        # Прогресс-бар
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

        # Таблица внутри QScrollArea
        self.table = QTableWidget(254, 16, self)
        self.table.verticalHeader().setVisible(False)

        self.table.setFixedWidth(1500)  # Устанавливаем фиксированную ширину для таблицы
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

       

        
        # Добавьте следующие строки здесь
        self.scrollArea.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOn)
        
        

        layout.addWidget(self.scrollArea)

        

        # Настройки таблицы
        self.table.setHorizontalHeaderLabels(["", "IP", "Status", "Type", "GHS avg", "GHS rt", "Elapsed", "fan_speed", "%pwm%", "Temp PCB", "Temp Chip" , "CompileTime", "Consumption/Watt ", "Cdvd" ])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Fixed)
        self.table.horizontalHeader().resizeSection(0,5)
        header = self.table.horizontalHeader()
        header.setStyleSheet("QHeaderView::section { background-color: #333333 }")
        palette = header.palette()
        palette.setColor(QPalette.Text, QColor("#ffffff"))
        header.setPalette(palette)

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

        # Подключение сигнала к слоту
        self.update_table_signal.connect(self.update_table)

        # Устанавливаем основной макет
        self.setLayout(layout)
        

    def update_progress_bar(self, scanned_ips):
        self.progress_bar.setValue(scanned_ips)
   

    
    def start_scan_and_get_data(self):
    # Чтение диапазона IP из файла
        with open('ip.txt', 'r') as f:
            ip_ranges = f.read().strip().splitlines()

         # Развертывание CIDR-диапазонов в список IP-адресов
        ip_list = []
        for cidr in ip_ranges:
            ip_list.extend(expand_cidr_range(cidr))

         # Установите максимальное значение прогресс-бара равным количеству IP-адресов
        self.progress_bar.setMaximum(len(ip_list))

         # Создание и запуск потока
        self.scan_thread = ScanThread(ip_list)
        self.scan_thread.finished.connect(self.on_scan_completed)  # подключение сигнала к слоту
        self.scan_thread.miner_found.connect(self.update_table)  # подключаем новый сигнал к методу update_table
        self.scan_thread.ip_scanned.connect(self.update_progress_bar)  # подключаем сигнал к слоту обновления прогресс-бара
        self.scan_thread.start()

       
    # Вызывается, когда фоновый поток завершает сканирование
    def on_scan_completed(self, open_ports, total_miners):
        # Отправляем сигнал с данными в главный поток
        self.update_table_signal.emit(open_ports, total_miners)
         # Добавляем уведомление о завершении сканирования
        QMessageBox.information(self, "Scan Finished", f"Scanning finished. Found {total_miners} devices.")

    def show_upgrade_dialog(self):
        selected_rows = []
        for i in range(self.table.rowCount()):
            item = self.table.item(i, 0)
            if item is not None and item.checkState() == Qt.Checked:
                selected_rows.append(i)

        if not selected_rows:
            QMessageBox.information(self, "No Selection", "Please select a row to upgrade.")
            return

        dialog = UpgradeDialog(self)
        dialog.label.setText(f"Selected rows: {len(selected_rows)}")
        dialog.exec_()


    def get_color_for_value(self, value, min_value=0, max_value=100):
       # Плавный переход от зеленого (70-30) к желтому (80-20)
        if 30 <= value <= 70:
            red_component = 0
            green_component = 255
        elif 20 < value < 30 or 70 < value < 80:
            red_component = 255
            green_component = 255
        # Плавный переход от желтого (80-20) к красному (100-0)
        else:
            red_component = 255
            green_component = 0

        blue_component = 0  # компонент синего цвета всегда равен 0

        return QColor(red_component, green_component, blue_component)

    
    def update_table(self, open_ports, total_miners):

        try:
            # Перебираем все открытые порты и соответствующие им данные
            for ip, data in open_ports.items():

                # Извлекаем данные статистики
                stats_data = data.get('STATS', [])


                if not stats_data:
                    print(f"stats_data пуст для {ip}, пропускаем")
                    continue

                # Добавляем новую строку в таблицу в начало
                self.table.insertRow(0)

                # Добавляем чекбокс в новую строку
                item = QTableWidgetItem()
                item.setFlags(Qt.ItemIsUserCheckable | Qt.ItemIsEnabled)
                item.setCheckState(Qt.Unchecked)
                self.table.setItem(0, 0, item)
                
                
                # IP
                item = QTableWidgetItem(ip)
                item.setTextAlignment(Qt.AlignCenter)  # Выровнять текст по центру
                self.table.setItem(0, 1, item)
  
                # Type
                if 'Type' in stats_data[0]:
                    self.table.setItem(0, 3, QTableWidgetItem(stats_data[0]['Type']))
  
                if len(stats_data) > 1:
                    detailed_stats = stats_data[1]


                # Status
                if 'GHS av' in detailed_stats:
                   if float(detailed_stats['GHS av']) > 0:
                       status_text = "online"
                       status_color = "#05B8CC"
                else:
                    status_text = detailed_stats.get('state', 'Unknown')
                    status_color = "red"
    
                status_label = QLabel(status_text)
                status_label.setAlignment(Qt.AlignCenter)
                status_label.setStyleSheet(f"background-color: {status_color}; color: white; border-radius: 10px;")
                self.table.setCellWidget(0, 2, status_label)

                # Устанавливаем фиксированный размер для ячейки статуса
                self.table.setRowHeight(0, 20)  # Устанавливаем высоту первой строки равной 50 пикселей
                self.table.setColumnWidth(2, 50)  # Устанавливаем ширину колонки статуса (2) равной 100 пикселям
        
               # GHS av
                if 'GHS av' in detailed_stats:
                    item = QTableWidgetItem(str(detailed_stats['GHS av']))
                    item.setTextAlignment(Qt.AlignCenter)  # Выровнять текст по центру
                    self.table.setItem(0, 4, item)

                # GHS 5s
                if 'GHS 5s' in detailed_stats:
                    item = QTableWidgetItem(str(detailed_stats['GHS 5s']))
                    item.setTextAlignment(Qt.AlignCenter)  # Выровнять текст по центру
                    self.table.setItem(0, 5, item)


 
                # Elapsed
                if 'Elapsed' in detailed_stats:
                    elapsed_seconds = int(detailed_stats['Elapsed'])
                    elapsed_time = convert_seconds_to_time_string(elapsed_seconds)  # Предполагая, что у вас есть соответствующая функция
                    self.table.setItem(0, 6, QTableWidgetItem(elapsed_time))

                # fan_speed
                if 'fan_num' in detailed_stats:
                    fan_num = detailed_stats['fan_num']
                    fans = []
                    for i in range(1, fan_num + 1):
                        fan_key = f"fan{i}"
                        if fan_key in detailed_stats:
                            fans.append(str(detailed_stats[fan_key]))
                    fans_str = "/".join(fans)
                    item = QTableWidgetItem(fans_str)
                    item.setTextAlignment(Qt.AlignCenter)  # Выровнять текст по центру
                    self.table.setItem(0, 7, item)
                    self.table.setColumnWidth(7, 125)  # Установить ширину столбца

                if 'fan_pwm' in detailed_stats:
                    fan_pwm = detailed_stats['fan_pwm']
                    item = QLabel(f"{fan_pwm}%")
                    item.setAlignment(Qt.AlignCenter)  # Выровнять текст по центру
                    self.table.setCellWidget(0, 8, item)
   

                # temp плат
                if 'temp1' in detailed_stats and 'temp2' in detailed_stats and 'temp3' in detailed_stats:
                    temps = [detailed_stats['temp1'], detailed_stats['temp2'], detailed_stats['temp3']]
                    item = QTableWidgetItem(f"{temps[0]}/{temps[1]}/{temps[2]}")
                    item.setTextAlignment(Qt.AlignCenter)  # Выровнять текст по центру
                    self.table.setItem(0, 9, item)

                # temp чипов
                if 'temp2_1' in detailed_stats and 'temp2_2' in detailed_stats and 'temp2_3' in detailed_stats:
                    temps = [detailed_stats['temp2_1'], detailed_stats['temp2_2'], detailed_stats['temp2_3']]
                    item = QTableWidgetItem(f"{temps[0]}/{temps[1]}/{temps[2]}")
                    item.setTextAlignment(Qt.AlignCenter)  # Выровнять текст по центру
                    self.table.setItem(0, 10, item)

                # CompileTime
                if 'CompileTime' in stats_data[0]:
                    self.table.setItem(0, 11, QTableWidgetItem(stats_data[0]['CompileTime']))

                # total_chain_consumption
                consumption_keys = [key for key in detailed_stats.keys() if 'consumption' in key]

                total_chain_consumption = round(sum(detailed_stats.get(key, 0) for key in consumption_keys), 1)

                # Если общее потребление больше 0, добавляем его в таблицу
                if total_chain_consumption > 0:
                   item = QTableWidgetItem(str(total_chain_consumption))
                   item.setTextAlignment(Qt.AlignCenter)
                   self.table.setItem(0, 12, item)
                else:
                   print(f"Отсутствуют данные о потреблении для {ip}. Использованы значения по умолчанию для отсутствующих ключей.")

    
                 
                # Извлекаем напряжение для всех плат и вычисляем среднее значение
                voltage_keys = ['voltage1', 'voltage2', 'voltage3', 'voltage4']
                voltages = [detailed_stats.get(key, 0) for key in voltage_keys]
                non_zero_voltages = [v for v in voltages if v > 0]
                average_voltage = sum(non_zero_voltages) / len(non_zero_voltages) if non_zero_voltages else 0

                # Используем глобальное напряжение, если оно присутствует
                global_voltage_key = 'chain_vol1'  # Если у вас другой ключ для глобального напряжения, замените его
                global_voltage = detailed_stats.get(global_voltage_key, None)
                if global_voltage:
                    # Конвертируем из милливольт в вольты
                    global_voltage = global_voltage / 1000.0
                    display_voltage = global_voltage
                else:
                    display_voltage = average_voltage

                # Объединяем значения напряжения и глобальной частоты в одной строке
                cell_value = f"{display_voltage:.1f}/{detailed_stats['frequency']}"

                # Устанавливаем значение ячейки
                self.table.setItem(0, 13, QTableWidgetItem(cell_value))




        except Exception as e:
            print(f"Ошибка при обновлении таблицы: {e}")



    def save_values(self):
        self.asic_values = []
        for row in range(self.table.rowCount()):
            item = self.table.item(row, 0)
            if item is not None:
                self.asic_values.append(item.text())
      
    def hideEvent(self, event):
        super().hideEvent(event)
        self.save_values()  # Сохраняем значения, когда вкладка скрывается


     # Инициализируем переменную экземпляра для хранения данных
        self.data = None

    def load_data(self):
        # Загружаем данные в переменную экземпляра
        self.data = 'Данные для вкладки ScanTab'

    def save_data(self):
        # Здесь мы предполагаем, что данные уже сохранены в переменной экземпляра.
        print(f"Сохраняю данные: {self.data}")
