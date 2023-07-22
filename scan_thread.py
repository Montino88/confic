import socket
import json
from PyQt5.QtCore import QThread, pyqtSignal
import concurrent.futures
import time
from json import JSONDecodeError


def send_command(command, ip_address, port=4028, retries=3, delay=2):
    for _ in range(retries):
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(2)  # Увеличиваем таймаут обратно до 2 секунд
        try:
            sock.connect((ip_address, port))
            sock.sendall(json.dumps(command).encode())
            data = sock.recv(4096)
            data = data.replace(b'\x00', b'')
            data_str = data.decode()
            data_str = data_str.replace("}{", "}, {")
            return json.loads(data_str)
        except socket.timeout as e:
            if _ < retries - 1:  # если это не последняя попытка, ждем и пробуем снова
                time.sleep(delay)
                continue
            return {'error': f"Error with IP {ip_address} and data {data_str if 'data_str' in locals() else 'N/A'}: {str(e)}"}
        except (ConnectionRefusedError, OSError):  # Ошибки подключения
            return {'error': f"Connection refused for IP {ip_address}"}
        except JSONDecodeError as e:
            return {'error': f"Error with IP {ip_address} and data {data_str if 'data_str' in locals() else 'N/A'}: {str(e)}"}
        except Exception as e:
            return {'error': f"Error for IP {ip_address}: {str(e)}"}
        finally:
            sock.close()
    return {'error': f"Error with IP {ip_address}: Max retries reached"}


class ScanThread(QThread):
    ip_scanned = pyqtSignal(int)  # new signal
    finished = pyqtSignal(dict, int)  # signal that will be emitted when the thread finishes
    miner_found = pyqtSignal(dict, int)  # new signal that will be emitted each time a new miner is found

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
  
        with concurrent.futures.ThreadPoolExecutor(max_workers=50) as executor:  # Уменьшаем количество рабочих потоков
            future_to_ip = {executor.submit(send_command, command, ip): ip for ip in ip_range}
            for future in concurrent.futures.as_completed(future_to_ip):
                ip = future_to_ip[future]
                data = future.result()
                if 'error' not in data:
                    data['IP'] = ip
                    open_ports[ip] = data
                    total_miners += 1
                else:
                    print(data['error'])
                scanned_ips += 1
                self.ip_scanned.emit(scanned_ips)

        return open_ports, total_miners