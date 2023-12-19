import json
import ipaddress
import aiohttp
import asyncio
from PyQt5.QtCore import QThread, pyqtSignal
from typing import Optional


TIMEOUT = 10
SEM_LIMIT = 50
http_session = None

async def get_http_session():
    global http_session
    if http_session is None:
        print("Создание HTTP сессии")
        http_session = aiohttp.ClientSession()
    return http_session

async def close_http_session():
    global http_session
    if http_session:
        print("Закрытие HTTP сессии")
        await http_session.close()
        http_session = None

async def send_http_request(url: str) -> str:
    async with aiohttp.ClientSession() as session:
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


async def determine_miner_model(ip: str) -> Optional[dict]:
    response = await send_http_request(f'http://{ip}/api/v1/info')
    if response:
        try:
            data = json.loads(response)
            return {
                'model': data.get('model'),
                'fw_name': data.get('fw_name', 'Unknown Firmware'),
                'response': data
            }
        except json.JSONDecodeError as e:
            print(f"Ошибка декодирования JSON в ответе от {ip}: {e}")
    return None



class ScanThread(QThread):
    ip_processed_signal = pyqtSignal(dict, int)
    scan_finished_signal = pyqtSignal(int)
    error_signal = pyqtSignal(str)  # ошибка 
    progress_signal = pyqtSignal(int)  # Сигнал для передачи значения прогресса



    def __init__(self, ip_list, credentials=None):
        super().__init__()
        self.ip_list = ip_list
        self.credentials = credentials or {}
        print(f"Создан экземпляр ScanThread {id(self)} с IP-адресами: {ip_list}")
        self.processed_count = 0  # Счетчик обработанных IP
    
    async def получить_токен(self, ip: str, пароль: str) -> Optional[str]:
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

    async def scan_network(self, ip_range: str):
        print(f"Сканирование сети в диапазоне {ip_range}")
        network = ipaddress.ip_network(ip_range, strict=False)
        total_ips = len(list(network.hosts()))  # Общее количество IP-адресов
        self.total_count = total_ips  # Сохраняем общее количество для расчета прогресса
        results = {}
        semaphore = asyncio.Semaphore(SEM_LIMIT)
        tasks = [self.handle_ip(str(ip), semaphore, results) for ip in network.hosts()]
        await asyncio.gather(*tasks)
        return results
    
    async def send_model_specific_commands(self, ip: str, model_data: dict, credentials: dict) -> dict:
        print(f"Вызов send_model_specific_commands для {ip}")
        command_responses = {}
         # Проверяем, что прошивка майнера - Vnish
        if model_data.get("fw_name") != "Vnish":
            print(f"Майнер {ip} не имеет прошивки Vnish")
            return {}
        токен = None
        if model_data.get("fw_name") == "Vnish":
            пароль = credentials.get("VnishOS", {}).get("password")
            if пароль:
                токен = await self.получить_токен(ip, пароль)
                if not токен:
                    print(f"Токен не получен для {ip}, запросы будут выполнены без токена")
                    self.error_signal.emit(f"Проверьте пароль.")
                    return {}  # Возвращаем пустой словарь, если токен не получен
            else:
                print(f"Пароль для VnishOS не задан для IP {ip}")
                return {}  # Выход, если пароль не задан

        # Запрос summary (с токеном, если он есть)
        url_summary = f"http://{ip}/api/v1/summary"
        headers = {}
        if токен:
            headers["Authorization"] = f"Bearer {токен}"
        async with aiohttp.ClientSession() as session:
            async with session.get(url_summary, headers=headers) as ответ:
                if ответ.status == 200:
                    command_responses["summary"] = await ответ.json()
                else:
                    print(f"Ошибка при запросе summary для {ip}: {ответ.status}")


    # Выполнение запроса info в любом случае
        response_info = await send_http_request(f'http://{ip}/api/v1/info')
        command_responses["info"] = json.loads(response_info) if response_info else {}

        print(f"Обработанные данные info для {ip}: {command_responses['info']}")
        print(f"Обработанные данные summary для {ip}: {command_responses['summary']}")
        return command_responses

    
    async def handle_ip(self, ip: str, semaphore, results):
        async with semaphore:
            model_info = await determine_miner_model(ip)
            if model_info:
                command_data = await self.send_model_specific_commands(ip, model_info, self.credentials)
                if command_data:
                    results[ip] = command_data
                    self.ip_processed_signal.emit({ip: command_data}, 1)
            # Увеличиваем счетчик обработанных IP в любом случае
            self.processed_count += 1
            progress_percent = int((self.processed_count / self.total_count) * 100)
            self.progress_signal.emit(progress_percent)
        


    async def scan_all_networks(self, ip_ranges):
        tasks = [self.scan_network(ip_range) for ip_range in ip_ranges]
        results = await asyncio.gather(*tasks)
        return {ip: data for network in results for ip, data in network.items()}
    # подсчет айпи для прогресс бара 
    def calculate_total_ips(self, ip_ranges):
        total_ips = 0
        for ip_range in ip_ranges:
            network = ipaddress.ip_network(ip_range, strict=False)
            total_ips += len(list(network.hosts()))
        return total_ips

    def run(self):
        print("Запуск потока сканирования")
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        self.total_count = self.calculate_total_ips(self.ip_list)  # Подсчет общего количества IP
        self.processed_count = 0  # Счетчик обработанных IP
        try:
            all_results = loop.run_until_complete(self.scan_all_networks(self.ip_list))
            print(f"Сканирование завершено, найдено устройств: {len(all_results)}")
            self.scan_finished_signal.emit(len(all_results))
        except Exception as e:
            print(f"Ошибка в потоке сканирования: {e}")
        finally:
            loop.close()