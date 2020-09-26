import datetime


class Notifications(object):
    def __init__(self, sender, formatter):
        self.notification_sender = sender
        self.formatter = formatter

    def task_failed(self, task):
        self.notification_sender.send(self.formatter.task_failed(task))

    def message(self, message):
        self.notification_sender.send(self.formatter.message(message))


class NotificationFormat(object):
    def __init__(self, add_timestamp=True):
        self.add_timestamp = add_timestamp

    def task_failed(self, task):
        return self.message(self._get_task_failed_string(task))

    def message(self, message):
        if self.add_timestamp:
            now = self._get_current_time()
            message = self._prepend_timestamp_to_message(now, message)
        return message

    def _get_task_failed_string(self, task):
        return f"Task failed: {task}"

    def _get_current_time(self):
        return datetime.datetime.now()

    def _prepend_timestamp_to_message(self, time, message):
        return f"{time:%d.%m.%Y %H:%M} - {message}"
