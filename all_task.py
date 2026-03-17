import os
import json
from datetime import datetime
from decimal import Decimal
from typing import Dict, List, Optional, Tuple
from collections import defaultdict
import bisect

from models import Car, CarFullInfo, CarStatus, Model, ModelSaleStats, Sale


class CarService:
    def __init__(self, root_directory_path: str) -> None:
        self.root_directory_path = root_directory_path
        self._ensure_directories()
        
        # Загружаем индексы в память (они должны быть отсортированы)
        self.models_index = self._load_sorted_index("models_index.txt")
        self.cars_index = self._load_sorted_index("cars_index.txt")
        self.sales_index = self._load_sorted_index("sales_index.txt")
        self.sales_by_number_index = self._load_sorted_index("sales_by_number_index.txt")
    
    def _ensure_directories(self):
        """Создание необходимых директорий"""
        os.makedirs(self.root_directory_path, exist_ok=True)
    
    def _load_sorted_index(self, filename: str) -> List[Tuple[str, int]]:
        """Загрузка отсортированного индекса из файла"""
        index_path = os.path.join(self.root_directory_path, filename)
        index = []
        
        if os.path.exists(index_path):
            with open(index_path, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line:
                        parts = line.split(';')
                        if len(parts) >= 2:
                            key = parts[0]
                            try:
                                line_num = int(parts[1])
                                index.append((key, line_num))
                            except ValueError:
                                continue
        
        # Сортируем индекс по ключу
        index.sort(key=lambda x: x[0])
        return index
    
    def _save_sorted_index(self, filename: str, index: List[Tuple[str, int]]):
        """Сохранение отсортированного индекса в файл"""
        index_path = os.path.join(self.root_directory_path, filename)
        
        # Сортируем перед сохранением
        index.sort(key=lambda x: x[0])
        
        with open(index_path, 'w') as f:
            for key, line_num in index:
                f.write(f"{key};{line_num}\n")
    
    def _find_in_index(self, index: List[Tuple[str, int]], key: str) -> Optional[int]:
        """Поиск ключа в отсортированном индексе (бинарный поиск)"""
        # Используем бинарный поиск для отсортированного списка
        idx = bisect.bisect_left([item[0] for item in index], key)
        if idx < len(index) and index[idx][0] == key:
            return index[idx][1]
        return None
    
    def _insert_into_index(self, index: List[Tuple[str, int]], key: str, line_num: int):
        """Вставка новой записи в отсортированный индекс"""
        # Находим позицию для вставки
        idx = bisect.bisect_left([item[0] for item in index], key)
        
        # Проверяем, не существует ли уже такой ключ
        if idx < len(index) and index[idx][0] == key:
            # Обновляем существующую запись
            index[idx] = (key, line_num)
        else:
            # Вставляем новую запись
            index.insert(idx, (key, line_num))
    
    def _remove_from_index(self, index: List[Tuple[str, int]], key: str) -> bool:
        """Удаление записи из отсортированного индекса"""
        # Находим позицию для удаления
        idx = bisect.bisect_left([item[0] for item in index], key)
        
        if idx < len(index) and index[idx][0] == key:
            # Удаляем запись
            index.pop(idx)
            return True
        return False
    
    def _format_line(self, data: dict) -> str:
        """Форматирование строки для записи в файл"""
        # Конвертируем все значения в строки
        formatted = {}
        for key, value in data.items():
            if isinstance(value, datetime):
                formatted[key] = value.isoformat()
            elif isinstance(value, Decimal):
                formatted[key] = str(value)
            elif value is None:
                formatted[key] = ""
            else:
                formatted[key] = str(value)
        
        line = json.dumps(formatted, ensure_ascii=False)
        # Дополняем строку до 500 символов и добавляем \n
        return line.ljust(500) + '\n'
    
    def _append_to_data_file(self, file_path: str, data: dict) -> int:
        """Добавление записи в файл данных и возврат номера строки"""
        line = self._format_line(data)
        
        with open(file_path, 'a') as f:
            # Получаем текущую позицию (это будет номер строки)
            f.seek(0, 2)  # Перемещаемся в конец файла
            current_pos = f.tell()
            line_num = current_pos // 501 if current_pos > 0 else 0
            f.write(line)
            
        return line_num
    
    def _read_line(self, file_path: str, line_num: int) -> Optional[dict]:
        """Чтение строки из файла"""
        try:
            with open(file_path, 'r') as f:
                f.seek(line_num * 501)  # 500 символов + \n
                line = f.read(500).strip()
                if line:
                    return json.loads(line)
        except (FileNotFoundError, json.JSONDecodeError, IndexError):
            pass
        return None
    
    def _write_line(self, file_path: str, line_num: int, data: dict):
        """Запись строки в файл"""
        line = self._format_line(data)
        
        with open(file_path, 'r+') as f:
            f.seek(line_num * 501)
            f.write(line)
    
    def _check_model_exists(self, model_id: int) -> bool:
        """Проверка существования модели по ID"""
        return self._find_in_index(self.models_index, str(model_id)) is not None

    # Задание 1. Сохранение автомобилей и моделей
    def add_model(self, model: Model) -> Model:
        """Добавление модели автомобиля"""
        # Пути к файлам
        models_data_path = os.path.join(self.root_directory_path, "models.txt")
        
        # Проверяем, существует ли модель с таким id
        if self._check_model_exists(model.id):
            raise ValueError(f"Model with id {model.id} already exists")
        
        # Добавляем запись в файл данных
        line_num = self._append_to_data_file(models_data_path, model.model_dump())
        
        # Вставляем в отсортированный индекс в памяти
        self._insert_into_index(self.models_index, str(model.id), line_num)
        
        # Сохраняем обновленный индекс в файл
        self._save_sorted_index("models_index.txt", self.models_index)
        
        return model
    
    # Задание 1. Сохранение автомобилей и моделей
    def add_car(self, car: Car) -> Car:
        """Добавление автомобиля"""
        # Пути к файлам
        cars_data_path = os.path.join(self.root_directory_path, "cars.txt")
        
        # Проверяем, существует ли автомобиль с таким VIN
        if self._find_in_index(self.cars_index, car.vin) is not None:
            raise ValueError(f"Car with VIN {car.vin} already exists")
        
        # Проверяем, существует ли модель
        if not self._check_model_exists(car.model):
            raise ValueError(f"Model with id {car.model} not found")
        
        # Добавляем запись в файл данных
        line_num = self._append_to_data_file(cars_data_path, car.model_dump())
        
        # Вставляем в отсортированный индекс в памяти
        self._insert_into_index(self.cars_index, car.vin, line_num)
        
        # Сохраняем обновленный индекс в файл
        self._save_sorted_index("cars_index.txt", self.cars_index)
        
        return car

    # Задание 2. Сохранение продаж (ИСПРАВЛЕНО)
    def sell_car(self, sale: Sale) -> Car:
        """
        Продажа автомобиля.
        
        Алгоритм:
        1. Записать продажу в sales.txt и добавить в sales_index.txt
        2. Найти автомобиль в cars.txt через индекс
        3. Обновить статус автомобиля на 'sold' (можно продавать available и reserve)
        4. Записать обновленный автомобиль в cars.txt
        """
        print(f"\n=== Начало продажи автомобиля ===")
        print(f"VIN: {sale.car_vin}")
        print(f"Номер продажи: {sale.sales_number}")
        
        # 1. Записываем продажу в файл sales.txt
        sales_data_path = os.path.join(self.root_directory_path, "sales.txt")
        print(f"1. Записываем продажу в файл: {sales_data_path}")
        
        # Добавляем запись о продаже в конец файла
        sale_line_num = self._append_to_data_file(sales_data_path, sale.model_dump())
        print(f"   Продажа записана в строку: {sale_line_num}")
        
        # 2. Добавляем запись в индекс продаж (sales_index.txt)
        print(f"2. Обновляем индекс продаж (sales_index.txt)")
        
        # Вставляем в отсортированный индекс продаж
        self._insert_into_index(self.sales_index, sale.car_vin, sale_line_num)
        
        # Сохраняем обновленный индекс в файл
        self._save_sorted_index("sales_index.txt", self.sales_index)
        print(f"   Индекс продаж обновлен: {sale.car_vin} -> строка {sale_line_num}")
        
        # 3. Находим автомобиль в файле cars.txt через индекс
        print(f"3. Ищем автомобиль в индексе автомобилей")
        car_line_num = self._find_in_index(self.cars_index, sale.car_vin)
        
        if car_line_num is None:
            raise ValueError(f"Автомобиль с VIN {sale.car_vin} не найден в базе")
        
        print(f"   Автомобиль найден в строке: {car_line_num}")
        
        # 4. Читаем данные автомобиля из файла cars.txt
        cars_data_path = os.path.join(self.root_directory_path, "cars.txt")
        print(f"4. Читаем данные автомобиля из файла: {cars_data_path}")
        
        car_data = self._read_line(cars_data_path, car_line_num)
        if not car_data:
            raise ValueError(f"Не удалось прочитать данные автомобиля с VIN {sale.car_vin}")
        
        print(f"   Данные автомобиля прочитаны: {car_data['vin']}, статус: {car_data['status']}")
        
        # 5. Создаем объект Car и проверяем, можно ли его продать
        car = Car(
            vin=car_data['vin'],
            model=int(car_data['model']),
            price=Decimal(car_data['price']),
            date_start=datetime.fromisoformat(car_data['date_start']),
            status=CarStatus(car_data['status'])
        )
        
        # ИСПРАВЛЕНИЕ: Проверяем, что автомобиль можно продать (available или reserve)
        if car.status not in [CarStatus.available, CarStatus.reserve]:
            raise ValueError(f"Нельзя продать автомобиль со статусом {car.status}")
        
        # 6. Обновляем статус автомобиля на 'sold'
        print(f"5. Обновляем статус автомобиля с '{car.status}' на 'sold'")
        car.status = CarStatus.sold
        
        # 7. Записываем обновленный автомобиль обратно в файл cars.txt
        print(f"6. Записываем обновленные данные автомобиля в файл")
        self._write_line(cars_data_path, car_line_num, car.model_dump())
        print(f"   Данные автомобиля обновлены в строке: {car_line_num}")
        
        # 8. Добавляем запись в индекс продаж по номеру
        self._insert_into_index(self.sales_by_number_index, sale.sales_number, sale_line_num)
        self._save_sorted_index("sales_by_number_index.txt", self.sales_by_number_index)
        
        print(f"=== Продажа успешно завершена ===")
        return car
    
    # Задание 3. Доступные к продаже
    def get_cars(self, status: CarStatus) -> list[Car]:
        """Получение списка автомобилей по статусу"""
        car_path = os.path.join(self.root_directory_path, "cars.txt")
        cars = []
        
        if not os.path.exists(car_path):
            return cars
        
        # Читаем все строки файла
        with open(car_path, 'r') as f:
            line_num = 0
            while True:
                try:
                    f.seek(line_num * 501)
                    line = f.read(500).strip()
                    
                    if not line:
                        break
                    
                    car_data = json.loads(line)
                    
                    # Преобразуем данные
                    car_status = CarStatus(car_data['status'])
                    
                    if car_status == status:
                        car = Car(
                            vin=car_data['vin'],
                            model=int(car_data['model']),
                            price=Decimal(car_data['price']),
                            date_start=datetime.fromisoformat(car_data['date_start']),
                            status=car_status
                        )
                        cars.append(car)
                    
                    line_num += 1
                except (json.JSONDecodeError, UnicodeDecodeError):
                    break
        
        # Сортируем автомобили по VIN-коду
        cars.sort(key=lambda car: car.vin)
        
        return cars

    # Задание 4. Детальная информация (ИСПРАВЛЕНО)
    def get_car_info(self, vin: str) -> CarFullInfo | None:
        """
        Получение детальной информации об автомобиле по VIN-коду.
        
        Алгоритм:
        1. Прочитать данные об автомобиле из cars.txt через индекс
        2. Прочитать данные о модели из models.txt через индекс
        3. Прочитать информацию о продаже (если автомобиль продан)
        4. Собрать все данные в объект CarFullInfo
        
        Возвращает CarFullInfo или None, если автомобиль не найден.
        """
        print(f"\n=== Поиск детальной информации по VIN: {vin} ===")
        
        # 1. Прочитать данные об автомобиле
        print("1. Ищем автомобиль в индексе cars_index.txt")
        car_line_num = self._find_in_index(self.cars_index, vin)
        
        if car_line_num is None:
            print(f"   Автомобиль с VIN {vin} не найден в базе")
            return None
        
        print(f"   Автомобиль найден в строке: {car_line_num}")
        
        # Читаем данные автомобиля из файла cars.txt
        car_path = os.path.join(self.root_directory_path, "cars.txt")
        car_data = self._read_line(car_path, car_line_num)
        
        if not car_data:
            print(f"   Не удалось прочитать данные автомобиля из строки {car_line_num}")
            return None
        
        print(f"   Данные автомобиля прочитаны:")
        print(f"     VIN: {car_data['vin']}")
        print(f"     Модель ID: {car_data['model']}")
        print(f"     Статус: {car_data['status']}")
        
        # 2. Прочитать данные о модели
        model_id = str(car_data['model'])
        print(f"\n2. Ищем модель (ID: {model_id}) в индексе models_index.txt")
        
        model_line_num = self._find_in_index(self.models_index, model_id)
        if model_line_num is None:
            print(f"   Модель с ID {model_id} не найдена в базе")
            return None
        
        print(f"   Модель найдена в строке: {model_line_num}")
        
        # Читаем данные модели из файла models.txt
        model_path = os.path.join(self.root_directory_path, "models.txt")
        model_data = self._read_line(model_path, model_line_num)
        
        if not model_data:
            print(f"   Не удалось прочитать данные модели из строки {model_line_num}")
            return None
        
        print(f"   Данные модели прочитаны:")
        print(f"     Название: {model_data['name']}")
        print(f"     Бренд: {model_data['brand']}")
        
        # 3. Прочитать информацию о продаже (если автомобиль продан)
        sales_date = None
        sales_cost = None
        
        # Проверяем статус автомобиля
        car_status = CarStatus(car_data['status'])
        print(f"\n3. Проверяем статус автомобиля: {car_status}")
        
        if car_status == CarStatus.sold:
            print(f"   Автомобиль продан. Ищем информацию о продаже...")
            
            # Ищем продажу в индексе продаж
            sale_line_num = self._find_in_index(self.sales_index, vin)
            
            if sale_line_num is not None:
                print(f"   Продажа найдена в индексе, строка: {sale_line_num}")
                
                # Читаем данные о продаже из файла sales.txt
                sales_path = os.path.join(self.root_directory_path, "sales.txt")
                sales_data = self._read_line(sales_path, sale_line_num)
                
                if sales_data:
                    sales_date = sales_data.get('sales_date')
                    sales_cost = sales_data.get('cost')
                    
                    print(f"   Данные о продаже прочитаны:")
                    print(f"     Дата продажи: {sales_date}")
                    print(f"     Стоимость продажи: {sales_cost}")
                else:
                    print(f"   Не удалось прочитать данные о продаже")
            else:
                print(f"   Продажа не найдена в индексе")
        
        # 4. Создаем и возвращаем объект CarFullInfo
        print(f"\n4. Собираем все данные в объект CarFullInfo")
        
        # Подготовка значений для CarFullInfo
        try:
            price = Decimal(car_data['price']) if car_data.get('price') else None
            date_start = datetime.fromisoformat(car_data['date_start']) if car_data.get('date_start') else None
            
            if sales_date:
                sales_date_dt = datetime.fromisoformat(sales_date)
            else:
                sales_date_dt = None
                
            if sales_cost:
                sales_cost_dec = Decimal(sales_cost)
            else:
                sales_cost_dec = None
            
            car_full_info = CarFullInfo(
                vin=car_data['vin'],
                car_model_name=model_data['name'],
                car_model_brand=model_data['brand'],
                price=price,
                date_start=date_start,
                status=car_status,
                sales_date=sales_date_dt,
                sales_cost=sales_cost_dec
            )
            
            print(f"   Объект CarFullInfo успешно создан")
            print(f"=== Поиск завершен успешно ===")
            
            return car_full_info
            
        except (KeyError, ValueError, TypeError) as e:
            print(f"   Ошибка при создании CarFullInfo: {e}")
            return None

    # Задание 5. Обновление ключевого поля
    def update_vin(self, vin: str, new_vin: str) -> Car:
        """
        Обновление VIN-кода автомобиля.
        
        Алгоритм:
        1. Найти автомобиль по старому VIN через индекс
        2. Проверить, что новый VIN не существует
        3. Обновить VIN в данных автомобиля
        4. Обновить запись в файле cars.txt
        5. Перестроить индекс (удалить старый VIN, добавить новый)
        6. Обновить VIN в записи о продаже (если есть)
        
        Возвращает обновленный объект Car.
        """
        print(f"\n=== Обновление VIN-кода ===")
        print(f"Старый VIN: {vin}")
        print(f"Новый VIN: {new_vin}")
        
        car_path = os.path.join(self.root_directory_path, "cars.txt")
        sales_path = os.path.join(self.root_directory_path, "sales.txt")
        
        # 1. Прочитать данные об автомобиле по старому VIN
        print("1. Ищем автомобиль по старому VIN в индексе cars_index.txt")
        car_line_num = self._find_in_index(self.cars_index, vin)
        
        if car_line_num is None:
            raise ValueError(f"Автомобиль с VIN {vin} не найден")
        
        print(f"   Автомобиль найден в строке: {car_line_num}")
        
        # Читаем данные автомобиля из файла cars.txt
        car_data = self._read_line(car_path, car_line_num)
        if not car_data:
            raise ValueError(f"Не удалось прочитать данные автомобиля с VIN {vin}")
        
        print(f"   Данные автомобиля прочитаны:")
        print(f"     Текущий VIN: {car_data['vin']}")
        print(f"     Модель: {car_data['model']}")
        print(f"     Статус: {car_data['status']}")
        
        # 2. Проверить, что новый VIN не существует
        print(f"\n2. Проверяем, что новый VIN {new_vin} не существует в базе")
        if self._find_in_index(self.cars_index, new_vin) is not None:
            raise ValueError(f"Автомобиль с VIN {new_vin} уже существует в базе")
        
        print(f"   Новый VIN свободен, можно обновлять")
        
        # 3. Обновить VIN в данных автомобиля
        print(f"\n3. Обновляем VIN в данных автомобиля")
        old_vin = car_data['vin']
        car_data['vin'] = new_vin
        
        # 4. Записать обновленный объект в файл cars.txt по тому же номеру строки
        print(f"4. Записываем обновленные данные в файл cars.txt (строка {car_line_num})")
        self._write_line(car_path, car_line_num, car_data)
        print(f"   Данные автомобиля обновлены в файле")
        
        # 5. Перестроить индекс автомобилей
        print(f"\n5. Перестраиваем индекс автомобилей (cars_index.txt)")
        
        # Удаляем старый VIN из индекса в памяти
        self._remove_from_index(self.cars_index, old_vin)
        print(f"   Старый VIN '{old_vin}' удален из индекса в памяти")
        
        # Добавляем новый VIN в индекс в памяти
        self._insert_into_index(self.cars_index, new_vin, car_line_num)
        print(f"   Новый VIN '{new_vin}' добавлен в индекс в памяти (строка {car_line_num})")
        
        # Сохраняем обновленный индекс в файл
        self._save_sorted_index("cars_index.txt", self.cars_index)
        print(f"   Индекс сохранен в файл cars_index.txt")
        
        # 6. Обновить VIN в записи о продаже (если автомобиль был продан)
        print(f"\n6. Проверяем, есть ли продажа для этого автомобиля")
        sale_line_num = self._find_in_index(self.sales_index, old_vin)
        
        if sale_line_num is not None:
            print(f"   Найдена продажа в строке: {sale_line_num}")
            
            # Читаем данные о продаже
            sales_data = self._read_line(sales_path, sale_line_num)
            if sales_data:
                print(f"   Данные о продаже прочитаны:")
                print(f"     Старый VIN в продаже: {sales_data.get('car_vin')}")
                
                # Обновляем VIN в данных о продаже
                sales_data['car_vin'] = new_vin
                
                # Записываем обновленные данные о продаже
                self._write_line(sales_path, sale_line_num, sales_data)
                print(f"   VIN в данных о продаже обновлен на '{new_vin}'")
                
                # Обновляем индекс продаж
                print(f"   Обновляем индекс продаж (sales_index.txt)")
                
                # Удаляем старый VIN из индекса продаж
                self._remove_from_index(self.sales_index, old_vin)
                print(f"     Старый VIN '{old_vin}' удален из индекса продаж")
                
                # Добавляем новый VIN в индекс продаж
                self._insert_into_index(self.sales_index, new_vin, sale_line_num)
                print(f"     Новый VIN '{new_vin}' добавлен в индекс продаж")
                
                # Сохраняем обновленный индекс продаж
                self._save_sorted_index("sales_index.txt", self.sales_index)
                print(f"     Индекс продаж сохранен в файл sales_index.txt")
            else:
                print(f"   Не удалось прочитать данные о продаже")
        else:
            print(f"   Продажа для этого автомобиля не найдена")
        
        # Создаем и возвращаем обновленный объект Car
        print(f"\n7. Создаем обновленный объект Car")
        updated_car = Car(
            vin=new_vin,
            model=int(car_data['model']),
            price=Decimal(car_data['price']),
            date_start=datetime.fromisoformat(car_data['date_start']),
            status=CarStatus(car_data['status'])
        )
        
        print(f"   Объект Car успешно создан с новым VIN: {updated_car.vin}")
        print(f"=== Обновление VIN завершено успешно ===")
        
        return updated_car

    # Задание 6. Удаление продажи (ИСПРАВЛЕНО)
    def revert_sale(self, sales_number: str) -> Car:
        """
        Отмена продажи автомобиля.
        
        Алгоритм (мягкое удаление):
        1. Найти продажу по номеру в индексе sales_by_number_index.txt
        2. Прочитать данные о продаже
        3. Найти автомобиль по VIN из продажи
        4. Обновить статус автомобиля на 'available'
        5. Пометить запись о продаже как удаленную (записать пустую строку)
        6. Удалить запись из индексов продаж
        
        Возвращает обновленный объект Car.
        """
        print(f"\n=== Отмена продажи ===")
        print(f"Номер продажи для отмены: {sales_number}")
        
        car_path = os.path.join(self.root_directory_path, "cars.txt")
        sales_path = os.path.join(self.root_directory_path, "sales.txt")
        
        # 1. Найти продажу по номеру в индексе
        print("1. Ищем продажу по номеру в индексе sales_by_number_index.txt")
        sale_line_num = self._find_in_index(self.sales_by_number_index, sales_number)
        
        if sale_line_num is None:
            raise ValueError(f"Продажа с номером {sales_number} не найдена")
        
        print(f"   Продажа найдена в строке: {sale_line_num}")
        
        # 2. Прочитать данные о продаже
        print("2. Читаем данные о продаже из файла sales.txt")
        sales_data = self._read_line(sales_path, sale_line_num)
        
        if not sales_data:
            raise ValueError(f"Не удалось прочитать данные о продаже с номером {sales_number}")
        
        vin = sales_data['car_vin']
        print(f"   Данные о продаже прочитаны:")
        print(f"     VIN автомобиля: {vin}")
        print(f"     Номер продажи: {sales_data.get('sales_number')}")
        print(f"     Дата продажи: {sales_data.get('sales_date')}")
        print(f"     Стоимость: {sales_data.get('cost')}")
        
        # 3. Найти автомобиль по VIN
        print(f"\n3. Ищем автомобиль по VIN {vin} в индексе cars_index.txt")
        car_line_num = self._find_in_index(self.cars_index, vin)
        
        if car_line_num is None:
            raise ValueError(f"Автомобиль с VIN {vin} не найден")
        
        print(f"   Автомобиль найден в строке: {car_line_num}")
        
        # Читаем данные автомобиля
        car_data = self._read_line(car_path, car_line_num)
        if not car_data:
            raise ValueError(f"Не удалось прочитать данные автомобиля с VIN {vin}")
        
        print(f"   Данные автомобиля прочитаны:")
        print(f"     Текущий статус: {car_data['status']}")
        
        # 4. Обновить статус автомобиля на 'available'
        print(f"\n4. Обновляем статус автомобиля с '{car_data['status']}' на 'available'")
        car_data['status'] = CarStatus.available.value
        
        # Записываем обновленные данные автомобиля
        self._write_line(car_path, car_line_num, car_data)
        print(f"   Статус автомобиля обновлен в файле cars.txt (строка {car_line_num})")
        
        # 5. Пометить запись о продаже как удаленную (мягкое удаление)
        print(f"\n5. Помечаем запись о продаже как удаленную")
        print(f"   Записываем пустую строку в файл sales.txt (строка {sale_line_num})")
        
        with open(sales_path, 'r+') as f:
            f.seek(sale_line_num * 501)
            f.write(' ' * 500 + '\n')  # Записываем строку из пробелов
        
        print(f"   Запись о продаже помечена как удаленная")
        
        # 6. Удалить запись из индексов продаж
        print(f"\n6. Удаляем запись из индексов продаж")
        
        # Удаляем из индекса продаж по VIN (sales_index.txt)
        if self._remove_from_index(self.sales_index, vin):
            print(f"   Запись удалена из индекса sales_index.txt (VIN: {vin})")
        else:
            print(f"   Запись не найдена в индексе sales_index.txt")
        
        # Удаляем из индекса продаж по номеру (sales_by_number_index.txt)
        if self._remove_from_index(self.sales_by_number_index, sales_number):
            print(f"   Запись удалена из индекса sales_by_number_index.txt (номер: {sales_number})")
        else:
            print(f"   Запись не найдена в индексе sales_by_number_index.txt")
        
        # Сохраняем обновленные индексы
        self._save_sorted_index("sales_index.txt", self.sales_index)
        self._save_sorted_index("sales_by_number_index.txt", self.sales_by_number_index)
        print(f"   Обновленные индексы сохранены в файлы")
        
        # Создаем и возвращаем обновленный объект Car
        print(f"\n7. Создаем обновленный объект Car")
        updated_car = Car(
            vin=car_data['vin'],
            model=int(car_data['model']),
            price=Decimal(car_data['price']),
            date_start=datetime.fromisoformat(car_data['date_start']),
            status=CarStatus(car_data['status'])
        )
        
        print(f"   Объект Car успешно создан")
        print(f"     Новый статус: {updated_car.status}")
        print(f"=== Отмена продажи завершена успешно ===")
        
        return updated_car

    # Задание 7. Самые продаваемые модели (ИСПРАВЛЕНО)
    def top_models_by_sales(self) -> list[ModelSaleStats]:
        """
        Получение топ-3 самых продаваемых моделей.
        
        Алгоритм:
        1. Собрать статистику продаж по ID моделей
        2. Отсортировать модели по количеству продаж (убыванию)
        3. При равенстве продаж сортировать по средней цене модели (убыванию)
        4. Взять топ-3 модели
        5. Получить информацию о каждой модели
        6. Вернуть список ModelSaleStats
        
        Возвращает список из 3 самых продаваемых моделей.
        """
        print(f"\n=== Определение самых продаваемых моделей ===")
        
        sales_path = os.path.join(self.root_directory_path, "sales.txt")
        car_path = os.path.join(self.root_directory_path, "cars.txt")
        model_path = os.path.join(self.root_directory_path, "models.txt")
        
        if not os.path.exists(sales_path):
            print("Файл продаж не найден. Нет данных для анализа.")
            return []
        
        # 1. Собираем информацию о моделях
        print("1. Собираем информацию о моделях...")
        model_info = {}  # model_id -> (name, brand, total_price, car_count)
        
        with open(model_path, 'r') as f:
            line_num = 0
            while True:
                try:
                    f.seek(line_num * 501)
                    line = f.read(500).strip()
                    
                    if not line:
                        break
                    
                    model_data = json.loads(line)
                    model_id = model_data['id']
                    model_info[model_id] = {
                        'name': model_data['name'],
                        'brand': model_data['brand'],
                        'total_price': Decimal('0'),
                        'car_count': 0
                    }
                    line_num += 1
                except (json.JSONDecodeError, UnicodeDecodeError, KeyError):
                    line_num += 1
                    continue
        
        # 2. Собираем информацию о ценах автомобилей для каждой модели
        print("2. Анализируем цены автомобилей по моделям...")
        with open(car_path, 'r') as f:
            line_num = 0
            while True:
                try:
                    f.seek(line_num * 501)
                    line = f.read(500).strip()
                    
                    if not line:
                        break
                    
                    car_data = json.loads(line)
                    model_id = car_data['model']
                    
                    if model_id in model_info:
                        try:
                            price = Decimal(car_data['price'])
                            model_info[model_id]['total_price'] += price
                            model_info[model_id]['car_count'] += 1
                        except (KeyError, ValueError):
                            pass
                    
                    line_num += 1
                except (json.JSONDecodeError, UnicodeDecodeError):
                    line_num += 1
                    continue
        
        # 3. Вычисляем средние цены
        for model_id, info in model_info.items():
            if info['car_count'] > 0:
                info['avg_price'] = info['total_price'] / info['car_count']
            else:
                info['avg_price'] = Decimal('0')
        
        # 4. Собираем статистику продаж
        print("3. Анализируем продажи...")
        sales_stats = defaultdict(int)  # model_id -> количество продаж
        total_sales = 0
        
        with open(sales_path, 'r') as f:
            line_num = 0
            while True:
                try:
                    f.seek(line_num * 501)
                    line = f.read(500).strip()
                    
                    if not line:
                        break
                    
                    # Пропускаем пустые строки (удаленные продажи)
                    if not line or line.isspace():
                        line_num += 1
                        continue
                    
                    total_sales += 1
                    
                    try:
                        sales_data = json.loads(line)
                        vin = sales_data['car_vin']
                        
                        # Используем индекс для быстрого поиска автомобиля
                        car_line_num = self._find_in_index(self.cars_index, vin)
                        if car_line_num is not None:
                            car_data = self._read_line(car_path, car_line_num)
                            if car_data:
                                model_id = car_data['model']
                                sales_stats[model_id] += 1
                    
                    except json.JSONDecodeError:
                        pass
                    
                    line_num += 1
                    
                except (UnicodeDecodeError, IndexError):
                    line_num += 1
                    continue
        
        print(f"   Всего обработано продаж: {total_sales}")
        print(f"   Уникальных моделей в продажах: {len(sales_stats)}")
        
        # 5. Преобразуем статистику в список для сортировки
        print("4. Подготавливаем данные для сортировки...")
        model_stats_list = []
        
        for model_id, sales_count in sales_stats.items():
            if model_id in model_info:
                avg_price = model_info[model_id]['avg_price']
                
                model_stats_list.append({
                    'model_id': model_id,
                    'sales_count': sales_count,
                    'avg_price': avg_price,
                    'name': model_info[model_id]['name'],
                    'brand': model_info[model_id]['brand']
                })
        
        # 6. ИСПРАВЛЕНИЕ: Сортировка по количеству продаж (убыванию),
        #    при равенстве - по средней цене (убыванию)
        print("5. Сортируем модели...")
        
        model_stats_list.sort(key=lambda x: (-x['sales_count'], -float(x['avg_price'])))
        
        # 7. Берем топ-3 модели
        print("6. Выбираем топ-3 модели...")
        top_models = model_stats_list[:3]
        
        # 8. Формируем результат
        print("7. Формируем результат...")
        result = []
        
        for i, model_stat in enumerate(top_models, 1):
            model_sale_stats = ModelSaleStats(
                car_model_name=model_stat['name'],
                brand=model_stat['brand'],
                sales_number=model_stat['sales_count']
            )
            result.append(model_sale_stats)
            
            print(f"   {i}. {model_stat['name']} ({model_stat['brand']}):")
            print(f"      Продаж: {model_stat['sales_count']}")
            print(f"      Средняя цена автомобиля: {model_stat['avg_price']:.2f}")
        
        if len(top_models) < 3:
            print(f"   Всего найдено только {len(top_models)} моделей с продажами")
        
        print(f"=== Анализ завершен ===")
        return result