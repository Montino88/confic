from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QPushButton, QTableWidget, 
                             QTableWidgetItem, QCheckBox, QHBoxLayout, QHeaderView)
from PyQt5.QtCore import Qt, pyqtSlot, QTimer, QThreadPool
import aiohttp  # Для асинхронных HTTP-запросов
import asyncio  # Для асинхронной работы
import re
import concurrent.futures
from PyQt5.QtCore import pyqtSignal
import webbrowser
from PyQt5.QtWidgets import QDialog, QVBoxLayout, QPushButton, QLabel, QLineEdit, QFileDialog, QMessageBox

class FirmwareUpdateDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Firmware Update")
        self.setFixedSize(400, 200)

        layout = QVBoxLayout(self)

        # Поле для выбора файла прошивки
        self.firmware_file_path = QLineEdit(self)
        layout.addWidget(QLabel("Firmware File:"))
        layout.addWidget(self.firmware_file_path)

        # Кнопка для выбора файла
        self.btn_select_firmware = QPushButton("Select Firmware File", self)
        self.btn_select_firmware.clicked.connect(self.select_firmware_file)
        layout.addWidget(self.btn_select_firmware)

        # Кнопка для запуска обновления прошивки
        self.btn_start_update = QPushButton("Start Update", self)
        self.btn_start_update.clicked.connect(self.accept)
        layout.addWidget(self.btn_start_update)

    def select_firmware_file(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Select Firmware File", "", "Firmware Files (*.bin);;All Files (*)")
        self.firmware_file_path.setText(file_path)

    def get_firmware_file(self):
        return self.firmware_file_path.text()





class ControlTab(QWidget):
    update_status_signal = pyqtSignal(str, str)  # Добавляем сигнал

    def __init__(self, parent=None):
        super().__init__(parent)
        self.credentials = {}  # Инициализация переменной для хранения учетных данных
        self.led_status = {}  # Словарь для хранения состояния LED

        # Основной вертикальный макет
        self.layout = QVBoxLayout(self)

        # Создание таблицы
        self.table = QTableWidget(self)
        self.table.setColumnCount(5)  # Установка количества столбцов
        self.table.setHorizontalHeaderLabels(["Select", "IP Address", "Model", "Status", "CompileTime"])
        self.table.setColumnWidth(0, 80)  # Ширина столбца под чекбокс
        self.table.setSortingEnabled(True)
        self.table.setStyleSheet("""
          
            QTableWidget::item {
        # Инициализация виджета для отображения таблицы
                background-color: #333333;
                color: #ffffff;
            }
            QTableWidget::item:selected {
                background-color: #333333;
                color: #ffffff;
            }
            QTableWidget::item:hover {
                background-color: #333333;
                color: #ffffff;
            }
            QCheckBox::indicator {
                width: 13px;
                height: 13px;
            }
            QCheckBox::indicator:unchecked {
                image: url(/path/to/your/unchecked/image);
            }
            QCheckBox::indicator:checked {
                image: url(/path/to/your/checked/image);
            }
            QTableWidget::item:selected {
                background-color: #333333;  /* Замените на желаемый цвет фона при выделении */
                color: #ffffff;
            }                     
        """)
       # Изменение цвета заголовка столбца
        header = self.table.horizontalHeader()

        header.setStyleSheet("""
            QHeaderView::section {
                background-color: #20B2AA ;
                color: #f0f0f0;
            }
        """)
       
       

        # Создание горизонтального макета для кнопок
        button_panel = QHBoxLayout()

        # Создание кнопок
        self.reboot_button = QPushButton("Ребут")
        self.search_miner_button = QPushButton("Поиск асика")
        self.update_firmware_button = QPushButton("Обновление прошивки ")
        self.change_of_pools_button = QPushButton("Смена пулов ")  # Исправлено здесь
        self.clone_button = QPushButton("Клонировка")
        
        
        # Создание и добавление главного чекбокса
        self.main_checkbox = QCheckBox("ВСЕ")
        self.main_checkbox.stateChanged.connect(self.main_checkbox_state_changed)
        button_panel.addWidget(self.main_checkbox)


        # Добавление кнопок в горизонтальный макет
        button_panel.addWidget(self.reboot_button)
        button_panel.addWidget(self.search_miner_button)
        button_panel.addWidget(self.update_firmware_button)
        button_panel.addWidget(self.change_of_pools_button)  
        button_panel.addWidget(self.clone_button)

        # Привязка кнопок к функциям выполнения команд
        self.reboot_button.clicked.connect(lambda: self.on_command_button_clicked('reboot'))
        self.search_miner_button.clicked.connect(lambda: self.on_command_button_clicked('search_miner'))
        self.update_firmware_button.clicked.connect(lambda: self.on_command_button_clicked('update_firmware'))
        self.change_of_pools_button.clicked.connect(lambda: self.on_command_button_clicked('change_pools'))
        self.clone_button.clicked.connect(lambda: self.on_command_button_clicked('clone'))

        
        # Добавление горизонтального макета кнопок в начало вертикального макета
        self.layout.addLayout(button_panel)

        # Добавляем таблицу в основной макет
        self.layout.addWidget(self.table)

        self.update_status_signal.connect(self.update_status)  # Подключаем сигнал к слоту
        self.update_firmware_button.clicked.connect(self.on_update_firmware_button_clicked)


        # Применение стилей к кнопкам
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
       
    def on_update_firmware_button_clicked(self):
        dialog = FirmwareUpdateDialog(self)
        if dialog.exec_() == QDialog.Accepted:
            firmware_path = dialog.get_firmware_file()
            if firmware_path:
                selected_models = self.get_selected_models()
                if selected_models:
                    # Вызываем функцию обновления прошивки для выбранных моделей
                    print(f"Selected firmware file: {firmware_path}")
                    print("Updating firmware for models:", selected_models)
                    # Пример: self.update_firmware_for_selected_models(firmware_path, selected_models)
                else:
                    QMessageBox.warning(self, "Warning", "No ASICs selected.")
            else:
                QMessageBox.warning(self, "Warning", "No firmware file selected.")

    def get_selected_models(self):
        selected_models = []
        for row in range(self.table.rowCount()):
            checkbox_widget = self.table.cellWidget(row, 0)
            if checkbox_widget is not None:
                checkbox = checkbox_widget.findChild(QCheckBox)
                if checkbox is not None and checkbox.isChecked():
                    ip = self.table.item(row, 1).text()
                    selected_models.append(ip)
        return selected_models

    def set_credentials(self, credentials):
        # Этот метод сохраняет учетные данные, полученные из SettingsTab
        self.credentials = credentials
        print(f"ControlTab получил учетные в ControlTab данные: {self.credentials}")  

    def main_checkbox_state_changed(self, state):
        # Изменение состояния всех чекбоксов в таблице
        for row in range(self.table.rowCount()):
            checkbox_widget = self.table.cellWidget(row, 0)
            if checkbox_widget is not None:
                checkbox = checkbox_widget.findChild(QCheckBox)
                if checkbox is not None:
                    checkbox.setChecked(state == Qt.Checked)

    def count_selected_models(self):
        selected_models_count = {}
        for row in range(self.table.rowCount()):
            checkbox_widget = self.table.cellWidget(row, 0)
            if checkbox_widget is not None:
                checkbox = checkbox_widget.findChild(QCheckBox)
                if checkbox is not None and checkbox.isChecked():
                    model = self.table.item(row, 2).text()  # Получаем модель из таблицы
                    selected_models_count[model] = selected_models_count.get(model, 0) + 1

        # Отображение выбранных моделей и их количества
        print("Выбранные модели и их количество:")
        for model, count in selected_models_count.items():
            print(f"{model} - {count}")                

    def add_device(self, ip, model, compile_time):
        # Определяем позицию новой строки
        row_position = self.table.rowCount()
        self.table.insertRow(row_position)

        # Добавляем чекбокс в первый столбец
        chk_box_widget = QWidget()
        chk_box_layout = QHBoxLayout(chk_box_widget)
        chk_box_layout.setAlignment(Qt.AlignCenter)
        chk_box = QCheckBox()
        chk_box_layout.addWidget(chk_box)
        self.table.setCellWidget(row_position, 0, chk_box_widget)

        # Создаем и добавляем IP адрес
        ip_item = QTableWidgetItem(ip)
        ip_item.setFlags(Qt.ItemIsEnabled)
        self.table.setItem(row_position, 1, ip_item)

        # Создаем и добавляем модель
        model_item = QTableWidgetItem(model)
        model_item.setFlags(Qt.ItemIsEnabled)
        self.table.setItem(row_position, 2, model_item)

        # Создаем и добавляем статус
        status_item = QTableWidgetItem("")
        status_item.setFlags(Qt.ItemIsEnabled)
        self.table.setItem(row_position, 3, status_item)
  
        # Создаем и добавляем время компиляции
        compile_time_item = QTableWidgetItem(compile_time)
        compile_time_item.setFlags(Qt.ItemIsEnabled)
        self.table.setItem(row_position, 4, compile_time_item)


    #переход по айпи 
    def open_web_interface(self, row, col):
        # Check if the clicked cell is the IP cell
        if col == 1:
            item = self.table.item(row, col)
            if item:
                ip = item.text()
                # Open the web interface
                webbrowser.open(f"http://{ip}")


    #обновлен е статуса LED 
    def update_status(self, ip, status_message):
        # Находим строку по IP и обновляем статус
        for row in range(self.table.rowCount()):
            if self.table.item(row, 1).text() == ip:
                status_item = self.table.item(row, 3)
                if not status_item:
                    status_item = QTableWidgetItem()
                    self.table.setItem(row, 3, status_item)
                if status_message == "LED off":  # Очищаем статус, если LED выключен
                    status_item.setText("")
                else:
                    status_item.setText(status_message)

   

    def update_status_with_clear(self, ip, message, delay):
        """
        Обновляет статус для указанного IP и очищает его после задержки.

        :param ip: IP адрес устройства
        :param message: Сообщение для отображения
        :param delay: Задержка в миллисекундах, после которой статус будет очищен
        """
        # Обновляем статус
        self.update_status_signal.emit(ip, message)

        # Устанавливаем таймер для очистки статуса через задержку
        QTimer.singleShot(delay, lambda: self.clear_status(ip))

    def clear_status(self, ip):
        """
        Очищает статус для указанного IP.

        :param ip: IP адрес устройства
        """
        # Находим строку по IP и очищаем статус
        for row in range(self.table.rowCount()):
            if self.table.item(row, 1).text() == ip:
                status_item = self.table.item(row, 3)
                if status_item:
                    status_item.setText("")
  
       #очистка таблицы      
    def clear_table(self):
        self.table.clearContents()
        self.table.setRowCount(0)

     #поступление данных 
    @pyqtSlot(list)
    def update_with_scan_data(self, data_list):
        self.clear_table()  # Очистка таблицы перед добавлением новых данных
        for ip, model, compile_time in data_list:
            self.add_device(ip, model, compile_time)

        
    async def execute_command(self, command, additional_data=None):
        print(f"Начало выполнения команды: {command}")
        selected_rows = self.get_selected_rows()
        print(f"Выбранные строки: {selected_rows}")
        tasks = []

        for row in selected_rows:
            ip = row['ip']
            model = row['model']
            print(f"Обработка IP: {ip}, модель: {model}")
            # Определение ключа для учетных данных на основе модели
            credentials_key = self.determine_credentials_key(model)
            # Получение соответствующих учетных данных
            credentials = self.credentials.get(credentials_key, {})

            manager_class = self.determine_asic_manager(model)
            if manager_class:
                current_status = self.led_status.get(ip, False)
                manager = manager_class(ip, credentials, current_status)

                if command == 'search_miner':
                    tasks.append(manager.toggle_search_asics())
                    print(f"Добавлена задача переключения режима поиска для {ip}")
                elif command == 'reboot':
                    # Создаем задачу для перезагрузки, но не выполняем ее сразу
                    task = manager.reboot()
                    tasks.append(task)
                elif command == 'update_firmware':
                    tasks.append(manager.update_firmware())
                elif command == 'change_pools':
                    tasks.append(manager.change_pools(additional_data))
                elif command == 'clone':
                    tasks.append(manager.clone())
                # ... другие команды ...
            else:
                print(f"Менеджер для модели {model} не найден.")

       # Асинхронное выполнение всех задач
        results = await asyncio.gather(*tasks)
        print(f"Результаты выполнения команды: {results}")

        for result in results:
            if result:
                ip, status_message = result
                self.led_status[ip] = 'on' in status_message
        # Обновление статуса с последующей очисткой через 5 секунд (5000 мс)
                self.update_status_with_clear(ip, status_message, 5000)

        return results
    
    def determine_credentials_key(self, model):
        """
        Возвращает ключ для словаря учетных данных на основе модели устройства.
        """
        if "Vnish" in model:
            return "VnishOS"
        elif "Avalonminer" in model:
            return "Avalonminer"
        elif "Whatsminer" in model:
            return "Whatsminer"
        else:
            return "Default"  # ключ для учетных данных по умолчанию, если модель не определена



    def on_command_button_clicked(self, command):
        print(f"Кнопка '{command}' нажата. Запуск выполнения команды.")
        # Запускаем асинхронную задачу в отдельном потоке
        pool = QThreadPool.globalInstance()
        loop = asyncio.new_event_loop()
        with concurrent.futures.ThreadPoolExecutor() as executor:
            future = executor.submit(loop.run_until_complete, self.execute_command(command))
            result = future.result()  # Ждем завершения задачи
            print(f"Результат выполнения команды '{command}': {result}")

            # Обработка результата

    # Обновленное регулярное выражение,
    def determine_asic_manager(self, model):
        pattern = re.compile(r'Antminer.*19.*Vnish', re.IGNORECASE)
        if pattern.search(model):
            return Antminer19VnishAsicManager
        # Добавьте другие условия для разных моделей
        return None

   #сбор данных с таблицы 
    def get_selected_rows(self):
        selected_rows = []
        for row in range(self.table.rowCount()):
            checkbox_widget = self.table.cellWidget(row, 0)
            if checkbox_widget is not None:
                checkbox = checkbox_widget.findChild(QCheckBox)
                if checkbox is not None and checkbox.isChecked():
                    ip = self.table.item(row, 1).text()
                    model = self.table.item(row, 2).text()
                    compile_time = self.table.item(row, 4).text()
                    selected_rows.append({'ip': ip, 'model': model, 'compile_time': compile_time})
        return selected_rows
    
    # Функция load_data: Отвечает за ... (детальное описание)
    def load_data(self):
        self.data = 'Data for 777'
    # Функция save_data: Отвечает за ... (детальное описание)
    def save_data(self):
        print(f"Saving data: {self.data}")     

class BaseAsicManager:
    def __init__(self, ip, credentials):
        self.ip = ip
        self.credentials = credentials

# Пример для Antminer19VnishAsicManager
class Antminer19VnishAsicManager(BaseAsicManager):
    def __init__(self, ip, credentials, current_status):
        super().__init__(ip, credentials)
        # Используйте параметр current_status, чтобы установить начальное состояние режима поиска
        self.search_mode = current_status
        print(f"Создан экземпляр Antminer19VnishAsicManager для IP: {ip}, с учетными данными: {credentials}")




    async def unlock_miner(self, password):
        """
        Асинхронная функция для разблокировки майнера и получения токена.
        """
        url = f'http://{self.ip}/api/v1/unlock'
        data = {"pw": password}

        async with aiohttp.ClientSession() as session:
            try:
                async with session.post(url, json=data) as response:
                    if response.status == 200:
                        token = await response.json()
                        return token.get('token')
                    else:
                        return None
            except Exception as e:
                return None

    async def reboot(self):
        """
        Асинхронная функция для перезагрузки майнера.
        """
        password = self.credentials.get('password', '')  # Получаем пароль
        if not password:
            return (self.ip, "Password error")

        # Получение токена с использованием пароля
        token = await self.unlock_miner(password)
        if not token:
            return (self.ip, "Password error")

        # Отправка команды перезагрузки с токеном
        reboot_url = f'http://{self.ip}/api/v1/system/reboot'
        headers = {"Authorization": f"Bearer {token}"}

        async with aiohttp.ClientSession() as session:
            try:
                async with session.post(reboot_url, headers=headers) as response:
                    if response.status == 200:
                        return (self.ip, "Reboot")
                    else:
                        return (self.ip, "Error: " + str(response.status))
            except Exception as e:
                return (self.ip, "Error: " + str(e))

    async def change_pools(self, new_pool_data):
        # Асинхронная логика для смены пулов на VnishOS асике
        pass
    
    async def unlock_miner(self, password):
        """Асинхронно разблокирует майнер и получает токен."""
        url = f'http://{self.ip}/api/v1/unlock'
        data = {"pw": password}
        async with aiohttp.ClientSession() as session:
            try:
                async with session.post(url, json=data) as response:
                    if response.status == 200:
                        token = await response.json()
                        return token.get('token')
                    else:
                        return None
            except Exception as e:
                return None

    async def update_firmware(self, firmware_path, keep_settings):
        """Асинхронно обновляет прошивку майнера."""
        token = await self.unlock_miner(self.credentials.get('password', ''))
        if token:
            url = f'http://{self.ip}/api/v1/firmware/update'
            files = {'file': open(firmware_path, 'rb')}
            params = {'keep_settings': 'true' if keep_settings else 'false'}
            headers = {'Authorization': f'Bearer {token}'}
            async with aiohttp.ClientSession() as session:
                try:
                    async with session.post(url, data=files, params=params, headers=headers) as response:
                        if response.status == 200:
                            return "Firmware update initiated successfully."
                        else:
                            return "Error: " + str(response.status)
                except Exception as e:
                    return "Error: " + str(e)
        else:
            return "Failed to obtain token for firmware update."

    async def toggle_search_asics(self):
        print(f"Переключение режима поиска ASIC {self.ip}. Текущий режим: {'on' if self.search_mode else 'off'}")
        self.search_mode = not self.search_mode
        state = 'on' if self.search_mode else 'off'

        url = f'http://{self.ip}/api/v1/find-miner'
        data = {'state': state}

        async with aiohttp.ClientSession() as session:
            try:
                async with session.post(url, json=data) as response:
                    if response.status == 200:
                        return (self.ip, "LED on" if state == 'on' else "LED off")
                    else:
                        return (self.ip, f"Error: {response.status}")
            except aiohttp.ClientError as e:
                return (self.ip, f"Error: {e}")
            

class AvalonminerAsicManager(BaseAsicManager):
    async def reboot(self):
        # Здесь будет асинхронная логика для перезагрузки Avalonminer асика
        pass

    
    async def search_asics(self):
        # Асинхронная логика для поиска асиков на VnishOS
        pass  