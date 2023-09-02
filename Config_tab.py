from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel


class ConfigTab(QWidget):
    def __init__(self, parent=None):
        super(ConfigTab , self).__init__(parent)
        layout = QVBoxLayout()

        label = QLabel("Содержимое вкладки 'Configuration")
        layout.addWidget(label)

        self.setLayout(layout)
