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
TIMEOUT = 10
SEM_LIMIT = 90
http_session = None

async def get_http_session():
    global http_session
    if http_session is None:
        http_session = aiohttp.ClientSession()
    return http_session

async def close_http_session():
    global http_session
    if http_session:
        await http_session.close()
        http_session = None

async def send_http_request(url: str) -> str:
    session = await get_http_session()
    try:
        async with session.get(url, timeout=TIMEOUT) as response:
            if response.status == 200:
                return await response.text()
            else:
                print(f"Ошибка при запросе к {url}: {response.status}")
                return ""
    except asyncio.TimeoutError:
        print(f"Превышено время ожидания для запроса к {url}")
        return ""
    except Exception as e:
        print(f"Исключение при запросе к {url}: {e}")
        return ""

async def is_http_port_open(ip: str, port: int = 80) -> bool:
    url = f"http://{ip}:{port}"
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=TIMEOUT) as response:
                if response.status in [200, 401, 403]:  # Успешный ответ или неавторизованный/запрещенный доступ
                    return True
                else:
                    return False
    except asyncio.TimeoutError:
        return False
    except Exception as e:
        return False
    


async def send_http_request(url: str) -> str:
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(url, timeout=TIMEOUT) as response:  # Установка времени ожидания для запроса
                if response.status == 200:
                    return await response.text()
                else:
                    print(f"Ошибка при запросе к {url}: {response.status}")
                    return ""
        except asyncio.TimeoutError:
            print(f"Превышено время ожидания для запроса к {url}")
            return ""
        except Exception as e:
            print(f"Исключение при запросе к {url}: {e}")
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
        print(f"Тайм-аут для сокет-команды на {ip}")
        return ""
    except ConnectionRefusedError:
        print(f"Отказ в подключении для сокет-команды на {ip}")
        return ""
    except Exception as e:
        print(f"Ошибка при отправке сокет-команды на {ip}: {e}")
        return ""


async def is_port_open(ip: str, port: int = 4028) -> bool:
    try:
        reader, writer = await asyncio.wait_for(asyncio.open_connection(ip, port), timeout=TIMEOUT)
        writer.close()
        await writer.wait_closed()
        return True
    except (asyncio.TimeoutError, ConnectionRefusedError):
        return False

async def determine_miner_model(ip: str) -> Optional[dict]:
    # Проверяем доступность HTTP-порта перед отправкой HTTP-запроса
    if await is_http_port_open(ip, 80):
         # Попытка определить модель через HTTP запрос
        vnish_response = await send_http_request(f'http://{ip}/api/v1/info')
        if vnish_response:
            try:
                response_data = json.loads(vnish_response)
                model = response_data.get('model')
                fw_name = response_data.get('fw_name', 'Unknown Firmware')
                if model:
                    print(f"Модель ASIC: {model}, Прошивка: {fw_name}")
                    return {"model": model, "fw_name": fw_name, "response": response_data}
                else:
                    print(f"Данные о модели не найдены в ответе от {ip}")
            except json.JSONDecodeError as e:
                print(f"Ошибка декодирования JSON в ответе от {ip}: {e}")
            

    # Попытка определения модели через команду version
    response = await send_socket_command(ip, 4028, "version")
    if "ERROR" not in response and response:
        if "PROD=" in response:
            try:
                prod_index = response.index("PROD=") + 5
                model_full = response[prod_index:].split(',')[0]
                model = model_full.split('-')[0]
                return {"model": model_full, "response": response}
            except (TypeError, LookupError):
                pass
        # В случае неудачи продолжаем следующую попытку

    # Попытка определения модели через команду stats
    response = await send_socket_command(ip, 4028, "stats")
    if "ERROR" not in response:
        if "Type=" in response:
            try:
                type_index = response.index("Type=") + 5
                model_full = response[type_index:].split('|')[0]
                return {"model": model_full, "response": response}
            except (TypeError, LookupError):
                pass

    # Если ни один из методов не сработал
    print(f"Не удалось определить модель майнера для IP {ip}")
    return None


class ScanThread(QThread):
    ip_processed_signal = pyqtSignal(dict, int)
    scan_finished_signal = pyqtSignal(int)

    
    def __init__(self, ip_list, credentials=None):
        super().__init__()
        self.ip_list = ip_list
        self.credentials = credentials or {}  # Инициализация пустым словарем
        print(f"Создан экземпляр ScanThread {id(self)} с IP-адресами: {ip_list}")

        

    def set_credentials(self, credentials):
        self.credentials = credentials
    
    async def get_miner_list(self, ip):
        return await self.scan_network(ip)
    
    async def получить_токен(self, ip, пароль):
        url = f"http://{ip}/api/v1/unlock"
        данные = {"pw": пароль}
        async with aiohttp.ClientSession() as session:
            try:
                async with session.post(url, json=данные) as ответ:
                    if ответ.status == 200:
                        json_response = await ответ.json()
                        токен = json_response.get("token")
                        print(f"Токен получен для {ip}: {токен}")
                        return токен
                    else:
                        print(f"Ошибка при получении токена для {ip}: {ответ.status}")
                        return None
            except Exception as e:
                print(f"Ошибка при получении токена для {ip}: {e}")
                return None
  
         
    async def send_model_specific_commands(self, ip: str, model_data: dict):
        command_responses = {}

        if model_data.get("fw_name") == "Vnish":
            пароль = self.credentials.get("VnishOS", {}).get("password")
            if пароль:
                токен = await self.получить_токен(ip, пароль)
                if токен:
                    # Если токен получен, используем его для запроса summary
                    url = f"http://{ip}/api/v1/summary"
                    заголовки = {"Authorization": f"Bearer {токен}"}
                    async with aiohttp.ClientSession() as session:
                        async with session.get(url, headers=заголовки) as ответ:
                            if ответ.status == 200:
                                command_responses["summary"] = await ответ.json()
                            else:
                                print(f"Ошибка при запросе summary для {ip} с токеном: {ответ.status}")
                else:
                    print(f"Токен не получен для {ip}, выполняется запрос без токена")
                    # Выполнение запроса summary без токена
                    response_summary = await send_http_request(f'http://{ip}/api/v1/summary')
                    command_responses["summary"] = json.loads(response_summary) if response_summary else {}
            else:
                print(f"Пароль для VnishOS не задан для IP {ip}")
                # Выполнение запроса summary без токена
                response_summary = await send_http_request(f'http://{ip}/api/v1/summary')
                command_responses["summary"] = json.loads(response_summary) if response_summary else {}

        # Выполнение запроса info в любом случае
            response_info = await send_http_request(f'http://{ip}/api/v1/info')
            command_responses["info"] = json.loads(response_info) if response_info else {}
            print(f"Обработанные данные info для {ip}: {command_responses['info']}")
            #print(f"Обработанные данные summary для {ip}: {command_responses['summary']}")
 

           
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