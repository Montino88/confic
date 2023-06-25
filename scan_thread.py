import socket
import json
from PyQt5.QtCore import QThread, pyqtSignal
import concurrent.futures
import time


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
    ip_scanned = pyqtSignal(int)  # новый сигнал
    finished = pyqtSignal(dict, int)  # сигнал, который будет отправлять данные при завершении потока
    miner_found = pyqtSignal(dict, int)  # новый сигнал, который будет отправляться каждый раз, когда найден новый майнер


    def __init__(self, ip_range):
        super().__init__()
        self.ip_range = ip_range

    def run(self):
        open_ports, total_miners = self.scan_network_and_update_info(self.ip_range)
        self.finished.emit(open_ports, total_miners)

    def scan_network_and_update_info(self, ip_range):
        command = {"command": "stats"}
        open_ports = {}
        total_miners = 0
        scanned_ips = 0
        last_update_time = time.time()

        with concurrent.futures.ThreadPoolExecutor(max_workers=100) as executor:
            future_to_ip = {executor.submit(send_command, command, ip): ip for ip in ip_range}
            for future in concurrent.futures.as_completed(future_to_ip):
                ip = future_to_ip[future]
                try:
                    data = future.result()
                    data['IP'] = ip
                    open_ports[ip] = data
                    total_miners += 1
                    scanned_ips += 1
                    self.ip_scanned.emit(scanned_ips)
                    current_time = time.time()
                    if current_time - last_update_time >= 5:  # отправляем сигнал каждые 5 секунд
                        self.miner_found.emit(open_ports, total_miners)
                        last_update_time = current_time
                except Exception as exc:
                    pass

        return open_ports, total_miners