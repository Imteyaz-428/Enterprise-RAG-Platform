import json
import os

import redis

from dotenv import load_dotenv

load_dotenv()


class RedisService:

    def __init__(self):

        self.client = redis.Redis(
            host=os.getenv("REDIS_HOST"),
            port=int(os.getenv("REDIS_PORT")),
            decode_responses=True,
        )

    def get(
        self,
        key: str,
    ):

        value = self.client.get(key)

        if value is None:
            return None

        return json.loads(value)

    def set(
        self,
        key: str,
        value,
    ):

        self.client.setex(
            key,
            int(os.getenv("REDIS_EXPIRE")),
            json.dumps(value),
        )

    def delete(
        self,
        key: str,
    ):

        self.client.delete(key)