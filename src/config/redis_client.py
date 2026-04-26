import redis.asyncio as r

from src.config.env import env


client = r.from_url(url=env.redis_url, decode_responses=True, socket_timeout=5)
