import sys
import webbrowser
from PyQt5.QtCore import pyqtSignal
from PyQt5.QtWidgets import QApplication, QMainWindow, QDockWidget, QListWidget, QListWidgetItem, QTextEdit, QAction, QPushButton, QToolBar, QWidget, QLabel, QVBoxLayout, QSizePolicy, QAbstractItemView, QStackedWidget
from PyQt5.QtGui import QIcon
from PyQt5.QtCore import Qt, QSize
from monitor_tab import MonitorTab
from scan_tab import ScanTab
from table_tab import TableTab
from Config_tab import ConfigTab
from settings_tab import SettingsTab
from PyQt5.QtCore import QTimer


class ClickableWidget(QWidget):
    clicked = pyqtSignal()

    def mousePressEvent(self, event):
        super().mousePressEvent(event)
        self.clicked.emit()


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

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        #  все виджеты во время инициализации
        self.scan_tab = ScanTab(self)
        self.monitor_tab = MonitorTab(self)
        self.table_tab = TableTab(self)
        self.config_tab = ConfigTab(self)
        self.settings_tab = SettingsTab(self)
        
        # Сопоставление меню и виджетов
        self.tab_dict = {
            0: self.scan_tab,
            1: self.monitor_tab,
            2: self.table_tab,
            3: self.config_tab,
            4: self.settings_tab
        }

        # Добавление виджетов в стек
        self.stack = QStackedWidget(self)
        self.stack.addWidget(self.scan_tab)
        self.stack.addWidget(self.monitor_tab)
        self.stack.addWidget(self.table_tab)
        self.stack.addWidget(self.config_tab)
        self.stack.addWidget(self.settings_tab)
        
        self.setCentralWidget(self.stack)

        self.setStyleSheet("""
            QWidget {
                background-color: #262F34;  /* Цвет фона всех виджетов */
                color: white;  /* Цвет текста всех виджетов */
            }
            QToolBar {
                background-color: #262F34;  /* Цвет фона панели инструментов */
            }
            QDockWidget {
                background: #4671D5;  /* Цвет фона DockWidget'ов */
            }
            QPushButton {
                background-color: #262F34;  /* Цвет фона кнопок */
            }
            QPushButton:hover {
                background-color: #262F34;  /* Цвет фона кнопок при наведении курсора */
                color: #375E97;  /* Цвет текста кнопок при наведении курсора */
                border: 1px dotted #375E97;  /* Добавляем пунктирную рамку при наведении. Измените цвет (#262F34) на желаемый */
            }
            QPushButton:pressed, QPushButton:focus {
                background-color: #262F34;  /* Цвет фона кнопок при нажатии */
                color: #4671D5;  /* Цвет текста кнопок при нажатии */
                outline: none;  /* Убираем пунктирную рамку при фокусе */
            }
            QListView::item:hover {
                background: #262F34;  /* Цвет фона элементов списка при наведении курсора */
            }
            QListView::item:focus {
                border: none;  /* Убираем рамку у элементов списка при фокусе */
            }
            QScrollBar { 
                width: 0px;  /* Ширина полосы прокрутки */
            } 
        """)   



        self.setWindowTitle("vnish.Tools")

        self.list_widget = QListWidget()
        self.list_widget.setSelectionMode(QAbstractItemView.NoSelection)
        self.text_edit = QTextEdit()

        

        self.add_menu_item("Scan", "C:/Users/acer/Desktop/config/moniy/scan.png", ScanTab)
        self.add_menu_item("Monitor", "C:/Users/acer/Desktop/config/moniy/monitor.png", MonitorTab)
        self.add_menu_item("Table", "C:/Users/acer/Desktop/config/moniy/table.png", TableTab)
        self.add_menu_item("Config", "C:/Users/acer/Desktop/config/moniy/Config.png", ConfigTab)
        self.add_menu_item("Settings", "C:/Users/acer/Desktop/config/moniy/setting.png", SettingsTab)

        self.add_support_button("Support", "C:/Users/acer/Desktop/config/moniy/support.png")

        for _ in range(12):
            item = QListWidgetItem()
            item.setFlags(Qt.NoItemFlags)
            self.list_widget.addItem(item)

       

        self.dock_widget = QDockWidget(self)
        self.dock_widget.setWidget(self.list_widget)
        self.addDockWidget(Qt.LeftDockWidgetArea, self.dock_widget)

        self.dock_widget.setTitleBarWidget(QWidget())
        self.dock_widget.setFeatures(QDockWidget.NoDockWidgetFeatures)
        self.dock_widget.setFixedSize(120, 600)

        self.toggle_button = QPushButton()
        self.toggle_button.setIcon(QIcon("C:/Users/acer/Desktop/config/moniy/menu.png"))  
        self.toggle_button.setIconSize(QSize(32, 32))  
        self.toggle_button.clicked.connect(self.toggle_dock_widget)
        self.toggle_button.setFocusPolicy(Qt.NoFocus)
        self.toggle_button.setFixedSize(40, 40)
        self.toggle_button.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)

        toolbar = QToolBar()
        toolbar.addWidget(self.toggle_button)
        self.addToolBar(Qt.TopToolBarArea, toolbar)

        self.setCentralWidget(self.text_edit)

        self.resize(800, 600)

        self.list_widget.itemClicked.connect(self.on_item_clicked)
        self.on_item_clicked(self.list_widget.item(0))  #Открытие  по дефолту «scan» при запуске

    def on_item_clicked(self, item):
        item_index = self.list_widget.row(item)
        self.stack.setCurrentIndex(item_index)    

    def toggle_dock_widget(self):
        self.dock_widget.setVisible(not self.dock_widget.isVisible())

    def add_menu_item(self, text, icon_path, tab_class):
        item_widget = IconLabelWidget(icon_path, text)
        item = QListWidgetItem()
        item.setSizeHint(item_widget.sizeHint())
        self.list_widget.addItem(item)
        self.list_widget.setItemWidget(item, item_widget)

        item_index = self.list_widget.row(item)
        self.tab_dict[item_index] = tab_class

    def on_item_clicked(self, item):
        item_index = self.list_widget.row(item)
        tab_class = self.tab_dict.get(item_index)
        if tab_class:
            tab = tab_class(self)
            self.setCentralWidget(tab)

    def add_support_button(self, text, icon_path):
        button_widget = IconLabelWidget(icon_path, text, 'https://t.me/Vnish_Antminer_Firmware')
        button = QListWidgetItem()
        button.setSizeHint(button_widget.sizeHint())
        self.list_widget.addItem(button)
        self.list_widget.setItemWidget(button, button_widget)


if __name__ == "__main__":
    app = QApplication(sys.argv)

    main_window = MainWindow()
    main_window.show()

    sys.exit(app.exec_())
