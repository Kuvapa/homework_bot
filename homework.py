import logging
import os
import sys
import time
from http import HTTPStatus

import requests
import telegram
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
        logging.info('Сообщение в чат успешно отправлено')
    except Exception as TelegramError:
        sys.exc_info(TelegramError)


def get_api_answer(current_timestamp):
    """Получает запрос с API."""
    params = dict(url=ENDPOINT, headers=HEADERS,
                  params={'from_date': current_timestamp})
    try:
        response = requests.get(**params)
    except Exception as error:
        raise Exception(f'Ошибка при запросе {params}: {error}')
    if response.status_code != HTTPStatus.OK:
        raise ConnectionError('cайт недоступен')
    try:
        return response.json()
    except Exception as JSONDecodeError:
        raise Exception(f'Ошибка {JSONDecodeError}')


def check_response(response):
    """Проверяет корректность ответа API."""
    logging.info('Начало получение ответа от сервера')
    homework = response['homeworks']
    current_date = response['current_date']
    if not isinstance(response, dict):
        raise TypeError(f'Неверный формат данных {response}')
    if homework is None:
        raise KeyError(f'Такой ключ {homework} отстуствует на сервере')
    if current_date is None:
        raise KeyError(f'Такой ключ {current_date} отстуствует на сервере')
    if not isinstance(homework, list):
        raise TypeError(f'Неверный формат данных {homework}')
    return homework


def parse_status(homework):
    """Извелкает информацию о статусе домашки."""
    homework_name = homework['homework_name']
    homework_status = homework['status']
    if homework_name is None:
        raise KeyError(f'Запрашиваемый ключ {homework_name} '
                       f'имеет другое значение. Проверьте')
    if homework_status not in HOMEWORK_STATUSES:
        raise KeyError(f'Такого значения: {homework_status}, '
                       f'нет в списке {HOMEWORK_STATUSES}')
    verdict = HOMEWORK_STATUSES[homework_status]
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def check_tokens():
    """Проверяет наличие всех токенов."""
    return all([PRACTICUM_TOKEN and TELEGRAM_TOKEN and TELEGRAM_CHAT_ID])


def main():
    """Основная логика работы бота."""
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    current_timestamp = int(time.time())
    if check_tokens() is False:
        logging.critical(
            f'Отсутсвует один из элементов'
            f'{PRACTICUM_TOKEN, TELEGRAM_TOKEN, TELEGRAM_CHAT_ID}'
        )
        sys.exit(
            f'Отсутсвует один из элементов'
            f'{PRACTICUM_TOKEN, TELEGRAM_TOKEN, TELEGRAM_CHAT_ID}'
        )
    while True:
        try:
            response = get_api_answer(current_timestamp)
            current_timestamp = response.get('current_date',
                                             current_timestamp)
            homework = check_response(response)
            message = parse_status(homework[0])
            bot.send_message(TELEGRAM_CHAT_ID, message)
            time.sleep(RETRY_TIME)
        except Exception as errors:
            logging.error(f'Сбой в работе программы: {errors}')
            message = f'Сбой в работе программы: {errors}'
            bot.send_message(TELEGRAM_CHAT_ID, message)
            time.sleep(RETRY_TIME)


if __name__ == '__main__':
    logging.basicConfig(
        format=('%(asctime)s, %(levelname)s, %(funcName)s,'
                '%(lineno)d, %(name)s, %(message)s'),
        level=logging.INFO,
        handlers=[logging.StreamHandler(stream=sys.stdout)],
    )
    main()
