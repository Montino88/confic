import socket
from PyQt5 import QtCore

import ipaddress
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel, QGridLayout, QPushButton, QFrame, QSpinBox, QLineEdit, QHBoxLayout, QDialog, QFormLayout
import json
from PyQt5.QtWidgets import QScrollArea, QSizePolicy
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QProgressBar
from PyQt5.QtGui import QPixmap
from PyQt5.QtWidgets import QLabel
from PyQt5 import QtWidgets, QtGui
from PyQt5.QtWidgets import QDialog, QVBoxLayout, QLabel, QProgressBar, QPushButton
from PyQt5.QtCore import Qt
from PyQt5.QtChart import QChart, QChartView, QLineSeries
from PyQt5.QtGui import QPen
from PyQt5.QtCore import Qt, QPointF
from PyQt5.QtWidgets import QApplication




class ASICDetailsDialog(QDialog):
    def __init__(self, data, parent=None):
        super().__init__(parent)
        self.setWindowModality(Qt.ApplicationModal)
        self.setWindowTitle("ASIC Details")

        self.layout = QVBoxLayout(self)

        self.ip_label = QLabel(f"IP Address: {data['ip']}")
        self.layout.addWidget(self.ip_label)

        self.status_label = QLabel(f"Status: {data['status']}")
        self.layout.addWidget(self.status_label)

        self.chips_temperature_label = QLabel(f"Chips temperature: {data['chips_temperature']}")  # Эта строка добавлена
        self.layout.addWidget(self.chips_temperature_label)

        self.fan_speed_progress_bar = QProgressBar()
        self.fan_speed_progress_bar.setValue(data['fan_speed'])
        self.layout.addWidget(self.fan_speed_progress_bar)

        self.temperature_progress_bar = QProgressBar()
        self.temperature_progress_bar.setValue(data['temperature'])
        self.layout.addWidget(self.temperature_progress_bar)

        self.chart_placeholder = QLabel("Здесь будет график")
        self.layout.addWidget(self.chart_placeholder)

        self.close_button = QPushButton("Закрыть")
        self.close_button.clicked.connect(self.close)
        self.layout.addWidget(self.close_button)


    

class ASICCell(QtWidgets.QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(60, 60)  # Minimum size of the card
        self.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)  # Allow resizing

        # Layout for the cell
        self.layout = QVBoxLayout(self)

        # IP input
        self.ip_address = QtWidgets.QLineEdit(self)
        self.ip_address.setStyleSheet("color: black; font-size: 14px;")
        self.layout.addWidget(self.ip_address)

        # Hashrate label
        self.hashrate_label = QtWidgets.QLabel(self)
        self.hashrate_label.setStyleSheet("color: black; font-size: 12px;")
        self.layout.addWidget(self.hashrate_label)

        # Temperature of the chips
        self.chips_temperature_label = QtWidgets.QLabel(self)
        self.chips_temperature_label.setStyleSheet("color: black; font-size: 12px;")
        self.layout.addWidget(self.chips_temperature_label)

        # Fan speed as progress bar
        self.fan_speed_bar = QtWidgets.QProgressBar(self)
        self.fan_speed_bar.setFixedHeight(10)  # Set the height of the progress bar
        self.fan_speed_bar.setMaximumWidth(80)  # Set the maximum width of the progress bar
        self.fan_speed_bar.setStyleSheet("""
            QProgressBar {
                border: 2px solid grey;
                border-radius: 5px;
                text-align: center;
                color: black;
            }

            QProgressBar::chunk {
                background-color: #05B8CC;
                width: 10px;
                margin: 0.5px;
            }
        """)  # Change the color of the text inside the progress bar to black

        self.layout.addWidget(self.fan_speed_bar)

        # Initially hide the labels and the progress bar
        self.hashrate_label.hide()
        self.chips_temperature_label.hide()
        self.fan_speed_bar.hide()

    def save_ip(self):
        if self.ip_address.text():  # Check if the IP address is entered
            # Hide the IP input
            self.ip_address.setVisible(False)
            # Show the labels and the progress bar
            self.hashrate_label.setVisible(True)
            self.chips_temperature_label.setVisible(True)
            self.fan_speed_bar.setVisible(True)
            # Process pending events
            QApplication.processEvents()
            # Change the size of the card
            self.setFixedSize(100, 100)  # Set the width and height to 100 pixels
        self.ip_address_value = self.ip_address.text()


    def update_data(self, data):
        print(f"Обновление данных ячейки: {data}")

        if 'GHS av' in data:
           hashrate = data['GHS av'] / 1000  # Convert from GH/s to TH/s
           self.hashrate_label.setText(f"Hashrate: {hashrate:.1f} TH/s")
           print(f"Hashrate: {hashrate:.1f} TH/s")

        chip_temp_fields = ['temp2_1', 'temp2_2', 'temp2_3']
        temperatures = []
        for field in chip_temp_fields:
            if field in data:
                temperatures.append(int(data[field]))  # Преобразовываем значения в int перед добавлением в список
        if temperatures:
           temp_max = max(temperatures)
           temp_min = min(temperatures)  # Get the minimum temperature
           self.chips_temperature_label.setText(f"Max chip temperature: {temp_max}\nMin chip temperature: {temp_min}")
           print(f"Max chip temperature: {temp_max}")
           print(f"Min chip temperature: {temp_min}")

        # Fan speed progress bar
        if 'fan_pwm' in data:
           fan_speed = data['fan_pwm']
           self.fan_speed_bar.setValue(fan_speed)
           self.fan_speed_label.setText(f"{fan_speed}%")  # Update fan speed label

         # Set color of the cell based on the status
        if 'state' in data:
           if data['state'] == 'mining':
               self.setStyleSheet("background-color: lightblue;")
           else:
               self.setStyleSheet("background-color: red;")

        self.update()  # Force update of the interface





    

    
   
    def mousePressEvent(self, event):
        hashrate_ghs = float(self.hashrate_label.text())  # Извлекаем хешрейт как число
        hashrate_ths = hashrate_ghs / 1000  # Преобразуем в терахеши
        data = {
              'ip': self.ip_address.text(),
              'status': 'Placeholder status',
              'hashrate': f"{hashrate_ths:.2f} TH/s",  # Передаем хешрейт в терахешах
              'chips_temperature': self.chips_temperature_label.text(),
              'fan_speed': self.fan_speed_bar.value()
        }
        self.details_dialog = ASICDetailsDialog(data, self)
        self.details_dialog.show()

class Shelf(QWidget):
    def __init__(self, shelf_name, asic_count, asic_per_row, parent=None):
        super(Shelf, self).__init__(parent)
        self.layout = QGridLayout(self)

        self.shelf_name_label = QLabel(shelf_name, self)
        self.layout.addWidget(self.shelf_name_label, 0, 0, 1, 1)

        self.asic_cells = []
        for i in range(asic_count):
            cell = ASICCell(self)
            self.layout.addWidget(cell, i // asic_per_row + 1, i % asic_per_row)
            self.asic_cells.append(cell)


class Container(QWidget):
    def __init__(self, container_name, shelf_count, asic_count, asic_per_row, parent=None):
        super(Container, self).__init__(parent)
        self.layout = QVBoxLayout(self)

        self.container_name_label = QLabel(container_name, self)
        self.layout.addWidget(self.container_name_label)

        self.shelves = []
        for i in range(shelf_count):
            shelf = Shelf(f"Shelf {i + 1}", asic_count, asic_per_row, self)
            self.layout.addWidget(shelf)
            self.shelves.append(shelf)


class GeneratorDialog(QDialog):
    def __init__(self, parent=None):
        super(GeneratorDialog, self).__init__(parent)
        self.layout = QFormLayout(self)

        self.container_name_label = QLabel("Имя контейнера:")
        self.container_name_input = QLineEdit()
        self.layout.addRow(self.container_name_label, self.container_name_input)

        self.shelf_count_label = QLabel("Количество полок на стойке:")
        self.shelf_count_input = QSpinBox()
        self.shelf_count_input.setMinimum(1)
        self.layout.addRow(self.shelf_count_label, self.shelf_count_input)

        self.asic_count_label = QLabel("Количество ASIC на полке:")
        self.asic_count_input = QSpinBox()
        self.asic_count_input.setMinimum(1)
        self.layout.addRow(self.asic_count_label, self.asic_count_input)

        self.asic_per_row_label = QLabel("Количество ASIC в ряду:")
        self.asic_per_row_input = QSpinBox()
        self.asic_per_row_input.setMinimum(1)
        self.layout.addRow(self.asic_per_row_label, self.asic_per_row_input)

        self.generate_button = QPushButton("Генерировать")
        self.generate_button.clicked.connect(self.accept)
        self.layout.addWidget(self.generate_button)


class TableTab(QWidget):
    def __init__(self, parent=None):
        super(TableTab, self).__init__(parent)
        self.layout = QVBoxLayout()

        self.controls_layout = QHBoxLayout()
        self.generate_button = QPushButton("Генерировать")
        self.generate_button.clicked.connect(self.open_generator_dialog)
        self.controls_layout.addWidget(self.generate_button)

        self.save_button = QPushButton("Save")
        self.save_button.clicked.connect(self.save_ips)
        self.controls_layout.addWidget(self.save_button)

        self.update_button = QPushButton("Обновить")
        self.update_button.clicked.connect(self.update_cells)
        self.controls_layout.addWidget(self.update_button)

        self.controls_layout.addStretch(1)
        self.layout.addLayout(self.controls_layout)

        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOn)
        self.scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOn)
        self.container_widget = QWidget()
        self.container_layout = QVBoxLayout(self.container_widget)
        self.scroll_area.setWidget(self.container_widget)
        self.layout.addWidget(self.scroll_area)

        self.setLayout(self.layout)

    def generate_asic_layout(self):
        container_name = self.generator_dialog.container_name_input.text()
        shelf_count = self.generator_dialog.shelf_count_input.value()
        asic_count = self.generator_dialog.asic_count_input.value()
        asic_per_row = self.generator_dialog.asic_per_row_input.value()

        for i in reversed(range(self.container_layout.count())):
            self.container_layout.itemAt(i).widget().setParent(None)

        container = Container(container_name, shelf_count, asic_count, asic_per_row, self)
        self.container_layout.addWidget(container)

    def save_ips(self):
        for i in range(self.container_layout.count()):
            container = self.container_layout.itemAt(i).widget()
            for shelf in container.shelves:
                for cell in shelf.asic_cells:
                    cell.save_ip()

    def update_cells(self):
        print("Обновление ячеек...")
        for i in range(self.container_layout.count()):
            container = self.container_layout.itemAt(i).widget()
            for shelf in container.shelves:
                for cell in shelf.asic_cells:
                    ip = cell.ip_address.text()
                    print(f"Обработка IP-адреса: {ip}")
                    try:
                        data = self.send_command({"command": "stats"}, ip)
                        if data and 'STATS' in data and len(data['STATS']) > 1:
                            cell.update_data(data['STATS'][1])
                           
                            temps2 = [int(t) for t in data['STATS'][1]['temp_chip2'].split('-')]
                            temps3 = [int(t) for t in data['STATS'][1]['temp_chip3'].split('-')]
                            temp_max = max(temps2 + temps3)
                            temp_min = min(temps2 + temps3)
                            
                            cell.chips_temperature_label.setText(f"{temp_max}-{temp_min} C^")
                            cell.fan_speed_bar.setValue(data['STATS'][1]['fan_pwm'])
                    except Exception as e:
                        print(f"Ошибка при обновлении ячейки: {e}")




    def send_command(self, command, ip_address, port=4028):
        print(f"Отправка команды: {command} на IP: {ip_address}")

        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            sock.connect((ip_address, port))
            sock.sendall(json.dumps(command).encode())
            data = sock.recv(4096)
            sock.close()
            data = data.replace(b'\x00', b'')
            data_str = data.decode()
            data_str = data_str.replace("}{", "}, {")
        except Exception as e:
            return {'error': str(e)}

        print(f"Получены данные: {data_str}")
        return json.loads(data_str)

    def open_generator_dialog(self):
        self.generator_dialog = GeneratorDialog(self)
        result = self.generator_dialog.exec_()
        if result == QDialog.Accepted:
            self.generate_asic_layout()

    def load_data(self):
        # Load here the data you need
        pass

    def save_data(self):
        # Save here the data you need
        pass
