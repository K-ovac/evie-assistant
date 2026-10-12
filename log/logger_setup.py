# logger_setup.py
import logging
import sys

def setup_logger():
    # Создаем базовый логгер
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)

    # Формат сообщений
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

    # Вывод в файл
    file_handler = logging.FileHandler('log/assistant.log', encoding='utf-8')
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    # Вывод в консоль
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    return logger