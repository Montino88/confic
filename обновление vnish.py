from PyQt5 import QtWidgets, QtCore
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QTableWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QProgressBar, QWidget, QLabel, QLineEdit, QFrame, QGridLayout, QMessageBox, QCheckBox
)
from PyQt5.QtGui import QIcon, QPixmap
from PyQt5.QtCore import QSettings
from scan_thread import ScanThread  # Убедитесь, что у вас есть файл scan_thread.py в той же папке
from PyQt5.QtCore import QThread, pyqtSlot
from PyQt5.QtWidgets import QTableWidgetItem
from PyQt5.QtCore import Qt, QTimer, QRect
import ipaddress

#класс уведомление 
class TimedMessage(QLabel):
    def __init__(self, message, parent=None):
        super().__init__(message, parent)
        self.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Dialog)
        self.setWindowModality(Qt.WindowModal)
        self.setStyleSheet("""
            background-color: #2b2b2b; 
            color: #ffffff; 
            font-size: 12pt; 
            padding: 15px; 
            border-radius: 10px;
            border: 2px solid #555;
            """)  # Стилизация

        # Добавление иконки
        self.icon = QLabel(self)
        self.icon.setPixmap(QPixmap('path_to_error_icon.png').scaled(40, 40, Qt.KeepAspectRatio))  # Путь к иконке ошибки
        self.icon.setGeometry(10, 10, 40, 40)

    def show_message(self, duration=3000):
        # Установка фиксированных размеров и позиционирование
        message_width = 250  # Ширина сообщения
        message_height = 80  # Высота сообщения
        screen_geometry = QApplication.desktop().screenGeometry()
        screen_width = screen_geometry.width()

        self.setGeometry(QRect(screen_width - message_width - 20, 20, message_width, message_height))
        self.show()
        QTimer.singleShot(duration, self.hide)  # Автоматическое исчезновение через duration миллисекунд



#главный класс 
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setGeometry(300, 300, 800, 600)
        self.setWindowTitle("Application")
        #в начале черный 
        self.current_theme = "dark"

        # Создаем объект для хранения настроек
        self.settings = QSettings("YourCompanyName", "YourAppName")  # Настройте на свое усмотрение

        self.init_ui()  #  инициализируем пользовательский интерфейс

        # Загружаем сохраненные настройки
        self.load_settings()  # Затем загружаем настройки

        self.timed_message = TimedMessage("", self)

       

    def init_ui(self):
        self.auth_widget = QWidget(self)  # Виджет для экрана авторизации
        self.auth_layout = QVBoxLayout(self.auth_widget)  # Вертикальное расположение элементов авторизации
        self.setCentralWidget(self.auth_widget)  # Установка виджета авторизации в центр окна

        self.init_auth_interface()  # Инициализация интерфейса авторизации

    def init_auth_interface(self):
        self.auth_frame = QFrame(self)  # Создание рамки для элементов авторизации
        self.auth_frame.setFrameShape(QFrame.StyledPanel)  # Установка стиля рамки
        self.auth_frame_layout = QGridLayout()  # Сеточное расположение элементов внутри рамки

        # Создание и настройка элементов для авторизации
        self.auth_label = QLabel("VhishNet/update", self)
        self.password_input = QLineEdit(self)
        self.ip_range_input = QLineEdit(self)
        self.login_button = QPushButton("Вход", self)

        self.password_input.setPlaceholderText("Введите пароль")
        self.ip_range_input.setPlaceholderText("Введите диапазон IP")
        self.login_button.setMinimumWidth(300)
        self.login_button.clicked.connect(self.on_login_clicked)  # Подключение обработчика нажатия кнопки

        # Добавление элементов в макет
        self.auth_frame_layout.addWidget(self.auth_label, 0, 0, 1, 2)
        self.auth_frame_layout.addWidget(self.password_input, 1, 0, 1, 2)
        self.auth_frame_layout.addWidget(self.ip_range_input, 2, 0, 1, 2)
        self.auth_frame_layout.addWidget(self.login_button, 3, 0, 1, 2)

        # Установка макета в рамку и добавление рамки в виджет авторизации
        self.auth_frame.setLayout(self.auth_frame_layout)
        self.auth_layout.addWidget(self.auth_frame, 0, QtCore.Qt.AlignCenter)

    def load_settings(self):
        # Загружаем сохраненные значения
        ip_range = self.settings.value("ipRange", "")
        password = self.settings.value("password", "")
        # Устанавливаем значения в поля ввода
        self.ip_range_input.setText(ip_range)
        self.password_input.setText(password)
    
    def save_settings(self, ip_range, password):
        # Сохраняем значения в настройках
        self.settings.setValue("ipRange", ip_range)
        self.settings.setValue("password", password)
        # Выводим сообщение о сохранении в консоль
        print(f"Сохранены данные: IP диапазон - {ip_range}, Пароль - {password}")
    
    def on_login_clicked(self):
        # Получаем значения из полей ввода
        password = self.password_input.text()
        ip_range = self.ip_range_input.text()
        # Переходим к основному интерфейсу
        self.init_main_interface()
        self.setCentralWidget(self.main_widget)
        # Сохраняем настройки при успешной авторизации
        self.save_settings(ip_range, password)
        # Создаем и запускаем поток сканирования
        self.start_scan(ip_range, password)

    def start_scan(self, ip_range, password):
        self.table_widget.clearContents()
        self.table_widget.setRowCount(0)
        # Создаем и запускаем поток сканирования
        self.scan_thread = ScanThread([ip_range], {"VnishOS": {"password": password}})
        self.scan_thread.ip_processed_signal.connect(self.update_table)
        self.scan_thread.scan_finished_signal.connect(self.scan_finished)
        self.scan_thread.error_signal.connect(self.show_error_message)
        self.scan_thread.progress_signal.connect(self.update_progress_bar)


        self.scan_thread.start()

    #  обновление прогресс бара 
    @pyqtSlot(int)
    def update_progress_bar(self, percent):
        self.progress_bar.setValue(percent)
  
    #главный интерфейс 
    def init_main_interface(self):
        # Создаем главный виджет и его макет
        self.main_widget = QWidget()
        self.main_layout = QVBoxLayout(self.main_widget)
       
        # Создание и настройка верхней панели
        self.top_panel = QWidget(self)
        self.top_panel_layout = QHBoxLayout(self.top_panel)
        self.top_panel.setFixedHeight(50)  # Устанавливаем фиксированную высоту для панели
    
        # Добавляем логотип и кнопку переключения темы на верхнюю панель
        self.logo_label = QLabel(self.top_panel)
        self.logo_label.setPixmap(QPixmap('path_to_logo.png'))  # Установка изображения логотипа
        self.logo_label.setFixedSize(68, 68)  # Установка размера логотипа
        self.top_panel_layout.addWidget(self.logo_label)
    
        # Добавляем растягивающий элемент перед кнопкой переключения темы для её сдвига вправо
        self.top_panel_layout.addStretch()
    
        # Создаем и настраиваем кнопку переключения тем
        self.theme_toggle_button = QPushButton("", self.top_panel)
        theme_toggle_icon = QIcon("path_to_theme_icon.png")  # Замените на путь к иконке переключения темы
        self.theme_toggle_button.setIcon(theme_toggle_icon)
        self.theme_toggle_button.setIconSize(QtCore.QSize(30, 30))  # Установка размера иконки
        self.theme_toggle_button.setFixedSize(30, 30)  # Установка размера кнопки
        self.theme_toggle_button.clicked.connect(self.toggle_theme)
        self.top_panel_layout.addWidget(self.theme_toggle_button)

        self.set_theme(self.current_theme)  # Переместите это ниже после создания всех виджетов

    
        # Размещаем верхнюю панель в верхней части главного макета
        self.main_layout.addWidget(self.top_panel, 0, QtCore.Qt.AlignTop)
    
        # Отступ под логотип
        self.logo_space = QLabel()
        self.logo_space.setFixedHeight(20)
        self.main_layout.addWidget(self.logo_space)
    
        # Прогресс-бар
        self.progress_bar = QProgressBar()
        self.main_layout.addWidget(self.progress_bar)

        self.progress_bar.setStyleSheet("""
            QProgressBar {
            text-align: center;
            }
        """)
       
    
        # Таблица данных
        self.table_widget = QTableWidget()
        self.table_widget.setColumnCount(8)  # Задаем количество столбцов
        # Заголовки столбцов таблицы
        self.table_widget.setHorizontalHeaderLabels([
            'Check', 'IP', 'Status', 'Model + Chips', 'Firmware Version',
            'Build Date', 'Platform', 'Installation Type'
        ])
        self.main_layout.addWidget(self.table_widget)
       # Сделать таблицу не редактируемой
        self.table_widget.setEditTriggers(QTableWidget.NoEditTriggers)

        # Установка ширины первого столбца (чекбокс)
        self.table_widget.setColumnWidth(0, 20)

        # Включение сортировки
        self.table_widget.setSortingEnabled(True)
        
        # Кнопка обновления с иконкой
        self.update_button = QPushButton("Auto Update", self.main_widget)
        update_icon = QIcon("path_to_update_icon.png")  # Замените на путь к иконке обновления
        self.update_button.setIcon(update_icon)
        self.update_button.setIconSize(QtCore.QSize(40, 40))  # Установка размера иконки
        self.update_button.clicked.connect(self.on_update_button_click)
        self.main_layout.addWidget(self.update_button)

        # Добавление чекбокса под таблицей
        self.global_checkbox = QCheckBox("Выбрать все")
        self.global_checkbox.stateChanged.connect(self.global_checkbox_state_changed)
        self.main_layout.addWidget(self.global_checkbox)
    
        # Устанавливаем главный виджет в центральное место окна
        self.setCentralWidget(self.main_widget)

    def init_top_panel(self):
       # Создаем виджет для верхней панели и устанавливаем его макет
        self.top_panel = QWidget()
        self.top_panel_layout = QHBoxLayout()
        self.top_panel.setLayout(self.top_panel_layout)
    
        # Устанавливаем фиксированную высоту для верхней панели
        self.top_panel.setFixedHeight(50)
    
    # Добавляем логотип в левой части панели
        self.logo_label = QLabel()
        logo_pixmap = QPixmap('path_to_your_logo.png')  # Укажите путь к логотипу
        self.logo_label.setPixmap(logo_pixmap)
        self.logo_label.setFixedSize(68, 68)  # Размер логотипа
        self.top_panel_layout.addWidget(self.logo_label)
    
    # Добавляем растягивающийся элемент, чтобы элементы управления выравнивались по правому краю
        self.top_panel_layout.addStretch()
      
    # Создаем кнопку для переключения темы и добавляем её в правой части панели
        self.theme_toggle_button = QPushButton()
        theme_toggle_icon = QIcon('path_to_theme_toggle_icon.png')  # Укажите путь к иконке переключения темы
        self.theme_toggle_button.setIcon(theme_toggle_icon)
        self.theme_toggle_button.setIconSize(QtCore.QSize(30, 30))  # Размер иконки
        self.theme_toggle_button.setFixedSize(30, 30)  # Размер кнопки
        self.theme_toggle_button.clicked.connect(self.toggle_theme)  # Связываем кнопку с функцией переключения темы
        self.top_panel_layout.addWidget(self.theme_toggle_button)
    
    # Добавляем верхнюю панель в основной макет окна
        self.main_layout.addWidget(self.top_panel, alignment=QtCore.Qt.AlignTop)
  
    
    def on_update_button_click(self):
        print("Auto Update clicked")

    def toggle_theme(self):
        self.current_theme = "light" if self.current_theme == "dark" else "dark"
        self.set_theme(self.current_theme)

    def set_theme(self, theme):
        if theme == "dark":
            self.setStyleSheet("""
                QWidget { background-color: #2b2b2b; color: #d3d3d3; }
                QTableWidget { background-color: #333333; color: #ffffff; selection-background-color: #333333; }
                QProgressBar { border: 2px solid #5c5c5c; background-color: #333333; color: #ffffff; }
                QHeaderView::section { background-color: #333333; color: #ffffff; }
                QPushButton { background-color: #555555; color: #ffffff; border: none; }
                QPushButton:hover { background-color: #777777; }
                QLabel { color: #ffffff; }
            """)
        else:
            self.setStyleSheet("""
                QWidget { background-color: #ADD8E6; color: #000000; }
                QTableWidget { background-color: #ffffff; color: #000000; selection-background-color: #ffffff; }
                QProgressBar { border: 2px solid #c0c0c0; background-color: #ffffff; color: #000000; }
                QHeaderView::section { background-color: #ADD8E6; color: #000000; }
                QPushButton { background-color: #ADD8E6; color: #000000; border: none; }
                QPushButton:hover { background-color: #B0E0E6; }
               QLabel { background-color: #ADD8E6; }
            """)

        # Обновление стилей для кнопки и логотипа
        self.theme_toggle_button.setFixedSize(16, 16)  # Изменение размера кнопки переключения темы
        self.logo_label.setFixedSize(68, 68)  # Установка размера логотипа

    @pyqtSlot(dict, int)
    def update_table(self, data, count):
        # Предполагаем, что 'data' это словарь, где ключ — это IP, а значение — это данные майнера
        for ip, miner_data in data.items():
            print(f"Обновление таблицы для IP {ip} с данными: {miner_data}")
            self.process_vnish_data(ip, miner_data)
    
    def find_or_create_row(self, ip):
        for row in range(self.table_widget.rowCount()):
            if self.table_widget.item(row, 1) and self.table_widget.item(row, 1).text() == ip:
                return row, False
        row_index = self.table_widget.rowCount()
        self.table_widget.insertRow(row_index)
        ip_item = QTableWidgetItem(ip)
        ip_item.setTextAlignment(Qt.AlignCenter)
        self.table_widget.setItem(row_index, 1, ip_item)
        return row_index, True
    
    def process_vnish_data(self, ip, data):
        print(f"Полные данные для IP {ip}: {data}")

        if not isinstance(data, dict):
            print(f"Данные для IP {ip} не являются словарем")
            return

    # Изменен способ доступа к данным
        info_data = data.get('info', {})

        print(f"IP: {ip}, Info Data: {info_data}")

    # Поиск или создание строки в таблице для данного IP
        row_for_ip, is_new_row = self.find_or_create_row(ip)

    # Если строка новая, добавляем чекбокс
        if is_new_row:
            checkbox_item = QTableWidgetItem()
            checkbox_item.setFlags(Qt.ItemIsUserCheckable | Qt.ItemIsEnabled)
            checkbox_item.setCheckState(Qt.Unchecked)
            self.table_widget.setItem(row_for_ip, 0, checkbox_item)

       # Ус# Установка IP адреса
        ip_item = QTableWidgetItem(ip)
        ip_item.setTextAlignment(Qt.AlignCenter)
        self.table_widget.setItem(row_for_ip, 1, ip_item)

    # Установка данных из info
        if 'model' in info_data:
            model_item = QTableWidgetItem(info_data['model'])
            model_item.setTextAlignment(Qt.AlignCenter)
            self.table_widget.setItem(row_for_ip, 3, model_item)

        if 'fw_version' in info_data:
            fw_version_item = QTableWidgetItem(info_data['fw_version'])
            fw_version_item.setTextAlignment(Qt.AlignCenter)
            self.table_widget.setItem(row_for_ip, 4, fw_version_item)

        if 'build_time' in info_data:
            build_time_item = QTableWidgetItem(info_data['build_time'])
            build_time_item.setTextAlignment(Qt.AlignCenter)
            self.table_widget.setItem(row_for_ip, 5, build_time_item)

        if 'platform' in info_data:
            platform_item = QTableWidgetItem(info_data['platform'])
            platform_item.setTextAlignment(Qt.AlignCenter)
            self.table_widget.setItem(row_for_ip, 6, platform_item)

        if 'install_type' in info_data:
            install_type_item = QTableWidgetItem(info_data['install_type'])
            install_type_item.setTextAlignment(Qt.AlignCenter)
            self.table_widget.setItem(row_for_ip, 7, install_type_item)
     
            
        
    def header_checkbox_state_changed(self, state):
        # Set the state of all checkboxes in the column
        for i in range(self.table.rowCount()):
            item = self.table.item(i, 0)
            if item is not None:
               item.setCheckState(state)
        
    
    @pyqtSlot(int)
    def scan_finished(self, result_count):
        QMessageBox.information(self, "Scan Finished", f"Сканирование завершено. Найдено устройств: {result_count}")

    @pyqtSlot(str)
    def show_error_message(self, message):
        self.timed_message.setText(message)
        self.timed_message.show_message(10000)  # Показать сообщение на 3 секунды
    
    #Устанавливаем главный чикбокс действия 
    def global_checkbox_state_changed(self, state):
        check_state = Qt.Checked if state == Qt.Checked else Qt.Unchecked
        for i in range(self.table_widget.rowCount()):
            checkbox_item = self.table_widget.item(i, 0)
            if checkbox_item:
                checkbox_item.setCheckState(check_state)

# Создание и запуск приложения
app = QApplication([])
window = MainWindow()
window.show()
app.exec_()