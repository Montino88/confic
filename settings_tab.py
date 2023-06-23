from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel, QLineEdit, QPushButton, QSizePolicy, QHBoxLayout, QSpacerItem, QDialog, QTableWidget, QTableWidgetItem
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtCore import pyqtSignal


class SettingsTab(QWidget):
    ip_range_changed = pyqtSignal(list)  # новый сигнал

    def __init__(self, parent=None):
        super(SettingsTab, self).__init__(parent)
        # Инициализация родительского класса и настройка начальных параметров

        layout = QVBoxLayout()
        # Создание вертикального макета

        ip_layout = QHBoxLayout() 
        # Создание горизонтального макета для ввода IP

        label = QLabel("Enter IP (e.g.,192.168.0.1 ): ")
        self.ip_input = QLineEdit()  
        self.ip_input.setFixedWidth(200) 
        # Создание метки и поля ввода для IP

        ip_layout.addWidget(label)
        ip_layout.addWidget(self.ip_input)
        # Добавление метки и поля ввода в макет

        self.add_button = QPushButton("+")
        self.add_button.setFixedWidth(20)
        self.remove_button = QPushButton("-")
        self.remove_button.setFixedWidth(20)
        # Создание кнопок для добавления и удаления IP

        self.add_button.clicked.connect(self.add_ip)
        self.remove_button.clicked.connect(self.remove_ip)
        # Подключение кнопок к функциям добавления и удаления IP

        ip_layout.addWidget(self.add_button)
        ip_layout.addWidget(self.remove_button)
        # Добавление кнопок в макет

        layout.addLayout(ip_layout)
        # Добавление макета ввода IP в основной макет

        self.ip_table = QTableWidget(0, 1)
        layout.addWidget(self.ip_table)
        # Создание таблицы для отображения добавленных IP и добавление ее в макет

        save_button = QPushButton("Save")
        save_button.clicked.connect(self.save_ip)
        save_button.setFixedSize(150, 40)
        # Создание кнопки сохранения и подключение ее к функции сохранения IP

        button_layout = QHBoxLayout()
        button_layout.addStretch(1)  
        button_layout.addWidget(save_button)
        button_layout.addStretch(1)
        # Создание макета для кнопки сохранения и добавление кнопки в макет

        layout.addLayout(button_layout)
        # Добавление макета кнопки в основной макет

        self.setLayout(layout)
        # Установка основного макета для виджета

    def save_ip(self):
        ip = self.ip_input.text()
        # Получение введенного IP

        with open('ip.txt', 'w') as f:
            f.write(ip)
        # Запись IP в файл

        dialog = CustomDialog(self)
        dialog.exec_()
        # Отображение диалогового окна с подтверждением

    def add_ip(self):
        ip = self.ip_input.text()
        # Получение введенного IP
        
        if ip:
            row = self.ip_table.rowCount()
            self.ip_table.insertRow(row)
            self.ip_table.setItem(row, 0, QTableWidgetItem(ip))
            # Если IP введен, добавление его в таблицу

    def remove_ip(self):
        row = self.ip_table.currentRow()
        # Получение выбранной строки

        if row != -1: 
            self.ip_table.removeRow(row)
            # Если строка выбрана, удаление ее из таблицы

    def save_settings(self):
        ip_range = []
        for row in range(self.ip_table.rowCount()):
            item = self.ip_table.item(row, 0)
            if item is not None:
                ip_range.append(item.text())
        self.ip_range_changed.emit(ip_range)



class CustomDialog(QDialog):
    def __init__(self, parent=None):
        super(CustomDialog, self).__init__(parent)
        # Инициализация родительского класса QDialog

        self.setWindowTitle("Settings")  
        # Установка заголовка окна

        self.setFixedSize(200, 100)
        # Установка фиксированного размера окна

        self.setStyleSheet("""
            QDialog {
                background-color: #262F34;
                border-radius: 10px;
            }
            QLabel {
                color: white;
            }
        """)
        # Установка пользовательского стиля для окна и метки

        layout = QVBoxLayout()
        # Создание вертикального макета

        label = QLabel("IP saved", self)
        label.setAlignment(Qt.AlignCenter)
        # Создание метки с текстом "IP saved" и выравнивание текста по центру

        layout.addWidget(label)
        # Добавление метки в макет

        self.setLayout(layout)
        # Установка макета для окна

        QTimer.singleShot(1000, self.close)
        # Закрытие окна через 1 секунду
