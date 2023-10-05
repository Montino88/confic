import sys
import webbrowser
from PyQt5.QtCore import pyqtSignal
from PyQt5.QtWidgets import (QApplication, QMainWindow, QDockWidget, QListWidget, 
                             QListWidgetItem, QTextEdit, QPushButton, QToolBar, 
                             QWidget, QLabel, QVBoxLayout, QAbstractItemView, QStackedWidget)
from PyQt5.QtGui import QIcon
from PyQt5.QtCore import Qt, QSize
# Импортируем ваши вкладки
from monitor_tab import MonitorTab
from scan_tab import ScanTab 
from table_tab import TableTab
from Config_tab import ConfigTab
from settings_tab import SettingsTab

# Класс для создания кликабельных виджетов
class ClickableWidget(QWidget):

    clicked = pyqtSignal()

    def mousePressEvent(self, event):
        super().mousePressEvent(event)
        self.clicked.emit()

# Класс для виджета с иконкой и текстом
class IconLabelWidget(ClickableWidget):
    def __init__(self, icon_path, text, link=None):
        super().__init__()
        self.link = link
       
        layout = QVBoxLayout()
        layout.setContentsMargins(10,10,10,10)

        icon_label = QLabel()
        icon_label.setPixmap(QIcon(icon_path).pixmap(24, 24))
        icon_label.setAlignment(Qt.AlignCenter)

        text_label = QLabel(text)
        text_label.setAlignment(Qt.AlignCenter)

        layout.addWidget(icon_label)
        layout.addWidget(text_label)

        self.setLayout(layout)
        self.clicked.connect(self.on_clicked)

    def on_clicked(self):
        if self.link:
            webbrowser.open(self.link)

# Основное окно приложения
class MainWindow(QMainWindow): 
    def __init__(self):
        super().__init__()

        # Создание вкладок
        self.scan_tab = ScanTab(self)
        self.monitor_tab = MonitorTab(self)
        self.table_tab = TableTab(self)
        self.config_tab = ConfigTab(self)
        self.settings_tab = SettingsTab(self)

        # Инициализация стека виджетов
        self.stack = QStackedWidget(self)
        self.stack.addWidget(self.scan_tab)
        self.stack.addWidget(self.monitor_tab)
        self.stack.addWidget(self.table_tab)
        self.stack.addWidget(self.config_tab)
        self.stack.addWidget(self.settings_tab)
        self.setCentralWidget(self.stack)

        # Словарь для соответствия между элементами меню и вкладками
        self.tab_dict = {
            0: self.scan_tab,
            1: self.monitor_tab,
            2: self.table_tab,
            3: self.config_tab,
            4: self.settings_tab
        }

        # Настройка стилей
        self.setStyleSheet("""
            QWidget {
                background-color: #FFFFFF;  /* Цвет фона основной */
                color: #000000;  /* Цвет текста всех виджетов */
            }
            QDockWidget {
                background: #0DDEF4;  /* Цвет фона DockWidget'ов */
            }
            QPushButton {
                background-color: #FFFFFF;  /* Цвет фона кнопок */
            }
            QPushButton:hover {
                background-color: #0C75F5;  /* Цвет фона кнопок при наведении курсора */
                color: #20B2AA;  /* Цвет текста кнопок при наведении курсора */
                border: 1px dotted #FFFFFF;
            }
        
            QListView::item:hover {
                background: #FFFFFF;  /* Цвет фона элементов списка при наведении курсора */
            }
            QListView::item:focus {
                border: none;
            }
            QScrollBar { 
                width: 0px;  /* Ширина полосы прокрутки */
            } 
        """)

        # Настройка списка меню слева
        self.list_widget = QListWidget()
        self.list_widget.setSelectionMode(QAbstractItemView.NoSelection)
        self.list_widget.setStyleSheet("background-color: #FFFFFF;")  # Установка цвета фона для списка меню
        base_path = "C:/Users/acer/Desktop/config/moniy/resources/"

        self.add_menu_item("Scan", base_path + "scan.png", ScanTab)
        self.add_menu_item("Monitor", base_path + "monitor.png", MonitorTab)
        self.add_menu_item("Table", base_path + "table.png", TableTab)
        self.add_menu_item("Config", base_path + "Config.png", ConfigTab)
        self.add_menu_item("Settings", base_path + "setting.png", SettingsTab)
        self.add_support_button("Support", base_path + "support.png")

        for _ in range(12):
            item = QListWidgetItem()
            item.setFlags(Qt.NoItemFlags)
            self.list_widget.addItem(item)

        # Настройка DockWidget
        self.dock_widget = QDockWidget(self)
        self.dock_widget.setWidget(self.list_widget)
        self.addDockWidget(Qt.LeftDockWidgetArea, self.dock_widget)
        self.dock_widget.setTitleBarWidget(QWidget())
        self.dock_widget.setFeatures(QDockWidget.NoDockWidgetFeatures)
        self.dock_widget.setFixedHeight(600)
        self.dock_widget.setFixedWidth(100)


        # Настройка кнопки переключения меню
        self.toggle_button = QPushButton()
        self.toggle_button.setIcon(QIcon("C:/Users/acer/Desktop/config/moniy/menu.png"))
        self.toggle_button.setIconSize(QSize(32, 32))
        self.toggle_button.clicked.connect(self.toggle_dock_widget)
        self.toggle_button.setFocusPolicy(Qt.NoFocus)
        self.toggle_button.setFixedSize(40, 40)

        self.toggle_button.setStyleSheet("""
            QPushButton {
                border: none;  // Убираем границы
                background-color: transparent;  // Делаем кнопку прозрачной
                padding: 0;  // Убираем отступы
                margin: 0;  // Убираем поля
            }
            QPushButton::hover {
                background-color: transparent;  // Убедитесь, что при наведении кнопка остается прозрачной
            } 
        """)

        # Настройка верхней панели инструментов
        toolbar = QToolBar()
        toolbar.setMovable(False)
        toolbar.addWidget(self.toggle_button)
        toolbar.setStyleSheet("background-color: #20B2AA;")  # Установка цвета фона для верхней панели инструментов
        self.addToolBar(Qt.TopToolBarArea, toolbar)

        self.resize(800, 600)
        
        # Инициализация текущей вкладки
        self.current_tab = None

         # слоты 
        self.scan_tab.send_to_monitoring_signal.connect(self.monitor_tab.receive_from_scan)
        self.scan_tab.scan_finished_signal.connect(self.forward_scan_finished)

    

        # Сигналы и слоты
        self.list_widget.itemClicked.connect(self.on_item_clicked)
        self.on_item_clicked(self.list_widget.item(0))  # По умолчанию открываем вкладку «Scan»

        self.stack.currentChanged.connect(self.switch_tab)

    def forward_scan_finished(self):
        self.monitor_tab.receive_scan_finished()

    def on_item_clicked(self, item):
        item_index = self.list_widget.row(item)
        self.stack.setCurrentIndex(item_index)
        self.switch_tab(item_index)

    def switch_tab(self, index):
        # Если была открыта какая-то вкладка, сохранить ее данные
        if self.current_tab is not None:
            self.current_tab.save_data()

        # Загрузить данные новой вкладки
        new_tab = self.stack.widget(index)
        new_tab.load_data()

        # Обновить текущую вкладку
        self.current_tab = new_tab

    def toggle_dock_widget(self):
        if self.dock_widget.width() > 70:  # Это примерное значение, меняйте по своему усмотрению
            self.dock_widget.setFixedWidth(70)  # Сохраняем только иконки
        else:
            self.dock_widget.setFixedWidth(110)  # Полная ширина меню

    def add_menu_item(self, text, icon_path, tab_class):
        item_widget = IconLabelWidget(icon_path, text)
        item = QListWidgetItem()
        item.setSizeHint(item_widget.sizeHint())
        self.list_widget.addItem(item)
        self.list_widget.setItemWidget(item, item_widget)

    def add_support_button(self, text, icon_path):
        button_widget = IconLabelWidget(icon_path, text, '')
        button = QListWidgetItem()
        button.setSizeHint(button_widget.sizeHint())
        self.list_widget.addItem(button)
        self.list_widget.setItemWidget(button, button_widget)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    main_window = MainWindow()
    main_window.show()
    sys.exit(app.exec_())