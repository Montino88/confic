from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel


class MonitorTab(QWidget):
    def __init__(self, parent=None):
        super(MonitorTab, self).__init__(parent)
        layout = QVBoxLayout()

        label = QLabel("Содержимое вкладки 'Монитор'")
        layout.addWidget(label)

        self.setLayout(layout)
