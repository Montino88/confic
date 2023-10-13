import socket
import json
from PyQt5.QtCore import QThread, pyqtSignal
import concurrent.futures
import asyncio
from concurrent.futures import ThreadPoolExecutor
import ipaddress
from typing import Optional
from json import JSONDecodeError
from collections import defaultdict

PORTS = [80, 4028]
TIMEOUT = 5
SEM_LIMIT = 90
# Глобальное множество для хранения известных IP-адресов 
known_ips = set()

async def send_socket_command(ip: str, port: int, command: str, json_format=False) -> str:
    try:
        reader, writer = await asyncio.wait_for(asyncio.open_connection(ip, port), timeout=TIMEOUT)
        
        if json_format:
            command = json.dumps({"cmd": command})
            
        writer.write(command.encode())
        data = await asyncio.wait_for(reader.read(200000), timeout=TIMEOUT)
        writer.close()
        await writer.wait_closed()
        return data.decode()
    except asyncio.TimeoutError:
        return ""
    except ConnectionRefusedError:
        return ""
    except Exception as e:
        return ""

async def is_port_open(ip: str, port: int = 4028) -> bool:
    try:
        reader, writer = await asyncio.wait_for(asyncio.open_connection(ip, port), timeout=TIMEOUT)
        writer.close()
        await writer.wait_closed()
        return True
    except (asyncio.TimeoutError, ConnectionRefusedError):
        return False

async def determine_miner_model(ip: str) -> Optional[str]:
    response = await send_socket_command(ip, 4028, "version")
    if "ERROR" not in response:
        if response and "PROD=" in response:
            try:
                prod_index = response.index("PROD=") + 5
                model_full = response[prod_index:].split(',')[0]
                model = model_full.split('-')[0]
                return {"model": model_full, "response": response}

            except (TypeError, LookupError):
                pass

    response = await send_socket_command(ip, 4028, "stats")
    if "ERROR" not in response:
        if "Type=" in response:
            try:
                type_index = response.index("Type=") + 5
                model_full = response[type_index:].split('|')[0]
                return {"model": model_full, "response": response}

            except (TypeError, LookupError):
                pass

    response = await send_socket_command(ip, 4028, "devdetails", json_format=True)
    if "ERROR" not in response and response:
        try:
            sock_json_data = json.loads(response)
            if "DEVDETAILS" in sock_json_data:
                for dev_detail in sock_json_data["DEVDETAILS"]:
                    if "Driver" in dev_detail:
                        driver = dev_detail["Driver"]
                        if driver == "bitmicro":
                            return {"driver": driver, "response": response}
        except (TypeError, LookupError, json.JSONDecodeError) as e:
            pass

class ScanThread(QThread):
    ip_processed_signal = pyqtSignal(dict, int)
    scan_finished_signal = pyqtSignal(int)

    def __init__(self, ip_list):
        super().__init__()
        self.ip_list = ip_list

    async def get_miner_list(self, ip):
        return await self.scan_network(ip)
    
    async def send_model_specific_commands(self, ip: str, model_data: str):

        command_responses = {}  # словарь для хранения ответов

        if "Antminer" in model_data:
            response_stats = await send_socket_command(ip, 4028, "stats")
            response_pools = await send_socket_command(ip, 4028, "pools")
            command_responses["stats"] = response_stats
            command_responses["pools"] = response_pools

        elif "avalon" in model_data.lower():
            response_pools = await send_socket_command(ip, 4028, "pools")
            response_estats = await send_socket_command(ip, 4028, "estats")
            command_responses["pools"] = response_pools
            command_responses["estats"] = response_estats

        elif model_data == 'bitmicro':
            response_devdetails = await send_socket_command(ip, 4028, "devdetails", json_format=True)
            response_edevs = await send_socket_command(ip, 4028, "edevs", json_format=True)
            response_summary = await send_socket_command(ip, 4028, "summary", json_format=True)
            response_pools = await send_socket_command(ip, 4028, "pools", json_format=True)
            command_responses["devdetails"] = response_devdetails
            command_responses["edevs"] = response_edevs
            command_responses["summary"] = response_summary
            command_responses["pools"] = response_pools

        return command_responses
    
    async def handle_ip(self, ip: str, semaphore, results):
        async with semaphore:
            if ip in known_ips or await is_port_open(ip, 4028):
                if ip not in known_ips:
                    known_ips.add(ip)
                model = await determine_miner_model(ip)
                if model:
                    identification_key = model.get('model', model.get('driver', None))
                    command_data = await self.send_model_specific_commands(ip, identification_key)


                    model["command_data"] = command_data
                    results[ip] = model

                else:
                    print(f"No miner model found at {ip}")
                    if ip in known_ips:
                        known_ips.remove(ip)

                self.ip_processed_signal.emit({ip: model if model else None}, 1 if model else 0)


            else:
                print(f"{ip} is not open on port 4028")
                if ip in known_ips:
                    known_ips.remove(ip)

    async def scan_network(self, ip_range: str):
        print(f"Known IPs before scanning: {known_ips}")
        network = ipaddress.ip_network(ip_range, strict=False)
        results = {}
        semaphore = asyncio.Semaphore(SEM_LIMIT)
        await asyncio.gather(*[self.handle_ip(str(ip), semaphore, results) for ip in network.hosts()])

        return results
    
    


    def run(self):
        print("Начало метода run...")
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        all_results = {}

        for ip in self.ip_list:
            try:
                ips_for_ip = loop.run_until_complete(self.get_miner_list(ip))
                if ips_for_ip:
                    all_results.update(ips_for_ip)
            except Exception as e:
                print(f"Ошибка при выполнении асинхронных задач: {e}")

        loop.close()
        self.scan_finished_signal.emit(len(all_results))