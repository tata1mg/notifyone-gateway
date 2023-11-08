from redis_wrapper.client import RedisCache


class UserCache(RedisCache):
    _key_prefix = "user"
    expire_time = 60 * 60

    @classmethod
    async def set_user(cls, key, value):
        return await cls.set(key, value, cls.expire_time)
