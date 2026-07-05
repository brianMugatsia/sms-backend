from collections import OrderedDict
import threading


class IdempotencyCache:

    def __init__(self, max_size: int = 10000):
        self.cache = OrderedDict()
        self.lock = threading.Lock()
        self.max_size = max_size

    def exists(self, sms_id: str) -> bool:

        with self.lock:

            if sms_id in self.cache:
                self.cache.move_to_end(sms_id)
                return True

            return False

    def add(self, sms_id: str):

        with self.lock:

            self.cache[sms_id] = True
            self.cache.move_to_end(sms_id)

            while len(self.cache) > self.max_size:
                self.cache.popitem(last=False)


processed_sms = IdempotencyCache()