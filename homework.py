import logging
import os
import sys
import time
from http import HTTPStatus

import requests
import telegram
from telegram import TelegramError
from dotenv import load_dotenv

load_dotenv()


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
        logging.info(f'Сообщение в чат {TELEGRAM_CHAT_ID}: {message}')
    except TelegramError:
        raise TelegramError('Сообщение не отправлено по причине:',
                            sys.exc_info())


def get_api_answer(current_timestamp):
    """Получает запрос с API."""
    timestamp = current_timestamp or int(time.time())
    params = dict(url=ENDPOINT, headers=HEADERS,
                  params={'from_date': timestamp})
    try:
        response = requests.get(**params)
    except Exception as error:
        raise Exception(f'Ошибка при запросе {params}: {error}')
    if response.status_code != HTTPStatus.OK:
        raise ConnectionError('cайт недоступен')
    return response.json()


def check_response(response):
    """Проверяет корректность ответа API."""
    logging.info('Начало получение ответа от сервера')
    if not isinstance(response, dict):
        raise TypeError('Неверный формат данных')
    try:
        homework = response['homeworks']
    except KeyError:
        raise KeyError(f'Такой ключ {homework} отстуствует на сервере')
    try:
        current_date = response['current_date']
    except KeyError:
        raise KeyError(f'Такой ключ {current_date} отстуствует на сервере')
    if not isinstance(homework, list):
        raise TypeError('Неверный формат данных')
    return homework


def parse_status(homework):
    """Извелкает информацию о статусе домашки."""
    try:
        homework_name = homework['homework_name']
    except KeyError:
        raise KeyError('Запрашиваемый ключ имеет другое значение. Проверьте')
    try:
        homework_status = homework['status']
    except KeyError:
        raise KeyError('Запрашиваемый ключ имеет другое значение. Проверьте')
    if homework.get('homework_name') not in homework.get('homework_name'):
        raise KeyError('Работы с таким именем не обнаружено')
    if homework_status not in HOMEWORK_STATUSES:
        raise KeyError('Непредвиденный статус работы')
    verdict = HOMEWORK_STATUSES[homework_status]
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def check_tokens():
    """Проверяет наличие всех токенов."""
    try:
        if all([PRACTICUM_TOKEN and TELEGRAM_TOKEN and TELEGRAM_CHAT_ID]):
            return True
    except AttributeError:
        raise AttributeError(
            f'Отсутсвует один из элементов'
            f'{PRACTICUM_TOKEN, TELEGRAM_TOKEN, TELEGRAM_CHAT_ID}'
        )


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
            except Exception as errors:
                logging.error(f'Сбой в работе программы: {errors}')
                message = f'Сбой в работе программы: {errors}'
                bot.send_message(TELEGRAM_CHAT_ID, message)
                time.sleep(RETRY_TIME)
    else:
        logging.critical(
            f'Отсутсвует один из элементов'
            f'{PRACTICUM_TOKEN, TELEGRAM_TOKEN, TELEGRAM_CHAT_ID}'
        )
        sys.exit(
            f'Отсутсвует один из элементов'
            f'{PRACTICUM_TOKEN, TELEGRAM_TOKEN, TELEGRAM_CHAT_ID}'
        )


if __name__ == '__main__':
    logging.basicConfig(
        format=('%(asctime)s, %(levelname)s, %(funcName)s,'
                '%(lineno)d, %(name)s, %(message)s'),
        level=logging.INFO,
        handlers=[logging.StreamHandler(stream=sys.stdout)],
    )
    main()
