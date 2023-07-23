import socket
import json
from PyQt5.QtCore import QThread, pyqtSignal
import concurrent.futures
import time
from json import JSONDecodeError

import asyncio
from pyasic.network import MinerNetwork

def send_command(command, ip_address, port=4028, retries=3, delay=2):
    for _ in range(retries):
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(1)
        try:
            sock.connect((ip_address, port))
            sock.sendall(json.dumps(command).encode())
            data = sock.recv(4096)
            data = data.replace(b'\x00', b'')
            data_str = data.decode()
            data_str = data_str.replace("}{", "}, {")
            print(f"Response for IP {ip_address}: {data_str}")  # Добавлен вывод ответа

            return json.loads(data_str)
        except socket.timeout as e:
            print(f"Socket timeout for IP {ip_address}")  # Добавлен вывод ошибки
            if _ < retries - 1:
                time.sleep(delay)
                continue
            return {'error': f"Error with IP {ip_address} and data {data_str if 'data_str' in locals() else 'N/A'}: {str(e)}"}
        except (ConnectionRefusedError, OSError):
            print(f"Connection refused for IP {ip_address}")  # Добавлен вывод ошибки
            return {'error': f"Connection refused for IP {ip_address}"}
        except JSONDecodeError as e:
            return {'error': f"Error with IP {ip_address} and data {data_str if 'data_str' in locals() else 'N/A'}: {str(e)}"}
        except Exception as e:
            return {'error': f"Error for IP {ip_address}: {str(e)}"}
        finally:
            sock.close()
    return {'error': f"Error with IP {ip_address}: Max retries reached"}

class UnknownMiner:
    def __init__(self):
        self.type = "Unknown"
        


class ScanThread(QThread):
    ip_scanned = pyqtSignal(int)
    finished = pyqtSignal(dict, int)
    miner_found = pyqtSignal(dict, int)

    def __init__(self, ip_range):
        super().__init__()
        self.ip_range = ip_range

    async def get_miner_list(self, ip):
        print(f"Initiating scan for IP: {ip}")  # Добавлен вывод
        network = MinerNetwork(ip)
        miners = await network.scan_network_for_miners()
        print(f"Found miners for IP {ip}: {miners}")  # Добавлен вывод
        return miners

    def run(self):
        print(f"Scanning IP range: {self.ip_range}")  # Добавлен вывод диапазона IP-адресов
    
        all_miners = []
        for ip in self.ip_range:
            miners = asyncio.run(self.get_miner_list(ip))
            print(f"List of miners from get_miner_list for IP {ip}: {miners}")  # Добавлен вывод
            all_miners.extend(miners)

        # Filter out 'Unknown' devices
        valid_miners = [miner for miner in all_miners if miner.model != "Unknown"]
        print(f"Valid miners: {valid_miners}")  # Добавлен вывод

        open_ports = {miner.ip: {} for miner in valid_miners}
        command = {"command": "stats"}
        for ip in open_ports.keys():
            response = send_command(command, ip)
            open_ports[ip] = response
 
        self.finished.emit(open_ports, len(open_ports))

