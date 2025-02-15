import json
import requests
import redis
import discord
import roll_player
from cards import Card

r = redis.Redis(host="localhost", port=6379, db=0, decode_responses=True)

LEADERBOARD_ADRESS = "https://paceman.gg/stats/api/getLeaderboard?category=nether&type=count&days=9999&limit=999999"
PB_ADRESS = "https://paceman.gg/stats/api/getLeaderboard?category=finish&type=fastest&days=9999&limit=999999"
MC_PLAYERS_ADDRESS = "https://playerdb.co/api/player/minecraft/"


def update_player_list():
    response = requests.get(LEADERBOARD_ADRESS)

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

        for item in filtered_data:
            r.lpush("_player_list", json.dumps(item))

        em = discord.Embed(description="Updated player list", color=0)
        return em
    else:
        em = discord.Embed(description=f"Failed to fetch data: {response.status_code}")
        print(response.text)  # Print error details
        return em


def update_player_list_pbs():
    response = requests.get(PB_ADRESS)

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
    response = requests.get(
        f"https://playerdb.co/api/player/minecraft/{roll_player.random_player()}"
    )
    player_name = response.json()["data"]["player"]["username"]
    player_uuid = response.json()["data"]["player"]["id"]
    return player_name, player_uuid


def stats_from_name(name):
    response = requests.get(
        f"https://paceman.gg/stats/api/getSessionStats?name={name}&hours=999999&hoursBetween=999999"
    )
    data = response.json()
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


def get_player_uuid(name):
    response = requests.get(f"https://playerdb.co/api/player/minecraft/{name}")
    uuid = response.json()["data"]["player"]["id"]
    return uuid


def create_card(name, player_stats, uuid=None):
    player_name = name
    player_uuid = uuid
    if player_uuid is None:
        player_uuid = get_player_uuid(player_name)
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
