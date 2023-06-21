from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel, QLineEdit, QPushButton, QSizePolicy, QHBoxLayout, QSpacerItem, QDialog, QTableWidget, QTableWidgetItem
from PyQt5.QtCore import Qt, QTimer

class CustomDialog(QDialog):
    def __init__(self, parent=None):
        super(CustomDialog, self).__init__(parent)
        self.setWindowTitle("Settings")  # Set the window title here

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


class SettingsTab(QWidget):
    def __init__(self, parent=None):
        super(SettingsTab, self).__init__(parent)

        layout = QVBoxLayout()

        ip_layout = QHBoxLayout() 

        label = QLabel("Enter IP (e.g.,192.168.0.1 ): ")
        self.ip_input = QLineEdit()  
        self.ip_input.setFixedWidth(200) 

        ip_layout.addWidget(label)
        ip_layout.addWidget(self.ip_input)

        # Buttons to add and remove IPs from the list
        self.add_button = QPushButton("+")
        self.add_button.setFixedWidth(20)
        self.remove_button = QPushButton("-")
        self.remove_button.setFixedWidth(20)

        # Connect buttons to functions
        self.add_button.clicked.connect(self.add_ip)
        self.remove_button.clicked.connect(self.remove_ip)

        # Add buttons to the layout
        ip_layout.addWidget(self.add_button)
        ip_layout.addWidget(self.remove_button)

        layout.addLayout(ip_layout)

        # Table to display added IPs
        self.ip_table = QTableWidget(0, 1)
        layout.addWidget(self.ip_table)

        save_button = QPushButton("Save")
        save_button.clicked.connect(self.save_ip)
        save_button.setFixedSize(150, 40)

        button_layout = QHBoxLayout()
        button_layout.addStretch(1)  
        button_layout.addWidget(save_button)
        button_layout.addStretch(1)

        layout.addLayout(button_layout)

        self.setLayout(layout)

    def save_ip(self):
        ip = self.ip_input.text()

        # Write IP address to file
        with open('ip.txt', 'w') as f:
            f.write(ip)

        # Show confirmation message
        dialog = CustomDialog(self)
        dialog.exec_()

    def add_ip(self):
        ip = self.ip_input.text()
        
        if ip:
            # Add new row in the table with IP
            row = self.ip_table.rowCount()
            self.ip_table.insertRow(row)
            self.ip_table.setItem(row, 0, QTableWidgetItem(ip))

    def remove_ip(self):
        # Get index of selected row
        row = self.ip_table.currentRow()

        if row != -1: # if there is a selected row
                        self.ip_table.removeRow(row)

