from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel, QHBoxLayout, QSizePolicy
from PyQt5.QtGui import QFont, QPainter, QPen, QBrush, QColor
from PyQt5.QtCore import Qt, QTimer, QSize
from matplotlib.figure import Figure
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from datetime import datetime, timedelta
from PyQt5.QtCore import pyqtSlot
from matplotlib.dates import DateFormatter
from matplotlib.ticker import AutoMinorLocator
import matplotlib.pyplot as plt
from PyQt5.QtWidgets import QToolTip
from matplotlib.widgets import Cursor
from PyQt5.QtCore import QPoint

class RoundProgressBar(QWidget):
    """Виджет круглого прогресс-бара."""
    def __init__(self, parent=None):
        super(RoundProgressBar, self).__init__(parent)
        self._value = 0
        self._max_value = 100
        self.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)

    def paintEvent(self, event):
        """Отрисовка прогресс-бара."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        # Рисуем внешний круг
        pen = QPen(QColor("#20FF1F"))
        pen.setWidth(10)
        painter.setPen(pen)
        painter.drawEllipse(5, 5, self.width() - 10, self.height() - 10)

        # Рисуем дугу прогресса
        arc_length = int(360 * self._value / self._max_value)
        painter.drawArc(5, 5, self.width() - 10, self.height() - 10, 90 * 16, -arc_length * 16)

        # Рисуем текст внутри круга
        painter.setPen(QColor("#20FF1F"))
        painter.setFont(QFont("Arial", 18))
        painter.drawText(self.rect(), Qt.AlignCenter, str(self._value))

    def sizeHint(self):
        """Подсказка размера для правильного отображения виджета."""
        return QSize(100,100)

    def setValue(self, value):
        """Установить значение прогресс-бара."""
        self._value = value
        self.update()

    def setRange(self, min_value, max_value):
        """Установить диапазон прогресс-бара."""
        self._max_value = max_value


class MonitorTab(QWidget):
    """Вкладка для мониторинга данных."""

    def __init__(self, scan_tab_reference, monitoring_interval_minutes=60, parent=None):
        super(MonitorTab, self).__init__(parent)

        # Ссылка на ScanTab
        self.scan_tab_reference = scan_tab_reference

        # Установка стиля для QToolTip
        QToolTip.setFont(QFont('Arial', 10))

        # Интервал мониторинга в миллисекундах (по умолчанию 60 минут)
        self.monitoring_interval = monitoring_interval_minutes * 60 * 1000

        # Список для хранения данных хешрейта за последние 24 часа
        self.hashrate_data = [0] * (24 * (60 // monitoring_interval_minutes))

        # Таймер для периодического обновления
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_monitoring_state)

        # Создание макета
        layout = QVBoxLayout()

        # Создание панели информации
        card_widget = QWidget()
        card_layout = QHBoxLayout()
        card_widget.setLayout(card_layout)
        card_widget.setFixedSize(400, 130)
        card_widget.setStyleSheet("background-color: #33333 ")

        # Добавляем круглый прогресс-бар
        self.progress_bar = RoundProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(100)  # Пример значения устройств
        card_layout.addWidget(self.progress_bar)

        # Добавляем метку хешрейта
        self.hashrate_label = QLabel("Hashrate: 0 GH/s")
        font = QFont()
        font.setPointSize(16)
        self.hashrate_label.setFont(font)
        self.hashrate_label.setStyleSheet("color: white;")
        card_layout.addWidget(self.hashrate_label)

        layout.addWidget(card_widget)

        # Создаем график хешрейта
        figure = Figure(figsize=(5, 3), dpi=100)
        figure.patch.set_facecolor('#3333')
        self.canvas = FigureCanvas(figure)
        self.hashrate_plot = figure.add_subplot(111)
        layout.addWidget(self.canvas)

        self.setLayout(layout)

    # Обработчик движения мыши для отображения подсказок
    def on_mouse_move(self, event):
        x, y = event.xdata, event.ydata
        if x is not None and y is not None:
            global_x, global_y = self.canvas.mapToGlobal(self.canvas.pos())
            QToolTip.showText(QPoint(global_x + event.x, global_y + event.y), f"TH: {y}")

    def receive_monitoring_data(self, data):
  #  """Обработка полученных данных мониторинга."""
        total_hashrate_ghs = 0
        for ip, miner_data in data.items():
            if 'estats' in miner_data:
                #hashrate_ghs_5s = miner_data['stats'][1].get('GHS 5s', 0)  # Преобразование в число, если ключ отсутствует, используется 0
              #  total_hashrate_ghs += float(hashrate_ghs_5s)
          #  else:
                print(f"Ключ 'estats' отсутствует для IP {ip}. Данные: {miner_data}")


                # Прибавляем нужное значение к total_hashrate_ghs
          #  total_hashrate_ghs += float(hashrate_ghs_5s)  # Преобразование в число
                # Если нужно прибавить и 'GHSmm', то можно добавить следующую строку:
        #total_hashrate_ghs += float(hashrate_ghs_mm)

            total_hashrate_ths = total_hashrate_ghs / 1000  # Конвертация в терахеши
            

            # Если значение превышает 1000 терахешей, конвертируем в петахеши
            if total_hashrate_ths >= 1000:
                total_hashrate_phs = total_hashrate_ths / 1000
                self.hashrate_label.setText(f"Hashrate: {total_hashrate_phs} PH/s")
                self.update_hashrate_plot(self.hashrate_data, unit="PH/s")
            else:
                self.hashrate_label.setText(f"Hashrate: {total_hashrate_ths} TH/s")
                self.update_hashrate_plot(self.hashrate_data, unit="TH/s")

            # Обновление количества устройств
            device_count = len(data)

            # Обновление прогресс-бара с новым количеством устройств
            self.progress_bar.setValue(device_count)  # Обновление значения прогресс-бара
  
            # Обновление данных хешрейта
            self.hashrate_data.pop(0)
            self.hashrate_data.append(total_hashrate_ths)

            # Обновление графика хешрейта
            self.update_hashrate_plot(self.hashrate_data)

    def start_monitor(self):
        """Запуск мониторинга."""
        self.timer.start(60000)

    def stop_monitor(self):
        """Остановка мониторинга."""
        self.timer.stop()        
    
    
    def update_monitoring_state(self):
        """Обновление состояния мониторинга."""
        # Вызов start_scan_and_get_data для обновления таблицы
        self.scan_tab_reference.start_scan_and_get_data()
    
    def on_plot_hover(self, event):
        xdata, ydata = event.xdata, event.ydata
        if xdata is not None and ydata is not None:
            print(f"Hover at x: {xdata}, y: {ydata}")  # Отладочное сообщение
            global_point = self.canvas.mapToGlobal(QPoint(event.x, event.y))
            QToolTip.showText(global_point, f"TH: {ydata:.2f}")

    def update_hashrate_plot(self, y_data, unit="TH/s"):
        x_data = [datetime.now() + timedelta(minutes=10 * i) for i in range(len(y_data))]
        self.hashrate_plot.clear()

        # Вычисляем максимальное значение для оси Y и проверяем на ноль
        y_max = max(y_data) * 1.25  # Устанавливаем на 20% выше максимального значения
        y_max = max(y_max, 1)  # Проверка на ноль

        # Определяем цвет в зависимости от единицы измерения
        if unit == "PH/s":
            plt.yticks(range(0, 51, 1))  # Шаг 1 для петахешей
            color_map = plt.get_cmap("coolwarm")
        else:
            plt.yticks(range(0, 1001, 50))  # Шаг 50 для терахешей
            color_map = plt.get_cmap("viridis")

        # Рисуем линию с градиентом
        norm_y_data = [y / y_max for y in y_data]
        for i in range(1, len(x_data)):
            self.hashrate_plot.plot(x_data[i-1:i+1], y_data[i-1:i+1], color=color_map(norm_y_data[i]))

        # Добавляем заполнение под графиком (опционально)
        self.hashrate_plot.fill_between(x_data, y_data, color=color_map(0.5), alpha=0.3)

        # Настройка графика
        self.hashrate_plot.tick_params(axis='y', labelsize=12)
        self.hashrate_plot.set_facecolor('#3333')
        self.hashrate_plot.set_xlabel("Время")
        self.hashrate_plot.yaxis.set_minor_locator(AutoMinorLocator())
        self.hashrate_plot.set_ylabel(f"Hashrate ({unit})")
        self.hashrate_plot.set_xlim(x_data[0], x_data[-1])
        self.hashrate_plot.set_ylim(0, y_max)  # Установка максимального значения оси Y

        # Подключение события
        self.canvas.mpl_connect('motion_notify_event', self.on_plot_hover)

        # Обновление холста
        self.canvas.draw()

    def load_data(self):
        self.data = 'Data for MonitorTab'

    def save_data(self):
        print(f"Saving data: {self.data}")       