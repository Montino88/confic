import socket
import json
from PyQt5.QtCore import QThread, pyqtSignal
import concurrent.futures
import time
from PyQt5.QtWidgets import QMessageBox



def send_command(command, ip_address, port=4028):
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.connect((ip_address, port))
        sock.sendall(json.dumps(command).encode())
        data = sock.recv(4096)
        sock.close()
        data = data.replace(b'\x00', b'')
        
        data_str = data.decode()
        data_str = data_str.replace("}{", "}, {")  # Добавьте запятую между объектами без пробела

        return json.loads(data_str)
    except Exception as e:
        return None
    
class ScanThread(QThread):

    ip_range_scanned = pyqtSignal(int)  # новый сигнал
    finished = pyqtSignal(dict, int)  # сигнал, который будет отправлять данные при завершении потока
    miner_found = pyqtSignal(dict, int)  # новый сигнал, который будет отправляться каждый раз, когда найден новый майнер
    update_progress_signal = pyqtSignal(int)  # новый сигнал

    def __init__(self, ip_ranges):
        super().__init__()
        self.ip_ranges = ip_ranges

    def run(self):
        open_ports, total_miners = self.scan_network_and_update_info(self.ip_ranges)
        self.finished.emit(open_ports, total_miners)

    def scan_network_and_update_info(self, ip_ranges):
        command = {"command": "stats"}
        open_ports = {}
        total_miners = 0
        scanned_ranges = 0

        for ip_range in ip_ranges:
            with concurrent.futures.ThreadPoolExecutor(max_workers=100) as executor:
                future_to_ip = {executor.submit(send_command, command, ip): ip for ip in ip_range}
                for future in concurrent.futures.as_completed(future_to_ip):
                    ip = future_to_ip[future]
                    print(f"Scanning IP: {ip}")  # добавленная строка

                    try:
                        data = future.result()
                        data['IP'] = ip
                        open_ports[ip] = data
                        total_miners += 1
                    except Exception as exc:
                        pass

            scanned_ranges += 1
            self.ip_range_scanned.emit(scanned_ranges)

        return open_ports, total_miners
