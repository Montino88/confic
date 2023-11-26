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
import aiohttp
import requests

PORTS = [80, 4028]
TIMEOUT = 15
SEM_LIMIT = 90


async def send_http_request(url: str) -> str:
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(url) as response:
                if response.status == 200:
                    return await response.text()
                else:
                    return ""
        except Exception as e:
            return ""
        
async def send_socket_command(ip: str, port: int, command: str, json_format=False) -> str:
    try:
        reader, writer = await asyncio.wait_for(asyncio.open_connection(ip, port), timeout=TIMEOUT)
        
        if json_format:
            command = json.dumps({"cmd": command})
            
        writer.write(command.encode())
        data = await asyncio.wait_for(reader.read(200000000), timeout=TIMEOUT)

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
                            print("Found bitmicro driver")  # Добавлено для диагностики
                            return {"driver": driver, "response": response}
        except (TypeError, LookupError, json.JSONDecodeError) as e:
            print("Error:", e)  # Вывод информации об ошибке


    vnish_response = await send_http_request(f'http://{ip}/api/v1/info')
    print(f"Ответ от {ip} на команду Info: {vnish_response}")
    if vnish_response:
        try:
            response_data = json.loads(vnish_response)
            model = response_data.get('model')
            fw_name = response_data.get('fw_name', 'Unknown Firmware')  # Добавляем fw_name

            if model:
                print(f"Модель ASIC: {model}, Прошивка: {fw_name}")
                return {"model": model, "fw_name": fw_name, "response": response_data}
            else:
                print(f"Данные о модели не найдены в ответе от {ip}")
        except json.JSONDecodeError as e:
            print(f"Ошибка декодирования JSON в ответе от {ip}: {e}")
        except Exception as e:
            print(f"Неизвестная ошибка при обработке ответа от {ip}: {e}")
    else:
        print(f"Пустой или недействительный ответ от {ip}")

    return None



class ScanThread(QThread):
    ip_processed_signal = pyqtSignal(dict, int)
    scan_finished_signal = pyqtSignal(int)

    
    def __init__(self, ip_list):
        super().__init__()
        self.ip_list = ip_list
        print(f"Создан экземпляр ScanThread {id(self)} с IP-адресами: {ip_list}")

        

   
    
    async def get_miner_list(self, ip):
        return await self.scan_network(ip)
    
    async def send_model_specific_commands(self, ip: str, model_data: dict):
        if not isinstance(model_data, dict):
            print(f"Ожидался словарь для model_data, получено: {type(model_data)}")
            return {}

        command_responses = {}  # словарь для хранения ответов

        if model_data.get("fw_name") == "Vnish":
            response_info = await send_http_request(f'http://{ip}/api/v1/info')
            response_summary = await send_http_request(f'http://{ip}/api/v1/summary')

            # Преобразование ответов в словари, если они в формате JSON
            try:
                command_responses["info"] = json.loads(response_info) if response_info else {}
                command_responses["summary"] = json.loads(response_summary) if response_summary else {}

            # Вывести результаты
                print("Response for info:", response_info)
                print("Response for summary:", response_summary)

            except json.JSONDecodeError as e:
                print(f"Ошибка декодирования JSON в ответе от {ip}: {e}")

        # Проверка на Antminer
        elif "Antminer" in model_data.get("model", ""):
            response_stats = await send_socket_command(ip, 4028, "stats")
            response_pools = await send_socket_command(ip, 4028, "pools")
            command_responses["stats"] = response_stats
            command_responses["pools"] = response_pools

        # Проверка на Avalon
        elif "avalon" in model_data.get("model", "").lower():
            response_pools = await send_socket_command(ip, 4028, "pools")
            response_estats = await send_socket_command(ip, 4028, "estats")
            command_responses["pools"] = response_pools
            command_responses["estats"] = response_estats
  
        # Проверка на Bitmicro
        elif model_data.get("driver") == 'bitmicro':
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
            if await is_port_open(ip, 4028):
                model_data = await determine_miner_model(ip)
               

                if not isinstance(model_data, dict):
                    return
            
                command_data = await self.send_model_specific_commands(ip, model_data)

                if command_data:
                    model_data["command_data"] = command_data
                    results[ip] = model_data
                else:
                    print(f"No command data found for model at {ip}")
            
                self.ip_processed_signal.emit({ip: model_data}, 1 if model_data else 0)

            else:
                print(f"{ip} is not open on port 4028")

    async def scan_network(self, ip_range: str):
        
        network = ipaddress.ip_network(ip_range, strict=False)
        results = {}
        semaphore = asyncio.Semaphore(SEM_LIMIT)
        await asyncio.gather(*[self.handle_ip(str(ip), semaphore, results) for ip in network.hosts()])

        return results
    
    async def scan_all_networks(self, ip_ranges):
        tasks = [self.scan_network(ip_range) for ip_range in ip_ranges]
        results = await asyncio.gather(*tasks)
        return {ip: data for network in results for ip, data in network.items()}
    

    
    def run(self):
        print("Начало метода run...")
        
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        try:
            all_results = loop.run_until_complete(self.scan_all_networks(self.ip_list))
        except Exception as e:
            print(f"Ошибка при выполнении асинхронных задач: {e}")
            all_results = {}

        loop.close()
        self.scan_finished_signal.emit(len(all_results))