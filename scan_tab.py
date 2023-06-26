from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QSpacerItem, QSizePolicy, QTableWidget, QHeaderView, QAbstractItemView, QCheckBox, QLabel, QProgressBar
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QPalette, QColor
from PyQt5.QtWidgets import QTableWidgetItem
from PyQt5.QtCore import QThread, pyqtSignal
from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import QTimer
from PyQt5.QtWidgets import QMessageBox
import traceback
from scan_thread import ScanThread
import ipaddress
from detailed_tooltip import DetailedInfoWidget



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
        self.scan_thread = None
        self.miner_rows = {}  # словарь для хранения строк таблицы для каждого майнера
        self.open_ports = {}  # инициализация open_ports как пустого словаря
        layout = QVBoxLayout()

        button_layout = QHBoxLayout()
        button_layout.setContentsMargins(0, -10, 0, 0)

        self.detailed_info_widget = DetailedInfoWidget()


        self.scan_button = QPushButton("Scan")
        self.scan_button.clicked.connect(self.start_scan_and_get_data)

        self.monitor_button = QPushButton("Monitor")
        self.asic_search_button = QPushButton("ASIC Search")
        self.update_button = QPushButton("Update")

        self.row_count = 0

        button_style = """
            QPushButton { 
                color: white;
                border: 2px solid #555555;
                border-radius: 10px;
                background: #grey;
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

      # Создание прогресс-бара
        self.progress_bar = QProgressBar(self)
        self.progress_bar.setRange(0, 100)  # Устанавливаем диапазон от 0 до 100
        self.progress_bar.setTextVisible(True)  # Включаем отображение текста

        # Стилизуем прогресс-бар с помощью CSS
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

 
        # Создание горизонтального макета и добавление в него прогресс-бара
        progress_layout = QHBoxLayout()
        progress_layout.addItem(QSpacerItem(20, 20, QSizePolicy.Expanding, QSizePolicy.Minimum))  # добавление расширяющегося пространства перед прогресс-баром
        progress_layout.addWidget(self.progress_bar)

        # Добавление progress_layout в основной макет
        layout.addLayout(progress_layout)

    
        # Подключить сигналы к слотам
        self.table = QTableWidget(254, 12, self)  # Измените число столбцов на 11
        self.table.setHorizontalHeaderLabels(["", "IP", "Type", "GHS av", "GHS 5s", "Elapsed", "fan_speed", "%pwm%", "Temp PCB", "Temp Chip" , "CompileTime", ])  # Добавьте новые заголовки
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Fixed)
        self.table.horizontalHeader().resizeSection(0, 100)


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

        layout.addWidget(self.table)

        self.setLayout(layout)

        self.setStyleSheet("""
            QTableWidget {
                background-color: #262F34;
                color: black;
                gridline-color: #ffffff;
            }
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

        self.setLayout(layout)

    def update_progress_bar(self, scanned_ips):
        self.progress_bar.setValue(scanned_ips)
   

    
    def start_scan_and_get_data(self):
        # Чтение диапазона IP из файла
        with open('ip.txt', 'r') as f:
            ip_range = f.read().strip()

       
        # Разбиваем строку на список по запятым или пробелам
        ip_list = ip_range.replace(',', ' ').split()

        # Разбиваем строку на список по запятым или пробелам
        cidr_ranges = ip_range.replace(',', ' ').split()

        # Развертывание CIDR-диапазонов в список IP-адресов
        ip_list = []
        for cidr in cidr_ranges:
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
        print(open_ports) 
        print("on_scan_completed вызван")
        # Отправляем сигнал с данными в главный поток
        self.update_table_signal.emit(open_ports, total_miners)
         # Добавляем уведомление о завершении сканирования
        QMessageBox.information(self, "Scan Finished", f"Scanning finished. Found {total_miners} devices.")

    def update_table(self, open_ports, total_miners):
        print("update_table вызвана")

        # Проверяем содержимое open_ports на входе
        print("open_ports:", open_ports)

        try:
            # Перебираем все открытые порты и соответствующие им данные
            for ip, data in open_ports.items():
                print(f"Обработка данных для IP: {ip}")

                # Извлекаем данные статистики
                stats_data = data.get('STATS', [])

                # Проверяем содержимое stats_data
                print(f"stats_data для {ip}: {stats_data}")

                if not stats_data:
                    print(f"stats_data пуст для {ip}, пропускаем")
                    continue

                # Добавляем новую строку в таблицу в начало
                self.table.insertRow(1)
                print(f"Добавлена строка для {ip}")

                # Добавляем чекбокс в новую строку
                checkbox = QCheckBox()
                self.table.setCellWidget(1, 0, checkbox)


                # Заполняем ячейки значениями

                # IP
                item = QTableWidgetItem(ip)
                item.setTextAlignment(Qt.AlignCenter)  # Выровнять текст по центру
                self.table.setItem(1, 1, item)
                print(f"Установлен IP: {ip}")

                # Type
                if 'Type' in stats_data[0]:
                    print(f"Type для {ip}: {stats_data[0]['Type']}")
                    self.table.setItem(1, 2, QTableWidgetItem(stats_data[0]['Type']))
                    print(f"Установлен Type: {stats_data[0]['Type']}")

               
                if len(stats_data) > 1:
                    detailed_stats = stats_data[1]

                # GHS av
                if 'GHS av' in detailed_stats:
                    item = QTableWidgetItem(str(detailed_stats['GHS av']))
                    item.setTextAlignment(Qt.AlignCenter)  # Выровнять текст по центру
                    self.table.setItem(1, 3, item)
                    print(f"Установлен GHS av: {detailed_stats['GHS av']}")

                # GHS 5s
                if 'GHS 5s' in detailed_stats:
                    item = QTableWidgetItem(str(detailed_stats['GHS 5s']))
                    item.setTextAlignment(Qt.AlignCenter)  # Выровнять текст по центру
                    self.table.setItem(1, 4, item)
                    print(f"Установлен GHS 5s: {detailed_stats['GHS 5s']}")

                # Elapsed
                if 'Elapsed' in detailed_stats:
                    elapsed_seconds = int(detailed_stats['Elapsed'])
                    elapsed_time = convert_seconds_to_time_string(elapsed_seconds)  # Предполагая, что у вас есть соответствующая функция
                    self.table.setItem(1, 5, QTableWidgetItem(elapsed_time))
                    print(f"Установлен Elapsed: {elapsed_time}")
  
                # fan_speed
                if 'fan_num' in detailed_stats:
                    fan_num = detailed_stats['fan_num']
                    fans = []
                    for i in range(1, fan_num + 1):
                        fan_key = f"fan{i}"
                        if fan_key in detailed_stats:
                            fans.append(str(detailed_stats[fan_key]))
                            fans_str = "/".join(fans)
                            self.table.setItem(1, 6, QTableWidgetItem(fans_str))
                            self.table.setColumnWidth(6, 125)  # Установить ширину столбца
                            print(f"Установлены скорости вентиляторов: {fans_str}")

                          
                # fan_pwm
                if 'fan_pwm' in detailed_stats:
                    item = QTableWidgetItem(f"{detailed_stats['fan_pwm']}%")
                    item.setTextAlignment(Qt.AlignCenter)  # Выровнять текст по центру
                    self.table.setColumnWidth(7, 50)  # Установить ширину столбца fan_pwm равной 50
                    self.table.setItem(1, 7, item)
                    print(f"Установлена скорость вентилятора: {detailed_stats['fan_pwm']}")

                # temp плат
                if 'temp1' in detailed_stats and 'temp2' in detailed_stats and 'temp3' in detailed_stats:
                    temps = [detailed_stats['temp1'], detailed_stats['temp2'], detailed_stats['temp3']]
                    item = QTableWidgetItem(f"{temps[0]}/{temps[1]}/{temps[2]}")
                    item.setTextAlignment(Qt.AlignCenter)  # Выровнять текст по центру
                    self.table.setItem(1, 8, item)
                    print(f"Установлена температура плат: {temps[0]}/{temps[1]}/{temps[2]}")

                # temp чипов
                if 'temp2_1' in detailed_stats and 'temp2_2' in detailed_stats and 'temp2_3' in detailed_stats:
                    temps = [detailed_stats['temp2_1'], detailed_stats['temp2_2'], detailed_stats['temp2_3']]
                    item = QTableWidgetItem(f"{temps[0]}/{temps[1]}/{temps[2]}")
                    item.setTextAlignment(Qt.AlignCenter)  # Выровнять текст по центру
                    self.table.setItem(1, 9, item)
                    print(f"Установлена температура плат: {temps[0]}/{temps[1]}/{temps[2]}")     
                
                # CompileTime
                if 'CompileTime' in stats_data[0]:
                    print(f"CompileTime для {ip}: {stats_data[0]['CompileTime']}")
                    self.table.setItem(1, 10, QTableWidgetItem(stats_data[0]['CompileTime']))
                    print(f"Установлен CompileTime: {stats_data[0]['CompileTime']}")
     



        except Exception as e:
                print("Exception:", e)  # Выводим исключение, если оно произошло

                self.table.update()
                print("Таблица обновлена")
                # Оповещение о количестве ASIC
                print(f"Всего ASIC: {total_miners}")   

                    

                self.table.cellClicked.connect(self.show_tooltip)  # Подключить сигнал к слоту


   