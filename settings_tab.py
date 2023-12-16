from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel, QLineEdit, QPushButton, QSizePolicy, QHBoxLayout, QSpacerItem, QDialog, QTableWidget, QTableWidgetItem
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtCore import pyqtSignal
from ipaddress import ip_network, AddressValueError
import os
from PyQt5 import QtGui



class SettingsTab(QWidget):
    ip_range_changed = pyqtSignal(list)  # новый сигнал
    ip_range_saved = pyqtSignal(list)  # Сигнал, испускаемый после сохранения IP-адресов
    credentials_updated = pyqtSignal(dict)  # Сигнал для передачи данных учетных записей


    def __init__(self, parent=None):
        super(SettingsTab, self).__init__(parent)
        layout = QVBoxLayout()
        self.changes_made = False  # Флаг, показывающий, были ли сделаны изменения

        ip_layout = QHBoxLayout() 
        self.ip_input = QLineEdit()  
        self.ip_input.setPlaceholderText("IP range (e.g., 192.168.1.1/24)")  # Установка подсказки в поле ввода
        self.ip_input.setFixedWidth(150) 
        ip_layout.addWidget(self.ip_input)

        self.add_button = QPushButton("+")
        self.add_button.setFixedWidth(20)
        self.remove_button = QPushButton("-")
        self.remove_button.setFixedWidth(20)

        self.add_button.clicked.connect(self.add_ip)
        self.remove_button.clicked.connect(self.remove_ip)

        ip_layout.addWidget(self.add_button)
        ip_layout.addWidget(self.remove_button)
        ip_layout.addStretch(1)  # Добавляем растягивающееся пространство после кнопок

        layout.addLayout(ip_layout)

        self.ip_table = QTableWidget(0, 1)  # Создаем таблицу с 0 строками и 1 столбцом
        self.ip_table.setHorizontalHeaderLabels(["IP Range"])  # Устанавливаем заголовок столбца
        self.ip_table.setMaximumHeight(150)
        self.ip_table.setFixedWidth(130)  # Установка фиксированной ширины для таблицы IP-адресов

        layout.addWidget(self.ip_table)

        # Применение стиля к заголовкам и ячейкам таблицы IP-адресов
        self.style_table_headers(self.ip_table)
        
        # Создаем и настраиваем таблицу модели, логина и пароля
        self.credentials_table = QTableWidget(0, 3)
        self.credentials_table.setHorizontalHeaderLabels(["Model", "Login", "Password"])
        self.credentials_table.setMaximumHeight(148)
        self.credentials_table.setMaximumWidth(318)

        self.initialize_models()
        layout.addWidget(self.credentials_table)

        # Применение стиля к заголовкам и ячейкам таблицы учетных данных
        self.style_table_headers(self.credentials_table)
        
        save_button = QPushButton("Save")
        save_button.clicked.connect(self.save_ip)
        save_button.setFixedSize(150, 40)
        
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

        button_layout = QHBoxLayout()
        button_layout.addStretch(1)
        button_layout.addWidget(save_button)
        button_layout.addStretch(1)
        layout.addLayout(button_layout)
        self.setLayout(layout)

        self.load_data()

    def initialize_models(self):
        models = ["VnishOS", "Avalonminer", "Whatsminer", "Antminer"]
        for model in models:
            row = self.credentials_table.rowCount()
            self.credentials_table.insertRow(row)
            model_item = QTableWidgetItem(model)
            model_item.setFlags(model_item.flags() & ~Qt.ItemIsEditable)  # Сделать ячейку нередактируемой
            self.credentials_table.setItem(row, 0, model_item)
            self.credentials_table.setItem(row, 1, QTableWidgetItem(""))
            self.credentials_table.setItem(row, 2, QTableWidgetItem(""))

    def style_table_headers(self, table):
        header = table.horizontalHeader()
        # Стиль для заголовков столбцов
        header.setStyleSheet("""
            QHeaderView::section {
                background-color: #262F34;  /* Цвет фона */
                color: white;               /* Цвет текста */
                font: bold;                 /* Жирный шрифт */
                border: 1px solid #6E6E6E;  /* Граница */
            }
        """)
        table.setFont(QtGui.QFont("Arial", 10))  # Шрифт для таблицы
        table.setStyleSheet("QTableWidget::item:selected { background-color: #4E4E4E; }")  # Цвет выделения


    def save_ip(self):
        self.save_data()  # Сохраняем IP-адреса и испускаем сигнал
        dialog = CustomDialog(self)
        dialog.exec_()
         # Собираем данные учетных записей
         # Собираем данные учетных записей
        credentials = {}
        for row in range(self.credentials_table.rowCount()):
            model = self.credentials_table.item(row, 0).text()
            login = self.credentials_table.item(row, 1).text()
            password = self.credentials_table.item(row, 2).text()
            if model and login and password:  # Убедитесь, что строки не пустые
                credentials[model] = {'login': login, 'password': password}

        # Испускаем сигнал с данными учетных записей
        print("Сохраненные учетные данные:", credentials)
        self.credentials_updated.emit(credentials)


    def hideEvent(self, event):
        super().hideEvent(event)
        self.save_data()  

    def add_ip(self):
        if self.ip_table.rowCount() < 5:
            ip = self.ip_input.text()
            if ip and self.validate_ip(ip):
                # Проверяем наличие IP в таблице
                for row in range(self.ip_table.rowCount()):
                    item = self.ip_table.item(row, 0)
                    if item is not None and item.text().strip() == ip.strip():
                       print(f"IP {ip} is already in the table.")
                       return
                # Если IP не найден, добавляем его
                row = self.ip_table.rowCount()
                self.ip_table.insertRow(row)
                self.ip_table.setItem(row, 0, QTableWidgetItem(ip))
                print(f"Added IP: {ip}")
                self.changes_made = True

    def remove_ip(self):
        row = self.ip_table.currentRow()
        if row != -1: 
            self.ip_table.removeRow(row)
            self.changes_made = True


    def save_data(self):
        print("Saving data for SettingsTab")
        ip_list = []

    # Сохраняем только заполненные строки
        for row in range(self.ip_table.rowCount()):
            item = self.ip_table.item(row, 0)
        
            # Если ячейка не пуста
            if item is not None and item.text().strip():
                ip_list.append(item.text().strip())
                filename = f"ip{row+1}.txt"
                with open(filename, 'w') as f:
                    f.write(item.text().strip())
                print(f"Saved IP address to {filename}: {item.text().strip()}")

        # Если ячейка пуста
            else:
                try:
                    filename = f"ip{row+1}.txt"
                    os.remove(filename)  # Удаляем файл, если он существует
                    print(f"Removed empty IP file {filename}")
                except FileNotFoundError:
                    pass

        if self.changes_made:
            self.ip_range_saved.emit(ip_list)
            self.changes_made = False  # Испускаем сигнал с обновленным списком IP-адресов




   

    def load_data(self):
        
        for idx in range(5):
           filename = f"ip{idx+1}.txt"
           open(filename, 'w').close()

        ip_list = []  # инициализируем список

        # Загрузка IP-адресов из файлов
        for idx in range(5):  # Предполагая, что у вас максимум 5 файлов
            filename = f"ip{idx+1}.txt"
            try:
                with open(filename, 'r') as f:
                    ip_address = f.read().strip()
                    if ip_address:  # добавляем адрес в список только если он не пустой
                        ip_list.append(ip_address)
            except FileNotFoundError:
                continue

        # Убираем дубликаты из списка
        unique_ips = list(set(ip_list))

        # Заполнение таблицы уникальными IP-адресами
        for ip in unique_ips:
            row = self.ip_table.rowCount()
            self.ip_table.insertRow(row)
            self.ip_table.setItem(row, 0, QTableWidgetItem(ip))
            print(f"Loaded IP address from ip{row+1}.txt: {ip}")




    def validate_ip(self, ip):
        try:
            ip_network(ip, strict=False)
            return True
        except AddressValueError:
            print(f"Invalid IP: {ip}")
            return False

class CustomDialog(QDialog):
    def __init__(self, parent=None):
        super(CustomDialog, self).__init__(parent)
        self.setWindowTitle("Settings")  
        self.setFixedSize(200, 100)
        self.setStyleSheet("""
            QDialog {
                background-color: #262F34;
                border-radius: 10px;
            }
            QLabel {
                color: white;
            }
        """)
        layout = QVBoxLayout()
        label = QLabel("IP saved", self)
        label.setAlignment(Qt.AlignCenter)
        layout.addWidget(label)
        self.setLayout(layout)
        QTimer.singleShot(1000, self.close)