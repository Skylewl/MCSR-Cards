import redis
import json
from random import randint
import random

random.seed()

r = redis.Redis(host="localhost", port=6379, db=0, decode_responses=True)


def random_player():
    random_index = randint(0, r.llen("_player_list") - 1)
    player = r.lrange("_player_list", random_index, random_index)
    player = json.loads(player[0])
    player_uuid = player["uuid"]
    return player_uuid
