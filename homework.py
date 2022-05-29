import logging
import os
import sys
import time
from http import HTTPStatus

import requests
import telegram
from dotenv import load_dotenv

load_dotenv()
logging.basicConfig(
    format='%(asctime)s, %(levelname)s, %(name)s, %(message)s',
    level=logging.INFO,
    filename='main.log',
    filemode='w',
)
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
handler = logging.StreamHandler(sys.stdout)
logger.addHandler(handler)
formatter = logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)

PRACTICUM_TOKEN = os.getenv('yandex_token')
TELEGRAM_TOKEN = os.getenv('telegram_token')
TELEGRAM_CHAT_ID = os.getenv('chat_id')

RETRY_TIME = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}


HOMEWORK_STATUSES = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}


def send_message(bot, message):
    """Отправляет сообщение о результатах ревью."""
    try:
        bot.send_message(TELEGRAM_CHAT_ID, message)
        logger.info(f'Сообщение в чат {TELEGRAM_CHAT_ID}: {message}')
    except Exception:
        logger.error('Сообщение не отправлено')


def get_api_answer(current_timestamp):
    """Получает запрос с API."""
    timestamp = current_timestamp or int(time.time())
    params = {'from_date': timestamp}
    try:
        response = requests.get(ENDPOINT, headers=HEADERS, params=params)
    except Exception as error:
        logger.error(f'Ошибка при запросе: {error}')
    if response.status_code != HTTPStatus.OK:
        logger.error('Сайт не доступен')
        raise ConnectionError('cайт недоступен')
    response = response.json()
    return response


def check_response(response):
    """Проверяет корректность ответа API."""
    if type(response) is not dict:
        logger.error('Неверный формат данных')
        raise TypeError('Неверный формат данных')
    try:
        homework = response.get('homeworks')
    except IndexError:
        logger.error('Пусто, нечего отправлять')
    if type(homework) is not list:
        logger.error('Неверный формат данных')
        raise TypeError('Неверный формат данных')
    return homework


def parse_status(homework):
    """Извелкает информацию о статусе домашки."""
    homework_name = homework['homework_name']
    homework_status = homework['status']
    if 'homework_name' not in homework:
        logger.error('Работы с таким именем не обнаружено')
        raise KeyError('Работы с таким именем не обнаружено')
    if homework_status not in HOMEWORK_STATUSES:
        logger.error('Непредвиденный статус работы')
        raise KeyError('Непредвиденный статус работы')
    verdict = HOMEWORK_STATUSES[homework_status]
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def check_tokens():
    """Проверяет наличие всех токенов."""
    try:
        if all([PRACTICUM_TOKEN, TELEGRAM_TOKEN, TELEGRAM_CHAT_ID]):
            return True
    except KeyError:
        logger.critical('Отсутсвует один из элементов')


def main():
    """Основная логика работы бота."""
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    current_timestamp = int(time.time())
    if check_tokens() is True:
        while True:
            try:
                response = get_api_answer(current_timestamp)
                current_timestamp = response.get('current_date')
                homework = check_response(response)
                message = parse_status(homework[0])
                bot.send_message(TELEGRAM_CHAT_ID, message)
                time.sleep(RETRY_TIME)
            except Exception as error:
                message = f'Сбой в работе программы: {error}'
                bot.send_message(TELEGRAM_CHAT_ID, message)
                time.sleep(RETRY_TIME)
    else:
        raise KeyError('Отсутсвует один из элементов')
        logger.critical('Отсутсвует один из элементов')


if __name__ == '__main__':
    main()
