from concurrent.futures import ThreadPoolExecutor, as_completed
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QGridLayout, QFrame, QComboBox, QSizePolicy
from PyQt5.QtCore import pyqtSlot
from PyQt5.QtGui import QFont
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from datetime import datetime
from matplotlib.dates import DateFormatter
import matplotlib.dates as md
import time

from PyQt5.QtCore import Qt
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
        
        # Radio buttons for graphs
        self.graph_rb1 = QRadioButton("Graph 1")
        self.graph_rb2 = QRadioButton("Graph 2")
        self.graph_rb3 = QRadioButton("Graph 3")
        self.graph_rb4 = QRadioButton("Graph 4")

        self.graph_group = QButtonGroup(self)
        self.graph_group.addButton(self.graph_rb1, 0) 
        self.graph_group.addButton(self.graph_rb2, 1)
        self.graph_group.addButton(self.graph_rb3, 2)
        self.graph_group.addButton(self.graph_rb4, 3)

        # Asics
        self.asics_label = QLabel("Asics:")
        self.asics_value = QLabel("0")
        self.asics_value.setStyleSheet("color: yellow;")
        
        # Real Hashrate
        self.hashrate_label = QLabel("Real H/r:")
        self.hashrate_value = QLabel("0 TH/s")
        
        # Average Hashrate
        self.avg_hashrate_label = QLabel("Avg H/r:")
        self.avg_hashrate_value = QLabel("0 TH/s")
        self.avg_hashrate_value.setStyleSheet("color: green;")
        
        # Power Consumption
        self.power_consumption_label = QLabel("Power:")
        self.power_consumption_value = QLabel("0 kW")
        self.power_consumption_value.setStyleSheet("color: red;")

        # Setting font and adding them to layout
        for label in [self.asics_label, self.hashrate_label, 
                      self.avg_hashrate_label, self.power_consumption_label]:
            label.setFont(font)
            label.setStyleSheet("color: #0DDEF4;")
            
        for label in [self.asics_value, self.hashrate_value, 
                      self.avg_hashrate_value, self.power_consumption_value]:
            label.setFont(font)
        
        self.layout.addWidget(self.graph_rb1, 0, 0)
        self.layout.addWidget(self.asics_label, 0, 1)
        self.layout.addWidget(self.asics_value, 0, 2)
        
        self.layout.addWidget(self.graph_rb2, 1, 0)
        self.layout.addWidget(self.hashrate_label, 1, 1)
        self.layout.addWidget(self.hashrate_value, 1, 2)
        
        self.layout.addWidget(self.graph_rb3, 2, 0)
        self.layout.addWidget(self.avg_hashrate_label, 2, 1)
        self.layout.addWidget(self.avg_hashrate_value, 2, 2)
        
        self.layout.addWidget(self.graph_rb4, 3, 0)
        self.layout.addWidget(self.power_consumption_label, 3, 1)
        self.layout.addWidget(self.power_consumption_value, 3, 2)

        self.setLayout(self.layout)


        
class MonitorTab(QWidget):
    def __init__(self, parent, start_scan_method, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.start_scan_method = start_scan_method

        self.layout = QVBoxLayout()
        self.data_by_ip = {}
        self.total_hashrate_by_model = {}
        self.asic_count_history = []  # История количества ASIC-устройств

        self.current_annotation = None
        self.hashrate_history = []
        self.power_consumption_history = []
        self.avg_hashrate_history = []

        self.time_history = []
        self.init_ui()

    def init_ui(self):
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

        self.radio_buttons_layout = QHBoxLayout()
        self.real_time_rb = QRadioButton("Real Time")
        self.real_time_rb.setChecked(True)
        self.last_24_hours_rb = QRadioButton("Last 24 Hours")
        self.last_month_rb = QRadioButton("Last Month")
        self.radio_buttons_layout.addWidget(self.real_time_rb, alignment=Qt.AlignTop)
        self.radio_buttons_layout.addWidget(self.last_24_hours_rb, alignment=Qt.AlignTop)
        self.radio_buttons_layout.addWidget(self.last_month_rb, alignment=Qt.AlignTop)
        self.radio_buttons_layout.addStretch(1)
        self.layout.addLayout(self.radio_buttons_layout)

        self.timeframe_group = QButtonGroup(self)
        self.timeframe_group.addButton(self.real_time_rb, 0)
        self.timeframe_group.addButton(self.last_24_hours_rb, 1)
        self.timeframe_group.addButton(self.last_month_rb, 2)
        self.timeframe_group.buttonClicked.connect(self.update_graph)

        # Создание графиков
        self.figure = Figure(figsize=(10, 8), dpi=100)
        self.canvas = FigureCanvas(self.figure)
        self.ax = self.figure.add_subplot(111)
        
        # Дополнительные графики
        self.figure_avg_hashrate = Figure(figsize=(10, 8), dpi=100)
        self.canvas_avg_hashrate = FigureCanvas(self.figure_avg_hashrate)
        self.ax_avg_hashrate = self.figure_avg_hashrate.add_subplot(111)

        self.figure_power_consumption = Figure(figsize=(10, 8), dpi=100)
        self.canvas_power_consumption = FigureCanvas(self.figure_power_consumption)
        self.ax_power_consumption = self.figure_power_consumption.add_subplot(111)
        
        # Создание нового графика для отображения количества ASIC-устройств
        self.figure_asic_count = Figure(figsize=(10, 8), dpi=100)
        self.canvas_asic_count = FigureCanvas(self.figure_asic_count)
        self.ax_asic_count = self.figure_asic_count.add_subplot(111)

        # Сначала делаем его невидимым график 
        self.canvas_asic_count.setVisible(False)  
        self.canvas_avg_hashrate.setVisible(False)
        self.canvas_power_consumption.setVisible(False)
        
        # Добавляем новый график в layout
        self.layout.addWidget(self.canvas)
        self.layout.addWidget(self.canvas_avg_hashrate)
        self.layout.addWidget(self.canvas_power_consumption)
        self.layout.addWidget(self.canvas_asic_count)
        
        self.refresh_button = QPushButton("Обновить")
        self.refresh_button.clicked.connect(self.start_scan)
        self.layout.addWidget(self.refresh_button)

         # Инициализация аннотаций для каждого графика
        self.annotations = {
            'main': None,
            'avg_hashrate': None,
            'power_consumption': None,
            'asic_count': None
        }


         # Добавляем подписки на события наведения и выхода курсора для каждого графика
        self.canvas.mpl_connect('motion_notify_event', self.on_hover)
        self.canvas.mpl_connect('axes_leave_event', self.on_leave)
        
        self.canvas_avg_hashrate.mpl_connect('motion_notify_event', self.on_hover)
        self.canvas_avg_hashrate.mpl_connect('axes_leave_event', self.on_leave)
        
        self.canvas_power_consumption.mpl_connect('motion_notify_event', self.on_hover)
        self.canvas_power_consumption.mpl_connect('axes_leave_event', self.on_leave)
        
        self.canvas_asic_count.mpl_connect('motion_notify_event', self.on_hover)
        self.canvas_asic_count.mpl_connect('axes_leave_event', self.on_leave)


        
        self.info_panel.graph_group.buttonClicked.connect(self.switch_graph)

        self.setLayout(self.layout)


    # линию для графика
    def switch_graph(self):
        selected_graph_id = self.info_panel.graph_group.checkedId()
    
         # Сначала делаем все графики невидимыми
        self.canvas.setVisible(False)
        self.canvas_avg_hashrate.setVisible(False)
        self.canvas_power_consumption.setVisible(False)
        self.canvas_asic_count.setVisible(False)
    
         # Теперь делаем видимым только выбранный график
        if selected_graph_id == 0:
            self.canvas_asic_count.setVisible(True)
        elif selected_graph_id == 1:
            self.canvas.setVisible(True)
        elif selected_graph_id == 2:
            self.canvas_avg_hashrate.setVisible(True)
        elif selected_graph_id == 3:
            self.canvas_power_consumption.setVisible(True)



    def start_scan(self):
        self.start_scan_method()

   

    @pyqtSlot(dict)
    def receive_from_scan(self, data):  
        is_final = data.get('is_final', False)
        if is_final:
            self.is_final_received = True
            self.finalize_update()
            return

        ip_address = data.get('ip_address')
        if not ip_address:
            return

        self.data_by_ip[ip_address] = data
        self.aggregate_data_by_model()
        self.update_info_panel()

        total_hashrate = sum([data['hashrate'] for data in self.total_hashrate_by_model.values()])
        total_power_consumption = sum([data['power_consumption'] for data in self.total_hashrate_by_model.values()])
    
        # Добавление данных в историю для всех графиков
        noise = random.uniform(-0.5, 0.5)
        self.hashrate_history.append(total_hashrate + noise)
        total_avg_hashrate = sum([data['avg_hashrate'] for data in self.total_hashrate_by_model.values()])
        self.avg_hashrate_history.append(total_avg_hashrate + noise)

        # Добавление данных в историю для всех графиков
        noise = random.uniform(-0.5, 0.5)
        self.hashrate_history.append(total_hashrate + noise)

        # Эта строка будет добавлять средний хэшрейт к истории
        total_avg_hashrate = sum([data['avg_hashrate'] for data in self.total_hashrate_by_model.values()])
        self.avg_hashrate_history.append(total_avg_hashrate + noise)

        self.power_consumption_history.append(total_power_consumption + noise)
        self.time_history.append(datetime.now())

      
        # В методе receive_from_scan класса MonitorTab
        total_count = sum([data['count'] for data in self.total_hashrate_by_model.values()])
        self.asic_count_history.append(total_count)


       

    
    @pyqtSlot()
    def finalize_update(self):
        if self.is_final_received:
            self.update_graph()
            self.is_final_received = False

    def aggregate_single_device_for_first_graph(self, ip, data):
        model = self.determine_model(data)
        if not model:
            return None

        hash_rate_key = 'GHS 5s' if model == 'Antminer' else 'GHSmm' if model == 'Avalon' else 'MHS_5s'
        hash_rate = float(data.get(hash_rate_key, 0))
        hash_rate_ths = hash_rate / 1000.0
   
        return model, hash_rate_ths

    def aggregate_single_device_for_avg_hashrate(self, ip, data):
        model = self.determine_model(data)
        if not model:
            return None

        # Используем ключи, которые представляют средний хешрейт для каждой модели
        hash_rate_key = 'GHS av' if model == 'Antminer' else 'GHSavg' if model == 'Avalon' else 'HS_RT'
        hash_rate = float(data.get(hash_rate_key, 0))
        hash_rate_ths = hash_rate / 1000.0

        return model, hash_rate_ths



    def aggregate_power_consumption(self, ip, data):
        model = self.determine_model(data)
        if not model:
            return None
        if model == 'Antminer':

            power_consumption_keys = ['chain_consumption1', 'chain_consumption2', 'chain_consumption3']
            power_consumption = sum([float(data.get(key, 0)) for key in power_consumption_keys])
        elif model == 'Avalon':
            power_consumption = float(data.get('PS', '0').split()[-1])
        else:
            power_consumption = float(data.get('Power', 0))
    
        power_consumption_kw = power_consumption * 0.001

        return model, power_consumption_kw


    def aggregate_all_data_for_ip(self, ip, data):
        return (
            self.aggregate_single_device_for_first_graph(ip, data),
            self.aggregate_single_device_for_avg_hashrate(ip, data),
            self.aggregate_power_consumption(ip, data)
        )



   
    def aggregate_data_by_model(self):
        self.total_hashrate_by_model.clear()

        with ThreadPoolExecutor(max_workers=20) as executor:
            futures = {executor.submit(self.aggregate_all_data_for_ip, ip, data): ip for ip, data in self.data_by_ip.items()}

            for future in as_completed(futures):
                ip = futures[future]
                try:
                    results = future.result()
                except Exception as exc:
                    print(f"Ошибка при обработке данных для IP {ip}: {exc}")
                    continue

                model_for_first_graph, hash_rate_ths = results[0]
                model_for_avg_hashrate, avg_hash_rate_ths = results[1]
                model_for_power, power_consumption_kw = results[2]

                # Предполагается, что все три функции агрегации возвращают модель в одинаковом формате.
                # Поэтому мы можем использовать любую из моделей для дальнейших вычислений.
                model = model_for_first_graph

                current_model_data = self.total_hashrate_by_model.get(model, {'hashrate': 0, 'count': 0, 'power_consumption': 0, 'avg_hashrate': 0})

                current_model_data['count'] += 1
                current_model_data['hashrate'] += hash_rate_ths
                current_model_data['avg_hashrate'] += avg_hash_rate_ths
                current_model_data['power_consumption'] += power_consumption_kw

            # Сохранение обновлённых данных обратно в словарь
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
        # Определяем график и его аннотацию
        if event.inaxes == self.ax:
            graph_key = 'main'
            current_data = self.hashrate_history
            color = '#0DDEF4'
        elif event.inaxes == self.ax_avg_hashrate:
            graph_key = 'avg_hashrate'
            current_data = self.avg_hashrate_history
            color = 'lightgreen'
        elif event.inaxes == self.ax_power_consumption:
            graph_key = 'power_consumption'
            current_data = self.power_consumption_history
            color = 'lightcoral'
        elif event.inaxes == self.ax_asic_count:
            graph_key = 'asic_count'
            current_data = self.asic_count_history
            color = 'yellow'
        else:
            return

    # Если на этом графике уже есть аннотация, удаляем ее
        if self.annotations[graph_key]:
            self.annotations[graph_key].remove()
            self.annotations[graph_key] = None

        # Ищем ближайшую точку
        numeric_times = mdates.date2num(self.time_history)
        distance = np.sqrt((numeric_times - event.xdata)**2)
        closest_index = np.argmin(distance)

    # Получаем данные для этой точки
        closest_time = self.time_history[closest_index]
        closest_value = current_data[closest_index]

    # Форматируем текст подсказки
        annotation_text = f"Date: {closest_time.strftime('%Y-%m-%d')}\nTime: {closest_time.strftime('%H:%M:%S')}\nValue: {closest_value:.2f}"


    # Создаем подсказку и сохраняем ее в словаре
        self.annotations[graph_key] = event.inaxes.annotate(
            annotation_text, 
            (event.xdata, event.ydata),
            textcoords="offset points",
            xytext=(0,10),
            ha='center',
            fontsize=9,
            bbox=dict(boxstyle="round,pad=0.3", edgecolor=color, facecolor="white", linewidth=1.2),
            color=color
        )
    
        # Обновляем только тот канвас, на котором произошло событие
        if event.inaxes == self.ax:
            self.canvas.draw()
        elif event.inaxes == self.ax_avg_hashrate:
            self.canvas_avg_hashrate.draw()
        elif event.inaxes == self.ax_power_consumption:
            self.canvas_power_consumption.draw()
        elif event.inaxes == self.ax_asic_count:
            self.canvas_asic_count.draw()

    def on_leave(self, event):
        # Удаляем аннотацию для соответствующего графика и обновляем канвас
        for key, annotation in self.annotations.items():
            if annotation:
                annotation.remove()
                self.annotations[key] = None
                if key == 'main':
                    self.canvas.draw()
                elif key == 'avg_hashrate':
                    self.canvas_avg_hashrate.draw()
                elif key == 'power_consumption':
                    self.canvas_power_consumption.draw()
                elif key == 'asic_count':
                    self.canvas_asic_count.draw()



    def update_info_panel(self):
        
        # Вычисление общего хешрейта
        total_hashrate = sum([data['hashrate'] for data in self.total_hashrate_by_model.values()])

        # Вычисление среднего хешрейта
        total_avg_hashrate = self.avg_hashrate_history[-1] if self.avg_hashrate_history else 0

        # Получение общего количества устройств и общего потребления электроэнергии
        total_count = sum([data['count'] for data in self.total_hashrate_by_model.values()])
        total_power_consumption = sum([data['power_consumption'] for data in self.total_hashrate_by_model.values()])

        # Обновление информационной панели
        self.info_panel.asics_value.setText(str(total_count))
        self.info_panel.hashrate_value.setText(f"{total_hashrate:.2f} TH/s")
        self.info_panel.avg_hashrate_value.setText(f"{total_avg_hashrate:.2f} TH/s")

        self.info_panel.power_consumption_value.setText(f"{total_power_consumption:.2f} kW")


    def update_graph(self):
        selected_timeframe_id = self.timeframe_group.checkedId()
        last_time = datetime.now()

        if selected_timeframe_id == 0:  # 10 Minutes
            start_time = last_time - timedelta(minutes=10)
            time_formatter = DateFormatter("%H:%M")
            time_locator = md.MinuteLocator(interval=1)

        elif selected_timeframe_id == 1:  # 24 Hours
            start_time = last_time - timedelta(hours=24)
            time_formatter = DateFormatter("%H:%M")
            time_locator = md.HourLocator(interval=2)

        elif selected_timeframe_id == 2:  # 30 Days
            start_time = last_time - timedelta(days=30)
            time_formatter = DateFormatter("%d-%m")
            time_locator = md.DayLocator(interval=2)
  
        else:
            start_time = last_time - timedelta(minutes=10)


        # Common function to update a graph with given data
        def update_given_graph(ax, canvas, times, data, color):
            ax.clear()
            ax.set_facecolor("white")
            ax.plot(times, data, color=color)
            ax.fill_between(times, 0, data, facecolor=color)
            ax.set_xlim(start_time, last_time)
            ax.xaxis.set_major_locator(time_locator)
            ax.xaxis.set_major_formatter(time_formatter)
            canvas.draw()

        # Update the main hashrate graph
        filtered_indices = [i for i, time in enumerate(self.time_history) if time >= start_time]
        filtered_times = [self.time_history[i] for i in filtered_indices]
        filtered_hashrates = [self.hashrate_history[i] for i in filtered_indices]

        update_given_graph(self.ax, self.canvas, filtered_times, filtered_hashrates, 'lightblue')

        # Update the average hashrate graph
        filtered_avg_hashrates = [self.avg_hashrate_history[i] for i in filtered_indices]
        update_given_graph(self.ax_avg_hashrate, self.canvas_avg_hashrate, filtered_times, filtered_avg_hashrates, 'lightgreen')

        # Update the power consumption graph
        filtered_power_consumptions = [self.power_consumption_history[i] for i in filtered_indices]
        update_given_graph(self.ax_power_consumption, self.canvas_power_consumption, filtered_times, filtered_power_consumptions, 'lightcoral')

        # Обновление нового графика для количества ASIC-устройств
        filtered_asic_counts = [self.asic_count_history[i] for i in filtered_indices if i < len(self.asic_count_history)]

        
        # Удостоверимся, что размерности совпадают
        if len(filtered_times) == len(filtered_asic_counts):
            update_given_graph(self.ax_asic_count, self.canvas_asic_count, filtered_times, filtered_asic_counts, 'yellow')  # жёлтый цвет для нового графика
        else:
            print(f"Warning: Skipped updating the ASIC count graph due to size mismatch: len(filtered_times) = {len(filtered_times)}, len(filtered_asic_counts) = {len(filtered_asic_counts)}")


    def update_all_graphs(self):
        self.update_graph(self.ax, self.hashrate_history, "Total Hashrate (TH/s)")
        self.update_graph(self.ax_avg_hashrate, self.avg_hashrate_history, "Average Hashrate (TH/s)")
        self.update_graph(self.ax_power_consumption, self.power_consumption_history, "Power Consumption (kW)")
        self.update_graph(self.ax_asic_count, self.asic_count_history, "ASIC Count")  # Добавляем новый график
    

 

   

    def load_data(self):
        self.data = 'Data for moni hTab'

    def save_data(self):
        print(f"Saving data: {self.data}")