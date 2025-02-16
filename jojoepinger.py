import json
from collections import namedtuple
import requests
import redis
import discord
from cachetools import cached, TTLCache
import roll_player
from cards import Card

r = redis.Redis(host="localhost", port=6379, db=0, decode_responses=True)

PACEMAN_STATS_API = "https://paceman.gg/stats/api/"
PLAYER_DB_API = "https://playerdb.co/api/"

PlayerIdentifiers = namedtuple("PlayerIdentifiers", ["name", "uuid"])


def query_api(url: str, *endpoint: str, **params) -> requests.Response:
    url += "/".join(endpoint)
    return requests.get(url, params=params, timeout=10)


def update_player_list():
    response = query_api(
        PACEMAN_STATS_API,
        "getLeaderboard",
        category="nether",
        type="count",
        days=9999,
        limit=999999,
    )

    if response.status_code == 200:

        data = response.json()

        with open(
            "player_list.json",
            "w",
            encoding="utf-8",
        ) as file:
            json.dump(data, file, indent=4)

        with open(
            "player_list.json",
            "r",
            encoding="utf-8",
        ) as file:
            original_data = json.load(file)
            filtered_data = [
                {"uuid": item["uuid"], "name": item["name"]} for item in original_data
            ]
        
        r.delete("_player_list")

        for item in filtered_data:
            r.lpush("_player_list", json.dumps(item))

        em = discord.Embed(description="Updated player list", color=0)
        return em
    else:
        em = discord.Embed(description=f"Failed to fetch data: {response.status_code}")
        print(response.text)  # Print error details
        return em


def update_player_list_pbs():
    response = query_api(
        PACEMAN_STATS_API,
        "getLeaderboard",
        category="finish",
        type="fastest",
        days=9999,
        limit=999999,
    )

    if response.status_code == 200:

        data = response.json()

        with open(
            "player_list_pbs.json",
            "w",
            encoding="utf-8",
        ) as file:
            json.dump(data, file, indent=4)

        with open(
            "player_list_pbs.json",
            "r",
            encoding="utf-8",
        ) as file:
            original_data = json.load(file)
        #     filtered_data = [{'uuid': item['uuid'], 'name': item['name']} for item in original_data]

        for item in original_data:
            r.set(f"_player_pb_{item['uuid']}", json.dumps(item))

        em = discord.Embed(description="Updated players' PBs", color=0)
        return em
    else:
        em = discord.Embed(description=f"Failed to fetch data: {response.status_code}")
        print(response.text)  # Print error details
        return em


def get_random_player_name():
    return get_player_identifiers(roll_player.random_player())


# TODO: this doesnt all need to be cached since cards only use some of the data
@cached(TTLCache(ttl=86400, maxsize=2000))
def stats_from_name(name):
    data = query_api(
        PACEMAN_STATS_API,
        "getSessionStats",
        name=name,
        hours=999999,
        hoursBetween=999999,
    ).json()
    print(data)
    return data


def minutes_to_seconds(minutes_str):
    minutes, seconds = map(int, minutes_str.split(":"))
    return minutes * 60 + seconds


def get_player_pb(uuid_to_find):
    player_pb = r.get(f"_player_pb_{uuid_to_find}")
    if player_pb is None:
        return None
    player_pb = json.loads(player_pb)
    player_pb = player_pb["value"] / 1000.0
    return player_pb


@cached(TTLCache(ttl=86400, maxsize=2000))
def get_player_identifiers(uuid_or_name):
    response = query_api(PLAYER_DB_API, "player", "minecraft", uuid_or_name)
    if response.status_code == 200:
        data = response.json()
        return PlayerIdentifiers(
            data["data"]["player"]["username"], data["data"]["player"]["id"]
        )
    return PlayerIdentifiers(None, None)


def create_card(name, player_stats, uuid=None):
    player_name = name
    player_uuid = uuid
    if player_uuid is None:
        player_uuid = get_player_identifiers(player_name).uuid
    player_image = f"https://mc-heads.net/body/{player_name}"
    player_pb = get_player_pb(player_uuid)
    player_nea = minutes_to_seconds(player_stats["nether"]["avg"])
    player_fsa = minutes_to_seconds(player_stats["first_structure"]["avg"])
    player_ssa = minutes_to_seconds(player_stats["second_structure"]["avg"])
    player_fpa = minutes_to_seconds(player_stats["first_portal"]["avg"])
    player_sea = minutes_to_seconds(player_stats["stronghold"]["avg"])
    player_eea = minutes_to_seconds(player_stats["end"]["avg"])
    player_fa = minutes_to_seconds(player_stats["finish"]["avg"])
    card = Card(
        player_name,
        player_uuid,
        player_image,
        player_pb,
        player_nea,
        player_fsa,
        player_ssa,
        player_fpa,
        player_sea,
        player_eea,
        player_fa,
    )
    return card
