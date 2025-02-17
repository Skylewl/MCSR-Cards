import logging
from time import gmtime, strftime, time
import random
from math import floor
from functools import partial
import json
import redis
import discord
from discord.ext import commands
import jojoepinger
from bot_token import TOKEN
from bot_token import TEST_BOT_TOKEN

r = redis.Redis(
    host="localhost", port=6379, db=0, decode_responses=True
)  # redis used as database
intents = (
    discord.Intents.default()
)  # specifies the intentions of the bot (send messages, etc.)
intents.message_content = True
intents.members = True
handler = logging.FileHandler(
    filename="discord.log", encoding="utf-8", mode="w"
)  # log file
bot = commands.Bot(command_prefix=["!", "$"], intents=intents)

# embed colors
dark_gray = discord.Color.from_rgb(31, 30, 30)
white = discord.Color.from_rgb(255, 255, 255)
green = discord.Color.from_rgb(20, 222, 30)
blue = discord.Color.from_rgb(20, 91, 222)
purple = discord.Color.from_rgb(134, 20, 222)
gold = discord.Color.from_rgb(255, 179, 0)
mythic = discord.Color.from_rgb(255, 66, 14)


@bot.event
async def on_ready():
    print(f"Logged in as {bot.user.name} - {bot.user.id}")


@bot.command(name="sync")
@commands.is_owner()
async def sync_commands(ctx):
    try:
        await bot.tree.sync()
        await ctx.reply("Commands synced!")
    except Exception as e:
        print(e)


@bot.command()
async def ping(ctx):
    await ctx.send("pong")


@bot.command(name="cooldown")
async def cooldown(ctx):
    em = cooldown_command(interaction=ctx)
    await ctx.send(embed=em)


@bot.tree.command(name="cooldown")
async def cooldown_tree(interaction: discord.Interaction):
    em = cooldown_command(interaction=interaction)
    await interaction.response.send_message(embed=em)


def cooldown_command(interaction):
    rolls_key = f"_u{interaction.author.id}_s{interaction.guild.id}_rolls"
    claims_key = f"_u{interaction.author.id}_s{interaction.guild.id}_claims"
    rolls_message = "All 10 rolls are available."
    claims_message = "All 3 claims are available."
    if r.exists(rolls_key):
        rolls = r.get(rolls_key)
        time_left = r.ttl(rolls_key)
        timestamp = floor(time() + int(time_left))
        rolls_message = (
            f"You have {10-int(rolls)} rolls available & all 10 reset <t:{timestamp}:R>"
        )
    if r.exists(claims_key):
        claims = r.get(claims_key)
        time_left = r.ttl(claims_key)
        timestamp = floor(time() + int(time_left))
        claims_message = (
            f"You have {3-int(claims)} claims available & all 3 reset <t:{timestamp}:R>"
        )
    em = discord.Embed(title="Cooldowns", color=0)
    em.add_field(name="Rolls", value=rolls_message, inline=False)
    em.add_field(name="Claims", value=claims_message, inline=False)
    return em


@bot.command(name="roll")
async def roll(ctx):
    em, view = roll_command(interaction=ctx)
    print("asdf")
    print(em)
    await ctx.send(embed=em, view=view)


@bot.tree.command(
    name="roll", description="Roll a random Minecraft speedrunner"
)  # MOST OF THESE TREE/SLASH COMMANDS ARE BROKEN BECAUSE OF CTX AND discord.Interaction HAVING DIFFERENT WAYS TO ACCESS USER ID (author.id vs user.id)
async def roll_tree(interaction: discord.Interaction):
    em, view = roll_command(interaction=interaction)
    await interaction.response.send_message(embed=em, view=view)


def roll_command(interaction):  # ROLL COMMAND
    rolls_key = f"_u{interaction.author.id}_s{interaction.guild.id}_rolls"  # roll cooldown logic
    if interaction.author.id == 238333085861675009:
        r.decr(rolls_key)
    rolls = r.get(rolls_key)
    if rolls is not None and int(rolls) >= 10:
        time_left = r.ttl(rolls_key)
        timestamp = floor(time() + int(time_left))
        em = discord.Embed(
            description=f"You used all 10 of your rolls, check back <t:{timestamp}:R>",
            color=0xE74C3C,
        )
        view = None
        return em, view

    new_rolls = r.incr(rolls_key)  # Increment roll count
    if new_rolls == 1:
        r.expire(rolls_key, 3600)  # Set expiry only on first roll

    for _ in range(10):
        player_name, player_uuid = jojoepinger.get_random_player_name()
        player_stats = jojoepinger.stats_from_name(player_name)
        if "error" in player_stats:
            continue
        break
    if "error" in player_stats:
        r.decr(rolls_key)
        em = discord.Embed(
            description="Something went wrong while trying to roll.", color=0xE74C3C
        )
        return em
    random_card = jojoepinger.create_card(player_name, player_stats, player_uuid)
    if random_card.value > 784:
        color = mythic
    elif random_card.value > 739:
        color = gold
    elif random_card.value > 649:
        color = purple
    elif random_card.value > 499:
        color = blue
    elif random_card.value > 399:
        color = green
    elif random_card.value > 149:
        color = white
    else:
        color = dark_gray
    em = discord.Embed(
        title=f"{random_card.name}",
        url=f"https://paceman.gg/stats/player/{random_card.name}",
        color=color,
    )
    if random_card.pb == 0:
        em.add_field(name="**Paceman PB**", value="No PB", inline=False)
    else:
        em.add_field(
            name="**Paceman PB**",
            value=f'{strftime("**%M:%S**", gmtime(random_card.pb))}',
            inline=False,
        )
    em.set_image(url=random_card.image)
    if f"{random_card.uuid}" not in r.lrange(
        f"_s{interaction.guild.id}_claimed_cards", 0, -1
    ):
        em.set_footer(
            text=f"Emeralds: {random_card.value}",
            icon_url="https://static.wikia.nocookie.net/minecraft_gamepedia/images/2/26/Emerald_JE3_BE3.png",
        )
        button = discord.ui.Button(label="Claim", style=discord.ButtonStyle.green)

        async def button_callback(interaction: discord.Interaction, card):
            if f"{str(card.uuid)}" in r.lrange(
                f"_s{interaction.guild.id}_claimed_cards", 0, -1
            ):
                return

            claims_key = f"_u{interaction.user.id}_s{interaction.guild.id}_claims"

            claims = r.get(claims_key)
            if claims is not None and int(claims) >= 3:
                time_left = r.ttl(claims_key)
                timestamp = floor(time() + int(time_left))
                em = discord.Embed(
                    description=f"You used all 3 of your claims this hour, check back <t:{timestamp}:R>",
                    color=0xE74C3C,
                )
                await interaction.response.send_message(embed=em)
                return

            # Increment claim count
            new_claims = r.incr(claims_key)
            if new_claims == 1:
                r.expire(claims_key, 3600)  # Set expiry only on first claim

            button.disabled = True
            button.label = "Claimed"
            button.style = discord.ButtonStyle.secondary
            r.lpush(
                f"_s{interaction.guild.id}_claimed_cards", f"{str(card.uuid)}"
            )  # set card as claimed in the server
            if interaction.guild.id == 314080405084962826:
                r.lpush(
                    f"_u{interaction.user.id}_s{interaction.guild.id}_cards",
                    str(card.uuid),
                )
                # r.lpush(
                #      f"_u{interaction.user.id}_s{interaction.guild.id}_cardsandvalue", json.dumps({"uuid": str(card.uuid), "value": int(card.value)})
                # )
            else:
                r.lpush(
                    f"_u{interaction.user.id}_s{interaction.guild.id}_cards",
                    str(card.uuid),
                )  # set card in users collection
            r.set(
                f"_c{str(card.uuid)}_s{interaction.guild.id}", f"{interaction.user.id}"
            )  # set user to card
            await interaction.response.send_message(
                f"{interaction.user.mention} claimed: [{card.name}](<https://paceman.gg/stats/player/{card.name}>)!"
            )
            await interaction.message.edit(view=view)

    else:
        owner = r.get(f"_c{random_card.uuid}_s{interaction.guild.id}")
        user = interaction.guild.get_member(int(owner))
        em.set_footer(
            text=f"Emeralds: {random_card.value} | Owned by {user}",
            icon_url="https://static.wikia.nocookie.net/minecraft_gamepedia/images/2/26/Emerald_JE3_BE3.png",
        )
        button = discord.ui.Button(
            label="Claimed", style=discord.ButtonStyle.secondary, disabled=True
        )
        view = discord.ui.View()

        async def button_callback(
            interaction: discord.Interaction,
        ):
            return

        button.callback = partial(button_callback)
        view.add_item(button)
        return em, view

    view = discord.ui.View()
    button.callback = partial(button_callback, card=random_card)
    view.add_item(button)
    return em, view


@bot.command(name="player", aliases=["card", "runner"])
async def show_player_command(ctx, name: str):
    em = show_player(interaction=ctx, name=name)
    await ctx.send(embed=em)


@bot.tree.command(name="player")
async def show_player_tree_command(interaction: discord.Interaction, name: str):
    em = show_player(interaction, name)
    await interaction.response.send_message(embed=em)


def show_player(interaction, name: str):  # SHOW PLAYER COMMAND
    try:
        player_stats = jojoepinger.stats_from_name(name)
        if not player_stats:
            em = discord.Embed(
                description="Something went wrong trying to find that player.",
                color=0xE74C3C,
            )
            return em
        response_name = jojoepinger.get_player_identifiers(name).name
        if response_name is not None:
            name = response_name
        player = jojoepinger.create_card(name, player_stats)
        if player.value > 784:
            color = mythic
        elif player.value > 739:
            color = gold
        elif player.value > 649:
            color = purple
        elif player.value > 499:
            color = blue
        elif player.value > 399:
            color = green
        elif player.value > 149:
            color = white
        else:
            color = dark_gray
        em = discord.Embed(
            title=f"{player.name}",
            url=f"https://paceman.gg/stats/player/{player.name}",
            description="Paceman stats",
            color=color,
        )
        if player.pb == 0:
            em.add_field(name="**Paceman PB**", value="No PB", inline=False)
        else:
            em.add_field(
                name="**Paceman PB**",
                value=f'{strftime("**%M:%S**", gmtime(player.pb))}',
                inline=False,
            )
        em.add_field(
            name="Enter average",
            value=f'{strftime("%M:%S", gmtime(player.nea))}',
            inline=False,
        )
        em.add_field(
            name="Second structure average",
            value=f'{strftime("%M:%S", gmtime(player.ssa))}',
            inline=False,
        )
        em.add_field(
            name="First portal average",
            value=f'{strftime("%M:%S", gmtime(player.fpa))}',
            inline=False,
        )
        em.set_image(url=player.image)
        if f"{player.uuid}" not in r.lrange(
            f"_s{interaction.guild.id}_claimed_cards", 0, -1
        ):
            em.set_footer(
                text=f"Emeralds: {player.value}",
                icon_url="https://static.wikia.nocookie.net/minecraft_gamepedia/images/2/26/Emerald_JE3_BE3.png",
            )
        else:
            owner = r.get(f"_c{player.uuid}_s{interaction.guild.id}")
            user = interaction.guild.get_member(int(owner))
            em.set_footer(
                text=f"Emeralds: {player.value} | Owned by {user}",
                icon_url="https://static.wikia.nocookie.net/minecraft_gamepedia/images/2/26/Emerald_JE3_BE3.png",
            )
        return em
    except Exception as e:
        em = discord.Embed(
            description="Something went wrong trying to find that player.",
            color=0xE74C3C,
        )
        with open("discord.log", "a", encoding="utf-8") as f:
            f.write(str(e))
            f.close()
        return em


@bot.command(name="collection", aliases=["cards"])
async def collection_command(ctx, member: discord.Member = None):
    em = show_collection(interaction=ctx, member=member)
    await ctx.send(embed=em)


@bot.tree.command(name="collection")
async def collection_tree_command(
    interaction: discord.Interaction, member: discord.Member | None
):
    em = show_collection(interaction=interaction, member=member)
    await interaction.response.send_message(embed=em)


def show_collection(interaction, member=None):
    if member is None:
        member = interaction.author
    if interaction.guild.id == 314080405084962826:
        if r.lrange(f"_u{interaction.author.id}_s{interaction.guild.id}_cards", 0, -1):
            em = recalculate_emeralds(interaction=interaction)
            return em
        bottom_index = 0
        top_index = -1
        collection_list = r.lrange(
            f"_u{member.id}_s{interaction.guild.id}_cardsandvalue",
            bottom_index,
            top_index,
        )
        new_collection_list = {}
        for item in collection_list:
            data = json.loads(item)  # Convert JSON string to Python dict
            uuid = data["uuid"]
            value = data["value"]

            player_name = ignore_underscore(
                jojoepinger.get_player_identifiers(uuid).name
            )  # Assuming this function exists
            new_collection_list[
                player_name
            ] = value  # Store in dict with player name as key

        collection_list_names = "\n".join(
            f"# {key}          ‎" for key, value in new_collection_list.items()
        )
        collection_list_values = "\n".join(
            f"# <:emerald:1340876788934643815> {value}"
            for key, value in new_collection_list.items()
        )
        net_worth_sum = 0
        for key, value in new_collection_list.items():
            net_worth_sum += value
        em = discord.Embed(title=f"{member}'s Collection", color=green)
        em.add_field(name="Player", value=collection_list_names, inline=True)
        em.add_field(name="Emeralds", value=collection_list_values, inline=True)
        em.set_footer(
            text=f"Net worth: {net_worth_sum}",
            icon_url="https://static.wikia.nocookie.net/minecraft_gamepedia/images/2/26/Emerald_JE3_BE3.png",
        )
        return em

    if member is None:
        member = interaction.author
    bottom_index = 0
    top_index = -1
    collection_list = r.lrange(
        f"_u{member.id}_s{interaction.guild.id}_cards", bottom_index, top_index
    )
    if not collection_list:
        em = discord.Embed(description="Collection does not have any cards.", color=0)
        return em
    new_collection_list = []
    for uuid in collection_list:
        new_collection_list.append(
            ignore_underscore(jojoepinger.get_player_identifiers(uuid).name)
        )
    new_collection_list = "\n".join(f"- {item}" for item in new_collection_list)
    em = discord.Embed(
        title=f"{member}'s Collection", description=f"{new_collection_list}", color=0
    )
    print(new_collection_list)
    return em


def ignore_underscore(s: str):
    return s.replace("_", r"\_")


@bot.command(name="delete", aliases=["remove", "deletecard", "removecard", "dc"])
async def delete_card_command(ctx, player_name):
    em = delete_card(interaction=ctx, player_uuid_or_name=player_name)
    await ctx.send(embed=em)


@bot.tree.command(name="delete")
async def delete_card_tree_command(interaction: discord.Interaction, player_name: str):
    em = delete_card(interaction=interaction, player_uuid_or_name=player_name)
    await interaction.response.send_message(embed=em)


def delete_card(interaction, player_uuid_or_name):
    player_name, player_uuid = jojoepinger.get_player_identifiers(player_uuid_or_name)
    items = r.lrange(f"_u{interaction.author.id}_s{interaction.guild.id}_cards", 0, -1)
    if player_uuid in items:
        r.lrem(
            f"_u{interaction.author.id}_s{interaction.guild.id}_cards",
            count=1,
            value=player_uuid,
        )
        r.lrem(f"_s{interaction.guild.id}_claimed_cards", count=1, value=player_uuid)
        r.delete(f"_c{player_uuid}_s{interaction.guild.id}", f"{interaction.author.id}")
        em = discord.Embed(
            description=f"Deleted {ignore_underscore(player_name)} from your collection",
            color=0,
        )
    else:
        em = discord.Embed(
            description="Something went wrong trying to delete that player from your collection",
            color=0,
        )
    return em


@bot.command(name="trade")
async def trade_card_command(ctx, member: discord.Member, player_one, player_two=None):
    em, view = trade_card(
        interaction=ctx, member=member, player_one=player_one, player_two=player_two
    )
    await ctx.send(embed=em, view=view)


@bot.tree.command(name="trade")
async def trade_card_tree_command(
    interaction: discord.Interaction,
    member: discord.Member,
    your_player: str,
    their_player: str | None,
):
    em, view = trade_card(
        interaction=interaction,
        member=member,
        player_one=your_player,
        player_two=their_player,
    )
    await interaction.response.send_message(embed=em, view=view)


def trade_card(interaction, member, player_one, player_two=None):
    trade_offerer_id = interaction.author.id
    trade_acceptor_id = member.id

    name_one, uuid_one = jojoepinger.get_player_identifiers(player_one)
    if uuid_one is not None:
        collection_one = r.lrange(
            f"_u{trade_offerer_id}_s{interaction.guild.id}_cards", 0, -1
        )
        if uuid_one not in collection_one:
            em = discord.Embed(description="You don't have that player", color=0)
            return em, None
    else:
        em = discord.Embed(description="Couldn't find player one", color=0)
        return em, None

    if player_two is not None:
        name_two, uuid_two = jojoepinger.get_player_identifiers(player_two)
        if uuid_two is not None:
            collection_two = r.lrange(
                f"_u{trade_acceptor_id}_s{interaction.guild.id}_cards", 0, -1
            )

            if uuid_two not in collection_two:
                em = discord.Embed(description="They don't have that player", color=0)
                return em, None

            async def button_callback(interaction: discord.Interaction):
                if interaction.user.id is trade_acceptor_id:
                    collection_one = r.lrange(
                        f"_u{trade_offerer_id}_s{interaction.guild.id}_cards", 0, -1
                    )  # check collection again on button press
                    if uuid_one in collection_one:
                        collection_two = r.lrange(
                            f"_u{trade_acceptor_id}_s{interaction.guild.id}_cards",
                            0,
                            -1,
                        )
                        if uuid_two in collection_two:
                            await interaction.response.defer()
                            r.lrem(
                                f"_u{trade_acceptor_id}_s{interaction.guild.id}_cards",
                                count=1,
                                value=uuid_two,
                            )  # delete acceptor's player
                            r.delete(
                                f"_c{uuid_two}_s{interaction.guild.id}",
                                f"{trade_acceptor_id}",
                            )

                            r.lrem(
                                f"_u{trade_offerer_id}_s{interaction.guild.id}_cards",
                                count=1,
                                value=uuid_one,
                            )  # delete OP's player
                            r.delete(
                                f"_c{uuid_one}_s{interaction.guild.id}",
                                f"{trade_offerer_id}",
                            )

                            r.lpush(
                                f"_u{trade_acceptor_id}_s{interaction.guild.id}_cards",
                                uuid_one,
                            )  # add acceptor's player
                            r.set(
                                f"_c{uuid_one}_s{interaction.guild.id}",
                                f"{trade_acceptor_id}",
                            )

                            r.lpush(
                                f"_u{trade_offerer_id}_s{interaction.guild.id}_cards",
                                uuid_two,
                            )  # add OP's player
                            r.set(
                                f"_c{uuid_two}_s{interaction.guild.id}",
                                f"{trade_offerer_id}",
                            )

                            button.disabled = True
                            button.label = "Accepted"
                            button.style = discord.ButtonStyle.secondary
                            em.color = green
                            em.title = f"{member.display_name} accepted {name_one} for {name_two}"
                            em.description = ""
                            await interaction.message.edit(embed=em, view=view)

        else:
            em = discord.Embed(description="Couldn't find player two", color=0)
            return em, None
        em = discord.Embed(
            title=f"Trade offer for {member.display_name}",
            description=f"{interaction.author.display_name} wants to trade **{name_one}** for your **{name_two}**",
            color=gold,
        )

    if player_two is None:

        async def button_callback(interaction: discord.Interaction):
            await interaction.response.defer()
            if interaction.user.id is trade_acceptor_id:
                collection_one = r.lrange(
                    f"_u{trade_offerer_id}_s{interaction.guild.id}_cards", 0, -1
                )  # check collection again on button press
                if uuid_one in collection_one:
                    r.lrem(
                        f"_u{trade_offerer_id}_s{interaction.guild.id}_cards",
                        count=1,
                        value=uuid_one,
                    )  # delete OP's player
                    r.delete(
                        f"_c{uuid_one}_s{interaction.guild.id}", f"{trade_offerer_id}"
                    )

                    r.lpush(
                        f"_u{trade_acceptor_id}_s{interaction.guild.id}_cards", uuid_one
                    )  # add acceptor's player
                    r.set(
                        f"_c{uuid_one}_s{interaction.guild.id}", f"{trade_acceptor_id}"
                    )

                    button.disabled = True
                    button.label = "Accepted"
                    button.style = discord.ButtonStyle.secondary
                    em.color = green
                    em.title = f"{member.display_name} accepted {name_one}"
                    em.description = ""
                    await interaction.message.edit(embed=em, view=view)

        em = discord.Embed(
            title=f"Gift offer for {member.display_name}",
            description=f"{interaction.author.display_name} wants to give you **{name_one}**",
            color=gold,
        )

    button = discord.ui.Button(label="Accept Trade", style=discord.ButtonStyle.green)
    button.callback = partial(button_callback)
    view = discord.ui.View()
    view.add_item(button)
    return em, view


@bot.command(name="updatepbs", aliases=["upb"])
@commands.is_owner()
async def update_player_pbs_command(ctx):
    em = jojoepinger.update_player_list_pbs()
    await ctx.send(embed=em)


@bot.command(name="updateplayerlist", aliases=["upl"])
@commands.is_owner()
async def update_player_list_command(ctx):
    em = jojoepinger.update_player_list()
    await ctx.send(embed=em)


@bot.command(name="calcemeralds", aliases=["ce"])
@commands.is_owner()
async def calculate_emeralds_command(ctx):
    em = calculate_emeralds(interaction=ctx)
    await ctx.send(embed=em)


def calculate_emeralds(interaction):
    collection = r.lrange(
        f"_u{interaction.author.id}_s{interaction.guild.id}_cards", 0, -1
    )

    emerald_sum = 0
    for item in collection:
        card = json.loads(item)
        emerald_sum += card.get("value", 0)
    print(emerald_sum)
    em = discord.Embed(
        description=f"You have {emerald_sum} emeralds",
        color=green,
    )
    return em


@bot.command(name="rce")
@commands.is_owner()
async def recalculate_emeralds_command(ctx):
    em = recalculate_emeralds(interaction=ctx)
    await ctx.send(embed=em)


def recalculate_emeralds(interaction):  # for emerald reworks
    print("started recalculate_emeralds")
    collection = r.lrange(
        f"_u{interaction.author.id}_s{interaction.guild.id}_cards", 0, -1
    )
    new_collection = r.lrange(
        f"_u{interaction.author.id}_s{interaction.guild.id}_cardsandvalue", 0, -1
    )
    for i in collection:
        if i not in new_collection:
            name = jojoepinger.get_player_identifiers(i)
            player_stats = jojoepinger.stats_from_name(name)
            card = jojoepinger.create_card(name=name, player_stats=player_stats, uuid=i)
            r.lpush(
                f"_u{interaction.author.id}_s{interaction.guild.id}_cardsandvalue",
                json.dumps({"uuid": card.uuid, "value": card.value}),
            )
    new_collection = r.lrange(
        f"_u{interaction.author.id}_s{interaction.guild.id}_cardsandvalue", 0, -1
    )
    r.delete(f"_u{interaction.author.id}_s{interaction.guild.id}_cards")
    print(new_collection)
    em = discord.Embed(description="recalculated, use the collection command again")
    return em


try:
    bot.run(TOKEN, log_handler=handler, log_level=20)
except Exception as e:
    print(e)
