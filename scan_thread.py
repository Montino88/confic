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
TIMEOUT = 2
SEM_LIMIT = 50

async def send_socket_command(ip: str, port: int, command: str, json_format=False) -> str:
    print(f"Attempting to send command '{command}' to {ip}:{port}")
    try:
        reader, writer = await asyncio.wait_for(asyncio.open_connection(ip, port), timeout=TIMEOUT)
        
        if json_format:
            command = json.dumps({"cmd": command})
            
        writer.write(command.encode())
        data = await asyncio.wait_for(reader.read(90000), timeout=TIMEOUT)
        writer.close()
        await writer.wait_closed()
        print(f"Received response from {ip}:{port}: {data.decode()}")
        return data.decode()
    except asyncio.TimeoutError:
        print(f"Timeout error for IP {ip} on port {port}")
        return ""
    except ConnectionRefusedError:
        print(f"Connection refused for IP {ip} on port {port}")
        return ""
    except Exception as e:
        print(f"Unknown error for IP {ip} on port {port}: {e}")
        return ""


async def is_port_open(ip: str, port: int = 4028) -> bool:
    print(f"Checking if port {port} is open on {ip}")
    try:
        reader, writer = await asyncio.wait_for(asyncio.open_connection(ip, port), timeout=TIMEOUT)
        writer.close()
        await writer.wait_closed()
        return True
    except (asyncio.TimeoutError, ConnectionRefusedError):
        return False

async def determine_miner_model(ip: str) -> Optional[str]:
    # Сначала попробуем определить модель для Avalon через команду "version"
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

    # Если не удалось определить модель Avalon, попробуем определить модель для Vnish через команду "stats"
    response = await send_socket_command(ip, 4028, "stats")
    if "ERROR" not in response:
        if "Type=" in response:
            try:
                type_index = response.index("Type=") + 5
                model_full = response[type_index:].split('|')[0]
                return {"model": model_full, "response": response}

            except (TypeError, LookupError):
                pass

     # Попробуем определить модель WhatsMiner через команду "devdetails"
    response = await send_socket_command(ip, 4028, "devdetails", json_format=True)
    if "ERROR" not in response and response:
        try:
            sock_json_data = json.loads(response)
            if "DEVDETAILS" in sock_json_data:
                miner_model = sock_json_data["DEVDETAILS"][0]["Model"]
                return {"model": miner_model, "response": response}


        except (TypeError, LookupError, json.JSONDecodeError):
            pass

    return None



async def scan_network(ip_range: str) -> dict:
    print(f"Starting to scan network {ip_range}")
    network = ipaddress.ip_network(ip_range, strict=False)
    results = {}
    semaphore = asyncio.Semaphore(SEM_LIMIT)

    async def handle_ip(ip: str):
        async with semaphore:
            print(f"Checking IP {ip}")
            if await is_port_open(ip, 4028):
                model = await determine_miner_model(ip)
                if model:
                    command_data = await send_model_specific_commands(ip, model['model'])  # получаем словарь с ответами
                    model["command_data"] = command_data  # сохраняем этот словарь внутри модели
                    results[ip] = model
                else:
                    print(f"No miner model found at {ip}")
            else:
                print(f"{ip} is not open on port 4028")

    await asyncio.gather(*[handle_ip(str(ip)) for ip in network.hosts()])
    return results


def print_final_results(results: dict):
    print("Final results:")
    if not results:
        print("Не найдено ни одного майнера.")
        return
    for ip, model in results.items():
        print(f"{ip} - {model}")

async def send_model_specific_commands(ip: str, model_data: str):
    print(f"Sending specific commands for {model_data} at {ip}")
    command_responses = {}  # словарь для хранения ответов

    if "Antminer" in model_data:

        response_stats = await send_socket_command(ip, 4028, "stats")
        response_pools = await send_socket_command(ip, 4028, "pools")
        command_responses["stats"] = response_stats
        command_responses["pools"] = response_pools
        print(f"[Antminer ] IP: {ip} | Stats: {response_stats} | Pools: {response_pools}")

    elif "avalon" in model_data.lower():
        response_version = await send_socket_command(ip, 4028, "version")
        response_pools = await send_socket_command(ip, 4028, "pools")
        response_estats = await send_socket_command(ip, 4028, "estats")
        command_responses["version"] = response_version
        command_responses["pools"] = response_pools
        command_responses["estats"] = response_estats
        print(f"[AVALON] IP: {ip} | Version: {response_version} | Pools: {response_pools} | Estats: {response_estats}")

    elif "whatsminer" in model_data.lower():
        response_devdetails = await send_socket_command(ip, 4028, "devdetails", json_format=True)
        response_devs = await send_socket_command(ip, 4028, "devs", json_format=True)
        response_pools = await send_socket_command(ip, 4028, "pools", json_format=True)
        command_responses["devdetails"] = response_devdetails
        command_responses["devs"] = response_devs
        command_responses["pools"] = response_pools
        print(f"[WHATSMINER] IP: {ip} | Devdetails: {response_devdetails} | Devs: {response_devs} | Pools: {response_pools}")

    else:
        print(f"Неизвестная модель устройства для IP {ip}")

    return command_responses


 



class ScanThread(QThread):
    finished = pyqtSignal(dict, int)
    update_table_signal = pyqtSignal(dict, int)
    ip_processed_signal = pyqtSignal(dict, int)

    monitoring_data_signal = pyqtSignal(dict)

    def __init__(self, ip_list):
        super().__init__()
        self.ip_list = ip_list

    async def get_miner_list(self, ip):
        return await scan_network(ip)

   

   
    def run(self):
        print("Начало метода run...")
        open_ports = {}
        all_ips = []
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        for ip in self.ip_list:
            try:
                ips_for_ip = loop.run_until_complete(self.get_miner_list(ip))
                if ips_for_ip:  # Добавляем эту проверку
                    open_ports.update(ips_for_ip)
            except Exception as e:
               print(f"Ошибка при выполнении асинхронных задач: {e}")



       

        print("Закрытие цикла событий...")
        loop.close()

        print("Вывод итоговых результатов...")
        print_final_results(open_ports)

        print("Отправка сигналов...")

        self.monitoring_data_signal.emit(open_ports)
        self.ip_processed_signal.emit(open_ports, len(open_ports))
        #self.finished.emit(open_ports, len(open_ports))



        print("Сигнал ip_processed_signal отправлен с данными:", open_ports)

        print("Сканирование завершено.")


