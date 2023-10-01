from concurrent.futures import ThreadPoolExecutor, as_completed

from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QGridLayout, QFrame, QComboBox, QToolTip, QSizePolicy
from PyQt5.QtCore import pyqtSlot
from PyQt5.QtGui import QFont
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from datetime import datetime, timedelta
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.artist import Artist
from matplotlib.dates import DateFormatter



class InfoPanel(QFrame):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.layout = QGridLayout()
        self.init_ui()

    def init_ui(self):
        self.asics_label = QLabel("Asics:")
        self.asics_value = QLabel("0")
        self.hashrate_label = QLabel("Total Hashrate:")
        self.hashrate_value = QLabel("0 TH/s")

        self.layout.addWidget(self.asics_label, 0, 0)
        self.layout.addWidget(self.asics_value, 0, 1)
        self.layout.addWidget(self.hashrate_label, 1, 0)
        self.layout.addWidget(self.hashrate_value, 1, 1)

        self.setLayout(self.layout)

# Основной класс для отслеживания данных и отображения их на графике
class MonitorTab(QWidget):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.layout = QVBoxLayout()
        self.data_by_ip = {}
        self.total_hashrate_by_model = {}
        self.current_annotation = None  # Текущая аннотация (подсказка)
        self.hashrate_history = []  # История хэшрейта
        self.time_history = []  # История времени

        self.init_ui()

    def init_ui(self):
        self.upper_horizontal_layout = QHBoxLayout()
        self.info_panel = InfoPanel()
        self.upper_horizontal_layout.addWidget(self.info_panel)

        self.is_final_received = False

        self.figure = Figure(figsize=(10, 8), dpi=100)
        self.canvas = FigureCanvas(self.figure)
        self.ax = self.figure.add_subplot(111)

        # Установка темного стиля для графика
        self.ax.set_facecolor("black")
        self.figure.patch.set_facecolor("black")
        self.ax.tick_params(colors='white')
        self.ax.xaxis.label.set_color('white')
        self.ax.yaxis.label.set_color('white')

        # Событие при наведении мыши и выходе из зоны графика
        self.canvas.mpl_connect('motion_notify_event', self.on_hover)
        self.canvas.mpl_connect('axes_leave_event', self.on_leave)

        self.canvas.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.upper_horizontal_layout.addWidget(self.canvas)
        self.layout.addLayout(self.upper_horizontal_layout)

        self.timeframe_combobox = QComboBox()
        self.timeframe_combobox.addItems(["Real Time", "Last 24 Hours", "Last Month"])
        self.layout.addWidget(self.timeframe_combobox)

        self.setLayout(self.layout)


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

        # Добавить текущий хэшрейт и текущее время в историю
        total_hashrate = sum([data['hashrate'] for data in self.total_hashrate_by_model.values()])
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
            self.current_annotation = self.ax.annotate(
                f'TeraHash: {event.ydata:.1f}', 
                (event.xdata, event.ydata),
                textcoords="offset points",
                xytext=(0,10),
                ha='center',
                color='white'
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
        if not self.is_final_received:
            return
        self.is_final_received = False
     
        selected_timeframe = self.timeframe_combobox.currentText()

        self.ax.clear()
        self.ax.set_facecolor("black")

        # Форматтеры для даты
        date_format = DateFormatter("%H:%M:%S")  # для "Real Time" и "Last 24 Hours"
        date_format_month = DateFormatter("%d %b")  # для "Last Month"

        if selected_timeframe == "Real Time":
            self.ax.plot(self.time_history[-100:], self.hashrate_history[-100:], color='white')
            self.ax.xaxis.set_major_formatter(date_format)
        elif selected_timeframe == "Last 24 Hours":
            self.ax.plot(self.time_history[-480:], self.hashrate_history[-480:], color='white')  # Assuming data every 3 minutes
            self.ax.xaxis.set_major_formatter(date_format)
        elif selected_timeframe == "Last Month":
            self.ax.plot(self.time_history[-14400:], self.hashrate_history[-14400:], color='white')  # Assuming data every 3 minutes
            self.ax.xaxis.set_major_formatter(date_format_month)

        # Установить шаги для терахэшей
        if self.hashrate_history:
            max_hashrate = max(self.hashrate_history)
            rounded_max_hashrate = round(max_hashrate, -1)  # Округляем до ближайшего круглого числа
    
            # Вычисляем значение шага для шкалы
            step = rounded_max_hashrate / 10
    
            self.ax.set_yticks(np.arange(0, rounded_max_hashrate + step, step))  # Установить диапазон шагов
    
            # Заполнить график на 70%
            self.ax.set_ylim(0, rounded_max_hashrate * 1.43)
                 # Для отладки: проверка последних 10 значений в истории хэшрейта и времени
       
        # Применить изменения
        self.canvas.draw()


    def load_data(self):
        self.data = 'Data for moni hTab'

    def save_data(self):
        print(f"Saving data: {self.data}")