from concurrent.futures import ThreadPoolExecutor, as_completed
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QGridLayout, QFrame, QComboBox, QSizePolicy
from PyQt5.QtCore import pyqtSlot
from PyQt5.QtGui import QFont
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from datetime import datetime
from matplotlib.dates import DateFormatter
import matplotlib.dates as md

import numpy as np
import random
from datetime import timedelta
from PyQt5.QtWidgets import QPushButton
from PyQt5.QtWidgets import QRadioButton, QButtonGroup
import matplotlib.dates as mdates





class InfoPanel(QFrame):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.layout = QGridLayout()
        self.init_ui()

    def init_ui(self):
        font = QFont()
        font.setPointSize(20)
        self.asics_label = QLabel("Asics:")
        self.asics_value = QLabel("0")
        self.hashrate_label = QLabel("Total H/r:")
        self.hashrate_value = QLabel("0 TH/s")

        for label in [self.asics_label, self.asics_value, self.hashrate_label, self.hashrate_value]:
            label.setFont(font)
            label.setStyleSheet("color: #0DDEF4;")

        self.layout.addWidget(self.asics_label, 0, 0)
        self.layout.addWidget(self.asics_value, 0, 1)
        self.layout.addWidget(self.hashrate_label, 1, 0)
        self.layout.addWidget(self.hashrate_value, 1, 1)
        self.setLayout(self.layout)

        
class MonitorTab(QWidget):
    # Конструктор класса
    def __init__(self, parent, start_scan_method, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Метод для запуска сканирования
        self.start_scan_method = start_scan_method

        # Инициализация основных атрибутов
        self.layout = QVBoxLayout()  # Главный вертикальный layout
        self.data_by_ip = {}  # Данные по IP-адресам
        self.total_hashrate_by_model = {}  # Общий хэшрейт по моделям
        self.current_annotation = None  # Текущая аннотация (подсказка) на графике
        self.hashrate_history = []  # История хэшрейта
        self.time_history = []  # История времени
        self.init_ui()  # Инициализация пользовательского интерфейса

    # Метод для инициализации пользовательского интерфейса
    def init_ui(self):
        # Создание верхнего горизонтального layout и контейнеров
        self.upper_horizontal_layout = QHBoxLayout()
        self.container1 = QFrame()
        self.container1_layout = QVBoxLayout()
        self.info_panel = InfoPanel()
        self.container1_layout.addWidget(self.info_panel)
        self.container1.setLayout(self.container1_layout)
        self.container2 = QFrame()
        self.upper_horizontal_layout.addWidget(self.container1)
        self.upper_horizontal_layout.addWidget(self.container2)
        self.layout.addLayout(self.upper_horizontal_layout)
        self.is_final_received = False

        # Создание радио-кнопок для выбора временного диапазона
        self.radio_buttons_layout = QHBoxLayout()  # New layout for radio buttons

        self.real_time_rb = QRadioButton("Real Time")
        self.real_time_rb.setChecked(True)  # Set "Real Time" as default
        self.last_24_hours_rb = QRadioButton("Last 24 Hours")
        self.last_month_rb = QRadioButton("Last Month")

        self.radio_buttons_layout.addWidget(self.real_time_rb)
        self.radio_buttons_layout.addWidget(self.last_24_hours_rb)
        self.radio_buttons_layout.addWidget(self.last_month_rb)
        self.layout.addLayout(self.radio_buttons_layout)  # Add the layout above the graph

        self.timeframe_group = QButtonGroup(self)
        self.timeframe_group.addButton(self.real_time_rb, 0)
        self.timeframe_group.addButton(self.last_24_hours_rb, 1)
        self.timeframe_group.addButton(self.last_month_rb, 2)
        self.timeframe_group.buttonClicked.connect(self.update_graph)
        
      

        # Создание графика
        self.figure = Figure(figsize=(10, 8), dpi=100)
        self.canvas = FigureCanvas(self.figure)
        self.ax = self.figure.add_subplot(111)
        self.canvas.mpl_connect('motion_notify_event', self.on_hover)
        self.canvas.mpl_connect('axes_leave_event', self.on_leave)
        self.canvas.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.layout.addWidget(self.canvas)

        # Создание кнопки "Обновить"
        self.refresh_button = QPushButton("Обновить")
        self.refresh_button.clicked.connect(self.start_scan)
        self.layout.addWidget(self.refresh_button)

        # Установка главного layout для этого виджета
        self.setLayout(self.layout)




    def start_scan(self):
        self.start_scan_method()
   
    

    @pyqtSlot(dict)
    def receive_from_scan(self, data):  
        is_final = data.get('is_final', False)
        if is_final:
            self.is_final_received = True
            print("receive_from_scan: is_final_received set to True, calling finalize_update")
            self.finalize_update()
            return

        ip_address = data.get('ip_address')
        if not ip_address:
            return

        self.data_by_ip[ip_address] = data
        self.aggregate_data_by_model()
        self.update_info_panel()

        total_hashrate = sum([data['hashrate'] for data in self.total_hashrate_by_model.values()])
    
         # Добавить небольшое случайное значение к total_hashrate
        noise = random.uniform(-0.5, 0.5)  # Добавляем шум в диапазоне от -5 до 5
        total_hashrate += noise
    
        self.hashrate_history.append(total_hashrate)
        self.time_history.append(datetime.now())





    @pyqtSlot()
    def finalize_update(self):
        if self.is_final_received:
            self.update_graph()
            self.is_final_received = False


    def aggregate_single_device(self, ip, data):
        model = self.determine_model(data)
        if not model:
            return None

        hash_rate_key = 'GHS 5s' if model == 'Antminer' else 'GHSmm' if model == 'Avalon' else 'MHS_5s'
        hash_rate = float(data.get(hash_rate_key, 0))
        hash_rate_ths = hash_rate / 1000.0

        return model, hash_rate_ths

    def aggregate_data_by_model(self):
        self.total_hashrate_by_model.clear()

        with ThreadPoolExecutor() as executor:
            futures = {executor.submit(self.aggregate_single_device, ip, data): ip for ip, data in self.data_by_ip.items()}
            for future in as_completed(futures):
                ip = futures[future]
                try:
                    model, hash_rate_ths = future.result()
                except Exception as exc:
                    print(f"An exception occurred while aggregating data for {ip}: {exc}")
                    continue

                if not model:
                    continue

                current_model_data = self.total_hashrate_by_model.get(model, {'hashrate': 0, 'count': 0})
                current_model_data['hashrate'] += hash_rate_ths
                current_model_data['count'] += 1
                self.total_hashrate_by_model[model] = current_model_data

    def determine_model(self, data):
        if 'Type' in data:
            return 'Antminer'  
        elif 'PROD' in data:
            return 'Avalon'
        elif 'Model' in data:
            return 'WhatsMiner'
        else:
            return None

    def on_hover(self, event):
        if self.current_annotation:
            self.current_annotation.remove()
            self.current_annotation = None

        if event.inaxes == self.ax:
            # Ищем ближайшую точку
            numeric_times = mdates.date2num(self.time_history)
            distance = np.sqrt((numeric_times - event.xdata)**2)

            closest_index = np.argmin(distance)

            # Получаем данные для этой точки
            closest_time = self.time_history[closest_index]
            closest_hashrate = self.hashrate_history[closest_index]
        
            # Форматируем текст подсказки
            annotation_text = f"Time: {closest_time.strftime('%H:%M:%S')}\nHashrate: {closest_hashrate:.2f} TH/s"

            # Создаем подсказку
            self.current_annotation = self.ax.annotate(
                annotation_text, 
                (event.xdata, event.ydata),
                textcoords="offset points",
                xytext=(0,10),
                ha='center',
                fontsize=9,
                bbox=dict(boxstyle="round,pad=0.3", edgecolor="#0DDEF4", facecolor="white", linewidth=1.2),
                color='#0DDEF4'
            )
            self.canvas.draw()

    def update_info_panel(self):
        total_hashrate = sum([data['hashrate'] for data in self.total_hashrate_by_model.values()])
        total_count = sum([data['count'] for data in self.total_hashrate_by_model.values()])
        self.info_panel.asics_value.setText(str(total_count))
        self.info_panel.hashrate_value.setText(f"{total_hashrate:.2f} TH/s")

    def on_leave(self, event):
        if self.current_annotation:
            self.current_annotation.remove()
            self.current_annotation = None
            self.canvas.draw()

    def update_graph(self):
        selected_timeframe_id = self.timeframe_group.checkedId()
    
        last_time = datetime.now()

        if selected_timeframe_id == 0:  # Real Time
            start_time = last_time - timedelta(minutes=10)
            self.ax.xaxis.set_major_locator(md.MinuteLocator(interval=1))
            self.ax.xaxis.set_major_formatter(DateFormatter("%H:%M"))

        elif selected_timeframe_id == 1:  # Last 24 Hours
            start_time = last_time - timedelta(hours=24)
            self.ax.xaxis.set_major_locator(md.HourLocator(interval=2))
            self.ax.xaxis.set_major_formatter(DateFormatter("%d-%m %H"))

        elif selected_timeframe_id == 2:  # Last Month
            start_time = last_time - timedelta(days=30)
            self.ax.xaxis.set_major_locator(md.DayLocator())
            self.ax.xaxis.set_major_formatter(DateFormatter("%d-%m-%y"))

        else:
            start_time = last_time - timedelta(minutes=10)

        # Фильтруем данные по временной рамке
        filtered_indices = [i for i, time in enumerate(self.time_history) if time >= start_time]
        filtered_times = [self.time_history[i] for i in filtered_indices]
        filtered_hashrates = [self.hashrate_history[i] for i in filtered_indices]

        if not filtered_times:
            filtered_times = [start_time, last_time]
            filtered_hashrates = [0, 0]

        # Очистка текущего графика и отображение новых данных
        self.ax.clear()
        self.ax.set_facecolor("white")
        self.ax.plot(filtered_times, filtered_hashrates, color='lightblue')
        self.ax.fill_between(filtered_times, 0, filtered_hashrates, facecolor='lightblue')

        # Установка делений и форматтера по оси X
        self.ax.set_xlim(start_time, last_time)

        # Установка делений по оси Y
        if filtered_hashrates:
            max_hashrate = max(filtered_hashrates)
            rounded_max_hashrate = round(max_hashrate, -1)
            step = rounded_max_hashrate / 10
            self.ax.set_yticks(np.arange(0, rounded_max_hashrate + step, step))
            self.ax.set_ylim(0, rounded_max_hashrate * 1.43)

        self.canvas.draw()



  

    def load_data(self):
        self.data = 'Data for moni hTab'

    def save_data(self):
        print(f"Saving data: {self.data}")