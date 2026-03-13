import time
import requests
import discord
from discord.ext import commands

TOKEN = "MTQ4MjAzNzE4Nzc5NjI3MTE0NA.Gm-L9I.gGlivlyPXtc-ZzQ-AU20RSZ_ngMzudYl_JfUzg"
LASTFM_API = "f2d8668834f742f202c65d9109cae19b"
REACTION_EMOJI_ID = 1482042315911463046

current_prefix = "!"
COOLDOWN_TIME = 5

intents = discord.Intents.default()
intents.message_content = True


def get_prefix(bot, message):
    return current_prefix


bot = commands.Bot(command_prefix=get_prefix, intents=intents)

users = {}       # discord user id -> last.fm username
words = {}       # trigger word -> discord user id
cooldowns = {}   # trigger word -> timestamp


@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")


@bot.command()
async def link(ctx, username: str):
    users[ctx.author.id] = username
    await ctx.send(f"🔗 Linked Last.fm account `{username}`")


@bot.command()
async def lfcc(ctx, trigger: str):
    trigger = trigger.lower().strip()
    words[trigger] = ctx.author.id
    await ctx.send(f"🎵 Your LFCC trigger word is now `{trigger}`")


@bot.command(name="prefix")
async def change_prefix(ctx, newprefix: str):
    global current_prefix
    current_prefix = newprefix
    await ctx.send(f"Prefix changed to `{current_prefix}`")


@bot.command()
async def unlink(ctx):
    users.pop(ctx.author.id, None)

    remove_words = [word for word, uid in words.items() if uid == ctx.author.id]
    for word in remove_words:
        words.pop(word, None)

    await ctx.send("❌ Removed your Last.fm link and trigger word")


@bot.event
async def on_message(message):
    if message.author.bot:
        return

    content = message.content.lower().strip()

    if content in words:
        now = time.time()

        if content in cooldowns and now - cooldowns[content] < COOLDOWN_TIME:
            await bot.process_commands(message)
            return

        cooldowns[content] = now
        user_id = words[content]

        if user_id not in users:
            await bot.process_commands(message)
            return

        username = users[user_id]

        url = (
            "https://ws.audioscrobbler.com/2.0/"
            f"?method=user.getrecenttracks&user={username}"
            f"&api_key={LASTFM_API}&format=json&limit=1"
        )

        try:
            response = requests.get(url, timeout=10)
            data = response.json()

            tracks = data.get("recenttracks", {}).get("track", [])
            if not tracks:
                await message.channel.send(f"No recent tracks found for **{username}**.")
                await bot.process_commands(message)
                return

            track = tracks[0]

            artist = track.get("artist", {}).get("#text", "Unknown Artist")
            song = track.get("name", "Unknown Track")
            album = track.get("album", {}).get("#text", "Unknown Album")

            images = track.get("image", [])
            image = images[-1].get("#text", "") if images else ""

            nowplaying = "@attr" in track and track["@attr"].get("nowplaying") == "true"

            embed = discord.Embed(
                title="🎧 Now Playing" if nowplaying else "Last Played",
                description=f"**{artist} — {song}**",
                color=0x1DB954
            )
            embed.add_field(name="Album", value=album or "Unknown", inline=True)
            embed.set_footer(text=username)

            if image:
                embed.set_thumbnail(url=image)

            sent_message = await message.channel.send(embed=embed)

            emoji = bot.get_emoji(REACTION_EMOJI_ID)
            if emoji:
                try:
                    await sent_message.add_reaction(emoji)
                except discord.HTTPException:
                    pass

            try:
                await message.delete()
            except discord.Forbidden:
                pass
            except discord.HTTPException:
                pass

        except Exception as e:
            print("Last.fm error:", e)
            await message.channel.send(f"Error getting Last.fm data for **{username}**.")

    await bot.process_commands(message)


bot.run(TOKEN)
