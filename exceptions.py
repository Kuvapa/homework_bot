class TelegramSendMessageError(Exception):
    """Ошибка отправки сообщения в телеграм."""

    pass


class CurrentDateKeyError(KeyError):
    """Ошибка наличия ключа на сервере."""

    pass
