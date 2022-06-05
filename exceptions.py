class TelegramSendMessageError(Exception):
    """Ошибка отправки сообщения в телеграм."""

    pass


class CurrentDateKeyError(Exception):
    """Ошибка наличия ключа на сервере."""

    pass
