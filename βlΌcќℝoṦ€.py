import sys
import webbrowser
from PyQt5.QtCore import pyqtSignal, Qt, QSize

from PyQt5.QtWidgets import (QApplication, QMainWindow, QDockWidget, QListWidget,
                             QListWidgetItem, QTextEdit, QPushButton, QToolBar,
                             QWidget, QLabel, QVBoxLayout, QAbstractItemView, QStackedWidget, QSizePolicy)
from PyQt5.QtGui import QIcon
from scan_tab import ScanTab
from settings_tab import SettingsTab
from control_tab import ControlTab  # Убедитесь, что этот импорт присутствует

# Класс для создания кликабельных виджетов
class ClickableWidget(QWidget):
    clicked = pyqtSignal()

    def mousePressEvent(self, event):
        super().mousePressEvent(event)
        self.clicked.emit()

# Класс для виджета с иконкой и текстом
class IconLabelWidget(ClickableWidget):
    def __init__(self, icon_path, text=None, link=None):
        super().__init__()
        self.link = link

        layout = QVBoxLayout()
        layout.setContentsMargins(10, 10, 10, 10)

        icon_label = QLabel()
        icon_label.setPixmap(QIcon(icon_path).pixmap(24, 24))
        icon_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(icon_label)

        if text:
            text_label = QLabel(text)
            text_label.setAlignment(Qt.AlignCenter)
            layout.addWidget(text_label)

        self.setLayout(layout)
        self.clicked.connect(self.on_clicked)

    def on_clicked(self):
        if self.link:
            webbrowser.open(self.link)

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.scan_tab = ScanTab()
        self.settings_tab = SettingsTab(self)
        self.control_tab = ControlTab(self)  # Убедитесь, что экземпляр ControlTab создается

        self.central_widget = QStackedWidget()  # Создаем QStackedWidget
        self.setCentralWidget(self.central_widget)

        # Добавление вкладок в QStackedWidget
        self.central_widget.addWidget(self.scan_tab)
        self.central_widget.addWidget(self.settings_tab)
        self.central_widget.addWidget(self.control_tab)

        self.settings_dock = QDockWidget("Settings", self)
        self.settings_dock.setWidget(self.settings_tab)
        self.settings_dock.setAllowedAreas(Qt.RightDockWidgetArea)
        self.settings_dock.setTitleBarWidget(QWidget())
        self.addDockWidget(Qt.RightDockWidgetArea, self.settings_dock)

        self.settings_dock.hide()

        self.init_toolbar()

        self.resize(800, 600)

        self.scan_tab.scan_finished_signal.connect(self.forward_scan_finished)
        self.settings_tab.ip_range_saved.connect(self.scan_tab.on_ip_range_saved)
        # Подключение сигнала из SettingsTab к слоту в ScanTab
        self.settings_tab.credentials_updated.connect(self.scan_tab.update_credentials)
        # Подключаем сигналы и слоты
        self.settings_tab.credentials_updated.connect(self.on_credentials_updated)
        # Соединение сигнала и слота
        self.scan_tab.update_control_tab_signal.connect(self.control_tab.update_with_scan_data)



    def init_toolbar(self):
        toolbar = QToolBar("Main Toolbar")
        toolbar.setMovable(False)
        toolbar.setMinimumHeight(50)
        toolbar.setMaximumHeight(50)

        # Функция для добавления пространства между кнопками
        def add_spacer():
            spacer = QWidget()
            spacer.setFixedSize(10, 10)  # Задаем фиксированный размер прозрачного виджета
            toolbar.addWidget(spacer)

        logo_label = QLabel(self)
        logo_label.setPixmap(QIcon("C:/Users/acer/Desktop/config/moniy/resources/lodo2.png").pixmap(48, 48))
        toolbar.addWidget(logo_label)

        spacer = QWidget()
        spacer.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        toolbar.addWidget(spacer)

        self.toggle_scan_tab_button = QPushButton()
        icon_path_scan = "C:/Users/acer/Desktop/config/moniy/resources/scan.png"
        self.toggle_scan_tab_button.setIcon(QIcon(icon_path_scan))
        self.toggle_scan_tab_button.setIconSize(QSize(24, 24))
        self.toggle_scan_tab_button.clicked.connect(lambda: self.central_widget.setCurrentWidget(self.scan_tab))
        toolbar.addWidget(self.toggle_scan_tab_button)

        add_spacer()  # Добавляем пространство между кнопками

        self.toggle_control_tab_button = QPushButton()
        icon_path_control = "C:/Users/acer/Desktop/config/moniy/resources/Config.png"
        self.toggle_control_tab_button.setIcon(QIcon(icon_path_control))
        self.toggle_control_tab_button.setIconSize(QSize(24, 24))
        self.toggle_control_tab_button.clicked.connect(lambda: self.central_widget.setCurrentWidget(self.control_tab))
        toolbar.addWidget(self.toggle_control_tab_button)
        
        add_spacer()  # Добавляем пространство между кнопками

        self.toggle_settings_button = QPushButton()
        icon_path_settings = "C:/Users/acer/Desktop/config/moniy/resources/setting.png"
        self.toggle_settings_button.setIcon(QIcon(icon_path_settings))
        self.toggle_settings_button.setIconSize(QSize(24, 24))
        self.toggle_settings_button.clicked.connect(self.toggle_settings_dock)
        toolbar.addWidget(self.toggle_settings_button)

        toolbar.setStyleSheet("""
            QToolBar {
                background-color: #05B8CC;
            }
            QPushButton {
                background-color: #05B8CC;
                border: none;
            }
        """)
        self.addToolBar(Qt.TopToolBarArea, toolbar)

    def on_credentials_updated(self, credentials):
        # Этот слот будет получать данные учетных записей из SettingsTab
        self.control_tab.set_credentials(credentials)

    def toggle_settings_dock(self):
        self.settings_dock.setVisible(not self.settings_dock.isVisible())

    def forward_scan_finished(self):
        # Действия после завершения сканирования
        pass

    def load_data(self):
        self.data = 'Data for main'

    def save_data(self):
        print(f"Saving data: {self.data}")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    main_window = MainWindow()
    main_window.show()
    sys.exit(app.exec_())