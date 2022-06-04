import logging
import os
import sys
import time
from http import HTTPStatus

import requests
import telegram
from dotenv import load_dotenv
from telegram import TelegramError

from exceptions import TelegramSendMessageError

load_dotenv()


PRACTICUM_TOKEN = os.getenv('yandex_token')
TELEGRAM_TOKEN = os.getenv('telegram_token')
TELEGRAM_CHAT_ID = os.getenv('chat_id')

RETRY_TIME = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}


HOMEWORK_VERDICTS = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}


def send_message(bot, message):
    """Отправляет сообщение о результатах ревью."""
    try:
        bot.send_message(TELEGRAM_CHAT_ID, message)
    except TelegramError:
        raise TelegramSendMessageError(
            'Произошла ошибка отправки сообщения, подробности: ',
            sys.exc_info()
        )
    else:
        logging.info('Сообщение в чат успешно отправлено')


def get_api_answer(current_timestamp):
    """Получает запрос с API."""
    params = dict(url=ENDPOINT, headers=HEADERS,
                  params={'from_date': current_timestamp})
    try:
        response = requests.get(**params)
        if response.status_code != HTTPStatus.OK:
            raise ConnectionError('cайт недоступен')
        return response.json()
    except Exception as error:
        raise Exception(f'Ошибка при запросе {params}: {error}')


def check_response(response):
    """Проверяет корректность ответа API."""
    logging.info('Начало получение ответа от сервера')
    if not isinstance(response, dict):
        raise TypeError(f'Неверный формат данных {response}')
    homework_list = response.get('homeworks')
    current_date = response.get('current_date')
    if homework_list is None:
        raise KeyError(f'Ключ {homework_list} либо отстуствует '
                       'на сервере, либо имеет другое значение или формат')
    if current_date is None:
        raise KeyError(f'Ключ {current_date} либо отстуствует '
                       'на сервере, либо имеет другое значение или формат')
    if not isinstance(homework_list, list):
        raise TypeError(f'Неверный формат данных {homework_list}')
    return homework_list


def parse_status(homework):
    """Извелкает информацию о статусе домашки."""
    homework_name = homework.get('homework_name')
    homework_status = homework.get('status')
    if homework_name is None:
        raise KeyError(f'Запрашиваемый ключ {homework_name} '
                       f'имеет другое значение. Проверьте')
    if homework_status not in HOMEWORK_VERDICTS:
        raise ValueError(f'Такого значения: {homework_status}, '
                         f'нет в списке {HOMEWORK_VERDICTS}')
    verdict = HOMEWORK_VERDICTS[homework_status]
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def check_tokens():
    """Проверяет наличие всех токенов."""
    return PRACTICUM_TOKEN and TELEGRAM_TOKEN and TELEGRAM_CHAT_ID


def main():
    """Основная логика работы бота."""
    critical_msg = ('Отсутсвует один из элементов '
                    f'{PRACTICUM_TOKEN, TELEGRAM_TOKEN, TELEGRAM_CHAT_ID}')
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    current_timestamp = int(time.time())
    if not check_tokens():
        logging.critical(critical_msg)
        sys.exit(critical_msg)
    while True:
        try:
            response = get_api_answer(current_timestamp)
            current_timestamp = response.get('current_date',
                                             current_timestamp)
            homework_list = check_response(response)
            if len(homework_list) > 0:
                message = parse_status(homework_list[0])
                bot.send_message(TELEGRAM_CHAT_ID, message)
        except TelegramError:
            logging.error(
                'Произошла ошибка отправки сообщения, подробности: ',
                exc_info=True
            )
        except KeyError:
            logging.error('Запрашиваемый ключ либо отстуствует на сервере, либо имеет другое значение или формат')
        except Exception as error:
            logging.error(f'Сбой в работе программы: {error}')
            message = (f'Сбой в работе программы: {error}')
            bot.send_message(TELEGRAM_CHAT_ID, message)
        finally:
            time.sleep(RETRY_TIME)


if __name__ == '__main__':
    logging.basicConfig(
        format=('%(asctime)s, %(levelname)s, %(funcName)s,'
                '%(lineno)d, %(name)s, %(message)s'),
        level=logging.INFO,
        handlers=[logging.StreamHandler(stream=sys.stdout)],
    )
    main()
