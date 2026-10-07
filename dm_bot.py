# =========================================================
# RYNNX DM BOT — slash-only, user-installable
# =========================================================

import os
import re
import time
import random
import sqlite3
import asyncio
import aiohttp
from datetime import datetime

import discord
from discord import app_commands
from discord.ext import commands

# =========================================================
# TOKEN
# =========================================================

TOKEN = os.getenv("DISCORD_TOKEN_DM")

if not TOKEN:
    from dotenv import load_dotenv
    load_dotenv()
    TOKEN = os.getenv("DISCORD_TOKEN_DM")

if not TOKEN:
    raise RuntimeError("DISCORD_TOKEN_DM not found in environment or .env file.")

# =========================================================
# INTENTS + BOT
# =========================================================

intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.dm_messages = True

bot = commands.Bot(command_prefix="!", intents=intents, help_command=None)

# =========================================================
# DATABASE
# =========================================================

db = sqlite3.connect("dm_economy.db", check_same_thread=False)
cursor = db.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    wallet INTEGER DEFAULT 100,
    bank INTEGER DEFAULT 0,
    daily_claim REAL DEFAULT 0,
    work_claim REAL DEFAULT 0,
    luck INTEGER DEFAULT 50
)
""")
db.commit()


def get_user_econ(user_id):
    cursor.execute("SELECT wallet, bank, luck FROM users WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()
    if row is None:
        cursor.execute(
            "INSERT INTO users (user_id, wallet, bank, daily_claim, work_claim, luck) VALUES (?, 100, 0, 0, 0, 50)",
            (user_id,),
        )
        db.commit()
        return 100, 0, 50
    return row[0], row[1], row[2]


def update_wallet(user_id, amount):
    wallet, bank, luck = get_user_econ(user_id)
    cursor.execute("UPDATE users SET wallet = ? WHERE user_id = ?", (wallet + amount, user_id))
    db.commit()


# =========================================================
# GROQ AI
# =========================================================

try:
    from groq import Groq
    _groq_key = os.getenv("GROQ_API_KEY")
    groq_client = Groq(api_key=_groq_key) if _groq_key else None
except Exception:
    groq_client = None

_groq_history = {}

# =========================================================
# GIF URLS
# =========================================================

KISS_GIFS = [
    "https://media.giphy.com/media/v1.Y2lkPTc5MGI3NjExMXV3a29uZG05MjRmZml2czN2bDJvaWQxaDNkeHoyamMwYTZ1ZWU0aSZlcD12MV9naWZzX3NlYXJjaCZjdD1n/FgWNX7NK6SpzqwmOWe/giphy.gif",
    "https://media.giphy.com/media/v1.Y2lkPTc5MGI3NjExZWx3YTB2NTJyMmF6YXN0YWFybHRtNG44YzlhbHliZ2t4NGJzeDMweSZlcD12MV9naWZzX3NlYXJjaCZjdD1n/2fLX7xDEhleyubyBmv/giphy.gif",
    "https://media.giphy.com/media/v1.Y2lkPTc5MGI3NjExZWx3YTB2NTJyMmF6YXN0YWFybHRtNG44YzlhbHliZ2t4NGJzeDMweSZlcD12MV9naWZzX3NlYXJjaCZjdD1n/Mo122cd9G2xmKymanO/giphy.gif",
]

PAT_GIFS = [
    "https://media.giphy.com/media/v1.Y2lkPTc5MGI3NjExcDBuZWZkajg3cmw2cHA4dTZjcWo1aGFvMTFrem5mMm42cncwZnc5aSZlcD12MV9naWZzX3NlYXJjaCZjdD1n/ye7OTQgwmVuVy/giphy.gif",
    "https://media.giphy.com/media/v1.Y2lkPTc5MGI3NjExcDBuZWZkajg3cmw2cHA4dTZjcWo1aGFvMTFrem5mMm42cncwZnc5aSZlcD12MV9naWZzX3NlYXJjaCZjdD1n/AomVL3N8lTxiuYtI2I/giphy.gif",
]

SLAP_GIFS = [
    "https://media.giphy.com/media/v1.Y2lkPTc5MGI3NjExd3l6bm5qZ3B2cndnZjdpdnd1ZW5yM2JqcG5xemF5eWxsdnJ4bWJ3YiZlcD12MV9naWZzX3NlYXJjaCZjdD1n/Gf3AUz3eBNbTW/giphy.gif",
]

HUG_GIFS = [
    "https://media.giphy.com/media/v1.Y2lkPTc5MGI3NjExd2l6bm5qZ3B2cndnZjdpdnd1ZW5yM2JqcG5xemF5eWxsdnJ4bWJ3YiZlcD12MV9naWZzX3NlYXJjaCZjdD1n/od5H3PmEG5EVq/giphy.gif",
]

FAKE_NITRO_LINKS = [
    "https://discord.gift/abc123XYZdefGHI",
    "https://discord.gift/xK9mP2qL7nR4tY6w",
    "https://discord.gift/aB3cD5eF7gH9iJ1k",
]

RICKROLL_URL = "https://youtu.be/dQw4w9WgXcQ?si=nrcYlllvyK1He4Xb"

MEME_LIST = [
    "https://media.giphy.com/media/v1.Y2lkPTc5MGI3NjExZncyZ3YzanY3YmVqcDc2NzI0Zm1wNTloZnRmYmJxcTAyYXlkemlqYiZlcD12MV9naWZzX3NlYXJjaCZjdD1n/s5wFafpHxqKbIEERl9/giphy.gif",
    "https://media.giphy.com/media/1rPynGFeM7zcvMwm4k/giphy.gif",
]

PFPS = [
    "https://cdn.discordapp.com/attachments/1489131525743182008/1540485204093829200/7fe79c89936adbfbfdec5ae1dfff9a4b.png",
    "https://cdn.discordapp.com/attachments/1489131525743182008/1540484967937740830/8f27a0cc3a0f2781ad74efd4008558a9.png",
]

AFK_USERS = {}

# =========================================================
# DECORATOR — user-install + DM-compatible
# =========================================================

USER_INSTALL = app_commands.allowed_installs(guilds=True, users=True)
DM_CONTEXT = app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)


def dmsafe(func):
    """Combined decorator: works in guilds, DMs, and private channels; user-installable."""
    func = DM_CONTEXT(func)
    func = USER_INSTALL(func)
    return func


# =========================================================
# BASIC
# =========================================================

@bot.tree.command(name="ping", description="Check bot latency")
@dmsafe
async def ping(interaction: discord.Interaction):
    await interaction.response.send_message(f"🏓 Pong! `{round(bot.latency * 1000)}ms`")


@bot.tree.command(name="botinfo", description="Show bot info")
@dmsafe
async def botinfo(interaction: discord.Interaction):
    embed = discord.Embed(title="🤖 Rynnx DM Bot", color=discord.Color.blurple())
    embed.add_field(name="Servers", value=str(len(bot.guilds)), inline=True)
    embed.add_field(name="Users", value=str(len(bot.users)), inline=True)
    embed.add_field(name="Latency", value=f"{round(bot.latency * 1000)}ms", inline=True)
    embed.set_footer(text="Works in DMs and servers")
    await interaction.response.send_message(embed=embed)


@bot.tree.command(name="help", description="Show all commands")
@dmsafe
async def help_cmd(interaction: discord.Interaction):
    embed = discord.Embed(
        title="📋 Rynnx DM Bot Commands",
        description="All commands work in DMs and servers ✨",
        color=discord.Color.from_rgb(30, 31, 34),
    )
    embed.add_field(
        name="🎉 Fun",
        value="`kiss`, `pat`, `slap`, `hug`, `cf`, `8ball`, `pp`, `iq`, `gayrate`, `roast`, `memes`, `pfps`",
        inline=False,
    )
    embed.add_field(
        name="💰 Economy",
        value="`balance`, `daily`, `work`, `pay`, `deposit`, `withdraw`",
        inline=False,
    )
    embed.add_field(
        name="🔧 Utility",
        value="`ghostping`, `fakenitro`, `translate`, `languages`, `afk`, `chat`, `chatreset`, `ping`, `botinfo`",
        inline=False,
    )
    await interaction.response.send_message(embed=embed)


# =========================================================
# FUN / SOCIAL
# =========================================================

@bot.tree.command(name="kiss", description="Kiss another user")
@app_commands.describe(user="The user to kiss")
@dmsafe
async def kiss(interaction: discord.Interaction, user: discord.User):
    if user.id == interaction.user.id:
        embed = discord.Embed(description=f"😘 {interaction.user.mention} kisses themselves... okay!", color=discord.Color.orange())
        embed.set_image(url=random.choice(KISS_GIFS))
        return await interaction.response.send_message(embed=embed)
    if user.bot:
        return await interaction.response.send_message("❌ You can't kiss a bot!", ephemeral=True)
    embed = discord.Embed(
        description=f"💋 {interaction.user.mention} kisses {user.mention}! ❤️",
        color=discord.Color.from_rgb(255, 105, 180),
    )
    embed.set_image(url=random.choice(KISS_GIFS))
    await interaction.response.send_message(embed=embed)


@bot.tree.command(name="pat", description="Pat another user")
@app_commands.describe(user="The user to pat")
@dmsafe
async def pat(interaction: discord.Interaction, user: discord.User):
    if user.id == interaction.user.id:
        embed = discord.Embed(description="🫂 You pat yourself... that's kinda sad but okay!", color=discord.Color.orange())
        embed.set_image(url=random.choice(PAT_GIFS))
        return await interaction.response.send_message(embed=embed)
    embed = discord.Embed(
        description=f"🫳 {interaction.user.mention} pats {user.mention}!",
        color=discord.Color.from_rgb(255, 182, 193),
    )
    embed.set_image(url=random.choice(PAT_GIFS))
    await interaction.response.send_message(embed=embed)


@bot.tree.command(name="slap", description="Slap another user")
@app_commands.describe(user="The user to slap")
@dmsafe
async def slap(interaction: discord.Interaction, user: discord.User):
    if user.id == interaction.user.id:
        embed = discord.Embed(description=f"👋 {interaction.user.mention} slaps themselves...", color=discord.Color.orange())
        embed.set_image(url=random.choice(SLAP_GIFS))
        return await interaction.response.send_message(embed=embed)
    embed = discord.Embed(
        description=f"{interaction.user.mention} slaps {user.mention}!",
        color=discord.Color.from_rgb(255, 182, 193),
    )
    embed.set_image(url=random.choice(SLAP_GIFS))
    await interaction.response.send_message(embed=embed)


@bot.tree.command(name="hug", description="Hug another user")
@app_commands.describe(user="The user to hug")
@dmsafe
async def hug(interaction: discord.Interaction, user: discord.User):
    if user.id == interaction.user.id:
        embed = discord.Embed(description="🫂 You hug yourself... aww!", color=discord.Color.orange())
        embed.set_image(url=random.choice(HUG_GIFS))
        return await interaction.response.send_message(embed=embed)
    embed = discord.Embed(
        description=f"🤗 {interaction.user.mention} hugs {user.mention}!",
        color=discord.Color.from_rgb(255, 182, 193),
    )
    embed.set_image(url=random.choice(HUG_GIFS))
    await interaction.response.send_message(embed=embed)


@bot.tree.command(name="cf", description="Flip a coin")
@dmsafe
async def cf(interaction: discord.Interaction):
    result = random.choice(["HEADS", "TAILS"])
    embed = discord.Embed(title="-Coin Flip-", description=f"Coin landed on **{result}**!", color=discord.Color.gold())
    embed.set_footer(text=f"Flipped by: {interaction.user.display_name}", icon_url=interaction.user.display_avatar.url)
    await interaction.response.send_message(embed=embed)


@bot.tree.command(name="8ball", description="Ask the magic 8ball")
@app_commands.describe(question="Your question")
@dmsafe
async def eight_ball(interaction: discord.Interaction, question: str):
    responses = [
        "It is certain.", "It is decidedly so.", "Without a doubt.",
        "Yes definitely.", "You may rely on it.", "Most likely.",
        "Outlook good.", "Yes.", "Reply hazy, try again.",
        "Ask again later.", "Cannot predict now.", "Don't count on it.",
        "My reply is no.", "Outlook not so good.", "Very doubtful.",
    ]
    embed = discord.Embed(title="🎱 Magic 8-Ball", color=discord.Color.dark_purple())
    embed.add_field(name="Question", value=question, inline=False)
    embed.add_field(name="Answer", value=random.choice(responses), inline=False)
    await interaction.response.send_message(embed=embed)


@bot.tree.command(name="pp", description="Check someone's pp size")
@app_commands.describe(user="Target user (defaults to you)")
@dmsafe
async def pp(interaction: discord.Interaction, user: discord.User = None):
    target = user or interaction.user
    size = random.randint(0, 15)
    pp_display = f"8{'=' * size}D"
    embed = discord.Embed(description=f"🍆 **{target.display_name}'s PP size:**\n{pp_display}", color=discord.Color.blurple())
    await interaction.response.send_message(embed=embed)


@bot.tree.command(name="iq", description="Check someone's IQ")
@app_commands.describe(user="Target user (defaults to you)")
@dmsafe
async def iq(interaction: discord.Interaction, user: discord.User = None):
    target = user or interaction.user
    score = random.randint(40, 160)
    embed = discord.Embed(description=f"🧠 **{target.display_name}'s IQ:** {score}", color=discord.Color.blurple())
    await interaction.response.send_message(embed=embed)


@bot.tree.command(name="gayrate", description="Check someone's gay percentage")
@app_commands.describe(user="Target user (defaults to you)")
@dmsafe
async def gayrate(interaction: discord.Interaction, user: discord.User = None):
    target = user or interaction.user
    rate = random.randint(0, 100)
    embed = discord.Embed(
        description=f"🏳️‍🌈 **{target.display_name}** is **{rate}%** gay!",
        color=discord.Color.from_rgb(255, 105, 180),
    )
    await interaction.response.send_message(embed=embed)


@bot.tree.command(name="roast", description="Roast someone")
@app_commands.describe(user="Target user (defaults to you)")
@dmsafe
async def roast(interaction: discord.Interaction, user: discord.User = None):
    target = user or interaction.user
    roasts = [
        "Your comeback is still loading.",
        "You bring tutorial-level confidence to boss-level problems.",
        "I've seen loading screens with more personality.",
        "You have a talent for making simple things look advanced.",
        "You somehow manage to be confidently incorrect.",
        "Your Wi-Fi has better decision-making skills than you.",
    ]
    embed = discord.Embed(description=f"🔥 {target.mention} {random.choice(roasts)}", color=discord.Color.red())
    await interaction.response.send_message(embed=embed)


@bot.tree.command(name="memes", description="Get a random meme")
@dmsafe
async def memes(interaction: discord.Interaction):
    embed = discord.Embed(title="😂 Random Meme", color=discord.Color.blurple())
    embed.set_image(url=random.choice(MEME_LIST))
    await interaction.response.send_message(embed=embed)


@bot.tree.command(name="pfps", description="Get a random PFP")
@dmsafe
async def pfps(interaction: discord.Interaction):
    embed = discord.Embed(title="👀 Random PFP", color=discord.Color.from_rgb(220, 20, 60))
    embed.set_image(url=random.choice(PFPS))
    await interaction.response.send_message(embed=embed)


# =========================================================
# GHOSTPING
# =========================================================

@bot.tree.command(name="ghostping", description="Ghost ping a user")
@app_commands.describe(user="User to ghost ping", times="How many times (1-20)", message="Optional extra text")
@dmsafe
async def ghostping(interaction: discord.Interaction, user: discord.User, times: int = 1, message: str = ""):
    times = max(1, min(20, times))
    await interaction.response.send_message(f"👻 Ghost pinging {user.display_name} x{times}...", ephemeral=True)

    content = f"{user.mention} {message}".strip() or user.mention
    sent = 0
    for _ in range(times):
        try:
            msg = await interaction.channel.send(content)
            try:
                await msg.delete()
            except Exception:
                pass
            sent += 1
        except Exception:
            break
        await asyncio.sleep(1)

    try:
        await interaction.edit_original_response(content=f"✅ Ghost ping done: {sent}/{times}")
    except Exception:
        pass


# =========================================================
# FAKE NITRO
# =========================================================

@bot.tree.command(name="fakenitro", description="Send a fake Nitro gift")
@app_commands.describe(user="Who 'gifted' it (defaults to you)")
@dmsafe
async def fakenitro(interaction: discord.Interaction, user: discord.User = None):
    recipient = user or interaction.user
    nitro_link = random.choice(FAKE_NITRO_LINKS)

    content = f"🎁 **{recipient.display_name}** just boosted the server!\n{nitro_link}"

    embed = discord.Embed(
        title="You've been gifted a subscription!",
        description=(
            f"**{recipient.display_name}** has gifted you **Nitro**!\n\n"
            "Click the button below to redeem your gift.\n"
            "-# This gift expires in 48 hours."
        ),
        color=0x5865F2,
    )
    embed.set_thumbnail(url="https://cdn.discordapp.com/emojis/949750669837475860.gif")

    view = discord.ui.View(timeout=None)
    view.add_item(discord.ui.Button(label="Redeem", emoji="🎁", style=discord.ButtonStyle.primary, url=RICKROLL_URL))

    try:
        await interaction.response.send_message(content=content, embed=embed, view=view)
    except Exception as e:
        await interaction.response.send_message(f"❌ Failed: `{str(e)[:150]}`", ephemeral=True)


# =========================================================
# TRANSLATE
# =========================================================

TRANSLATE_LANGS = {
    "en": "English", "es": "Spanish", "fr": "French", "de": "German",
    "it": "Italian", "pt": "Portuguese", "ru": "Russian", "ja": "Japanese",
    "ko": "Korean", "zh-CN": "Chinese (Simplified)", "ar": "Arabic",
    "hi": "Hindi", "nl": "Dutch", "pl": "Polish", "tr": "Turkish",
    "el": "Greek", "he": "Hebrew", "sv": "Swedish", "no": "Norwegian",
    "da": "Danish", "fi": "Finnish", "uk": "Ukrainian", "vi": "Vietnamese",
    "th": "Thai", "id": "Indonesian", "tl": "Filipino", "bn": "Bengali",
    "ur": "Urdu", "fa": "Persian", "ta": "Tamil", "te": "Telugu",
}

TRANSLATE_ALIASES = {v.lower(): k for k, v in TRANSLATE_LANGS.items()}
TRANSLATE_ALIASES.update({
    "chinese": "zh-CN", "mandarin": "zh-CN", "farsi": "fa", "tagalog": "tl",
})


def _resolve_lang(text):
    if not text:
        return None
    t = text.strip().lower()
    for code in TRANSLATE_LANGS:
        if code.lower() == t:
            return code
    if t in TRANSLATE_ALIASES:
        return TRANSLATE_ALIASES[t]
    for alias, code in TRANSLATE_ALIASES.items():
        if t in alias or alias in t:
            return code
    return None


@bot.tree.command(name="translate", description="Translate text to another language")
@app_commands.describe(language="Target language (e.g. spanish, japanese, fr)", text="Text to translate")
@dmsafe
async def translate(interaction: discord.Interaction, language: str, text: str):
    if len(text) > 1500:
        return await interaction.response.send_message("❌ Text too long (max 1500 chars).", ephemeral=True)

    target_code = _resolve_lang(language)
    if not target_code:
        return await interaction.response.send_message(
            f"❌ Unknown language `{language}`. Try `spanish`, `japanese`, `fr`, etc.",
            ephemeral=True,
        )

    await interaction.response.defer()

    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(
                "https://translate.googleapis.com/translate_a/single",
                params={"client": "gtx", "sl": "auto", "tl": target_code, "dt": "t", "q": text},
                timeout=10,
                headers={"User-Agent": "Mozilla/5.0"},
            ) as resp:
                data = await resp.json()
        except Exception as e:
            return await interaction.followup.send(f"❌ Translate failed: `{str(e)[:100]}`")

    try:
        translated = "".join(seg[0] for seg in data[0] if seg and seg[0])
    except Exception:
        translated = None

    if not translated:
        return await interaction.followup.send("❌ Couldn't translate that.")

    embed = discord.Embed(title="🌐 Translation", color=discord.Color.blurple())
    embed.add_field(name="📝 Original", value=text[:1024], inline=False)
    embed.add_field(name="✅ Translated", value=translated[:1024], inline=False)
    embed.set_footer(text=f"Target: {TRANSLATE_LANGS.get(target_code, target_code)}")
    await interaction.followup.send(embed=embed)


@bot.tree.command(name="languages", description="List supported translation languages")
@dmsafe
async def languages(interaction: discord.Interaction):
    common = " • ".join(f"{v} (`{k}`)" for k, v in list(TRANSLATE_LANGS.items())[:24])
    embed = discord.Embed(
        title="🌐 Supported Languages",
        description=f"{common}\n\n…and more. Just type the language name!",
        color=discord.Color.blurple(),
    )
    await interaction.response.send_message(embed=embed, ephemeral=True)


# =========================================================
# ECONOMY
# =========================================================

@bot.tree.command(name="balance", description="Check your balance")
@app_commands.describe(user="Target user (defaults to you)")
@dmsafe
async def balance(interaction: discord.Interaction, user: discord.User = None):
    target = user or interaction.user
    wallet, bank, luck = get_user_econ(target.id)
    embed = discord.Embed(color=discord.Color.from_rgb(88, 101, 242))
    embed.set_author(name=target.display_name, icon_url=target.display_avatar.url)
    embed.title = "Balance"
    embed.add_field(name="Wallet", value=f"🪙 {wallet:,}", inline=True)
    embed.add_field(name="Bank", value=f"🪙 {bank:,}", inline=True)
    embed.add_field(name="Net", value=f"🪙 {wallet + bank:,}", inline=False)
    await interaction.response.send_message(embed=embed)


@bot.tree.command(name="daily", description="Claim your daily reward")
@dmsafe
async def daily(interaction: discord.Interaction):
    user_id = interaction.user.id
    cursor.execute("SELECT daily_claim FROM users WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()
    now = time.time()
    if row and now - row[0] < 86400:
        remaining = int(86400 - (now - row[0]))
        h, m = remaining // 3600, (remaining % 3600) // 60
        return await interaction.response.send_message(f"⏳ Already claimed. Try again in **{h}h {m}m**.", ephemeral=True)

    reward = 500
    update_wallet(user_id, reward)
    cursor.execute("UPDATE users SET daily_claim = ? WHERE user_id = ?", (now, user_id))
    db.commit()
    await interaction.response.send_message(f"💸 Claimed daily reward of **${reward:,}**!")


@bot.tree.command(name="work", description="Work to earn cash")
@dmsafe
async def work(interaction: discord.Interaction):
    user_id = interaction.user.id
    cursor.execute("SELECT work_claim FROM users WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()
    now = time.time()
    if row and now - row[0] < 60:
        remaining = int(60 - (now - row[0]))
        return await interaction.response.send_message(f"⏳ Rest for **{remaining}s** before working again.", ephemeral=True)

    earned = random.randint(100, 350)
    update_wallet(user_id, earned)
    cursor.execute("UPDATE users SET work_claim = ? WHERE user_id = ?", (now, user_id))
    db.commit()
    await interaction.response.send_message(f"💼 You worked and earned **${earned:,}**!")


@bot.tree.command(name="pay", description="Pay another user")
@app_commands.describe(user="User to pay", amount="Amount to send")
@dmsafe
async def pay(interaction: discord.Interaction, user: discord.User, amount: int):
    if user.id == interaction.user.id:
        return await interaction.response.send_message("❌ You can't pay yourself.", ephemeral=True)
    if amount <= 0:
        return await interaction.response.send_message("❌ Amount must be > 0.", ephemeral=True)

    wallet, _, _ = get_user_econ(interaction.user.id)
    if wallet < amount:
        return await interaction.response.send_message("❌ Not enough money in wallet.", ephemeral=True)

    update_wallet(interaction.user.id, -amount)
    update_wallet(user.id, amount)
    await interaction.response.send_message(f"💸 Paid **${amount:,}** to {user.mention}!")


@bot.tree.command(name="deposit", description="Deposit money into your bank")
@app_commands.describe(amount="Amount to deposit (or 'all')")
@dmsafe
async def deposit(interaction: discord.Interaction, amount: str):
    user_id = interaction.user.id
    wallet, bank, _ = get_user_econ(user_id)

    if amount.lower() == "all":
        val = wallet
    else:
        try:
            val = int(amount)
        except ValueError:
            return await interaction.response.send_message("❌ Invalid amount.", ephemeral=True)

    if val <= 0:
        return await interaction.response.send_message("❌ Amount must be > 0.", ephemeral=True)
    if wallet < val:
        return await interaction.response.send_message("❌ Not enough money in wallet.", ephemeral=True)

    cursor.execute("UPDATE users SET wallet = wallet - ?, bank = bank + ? WHERE user_id = ?", (val, val, user_id))
    db.commit()
    await interaction.response.send_message(f"🏦 Deposited **${val:,}**.")


@bot.tree.command(name="withdraw", description="Withdraw money from your bank")
@app_commands.describe(amount="Amount to withdraw (or 'all')")
@dmsafe
async def withdraw(interaction: discord.Interaction, amount: str):
    user_id = interaction.user.id
    wallet, bank, _ = get_user_econ(user_id)

    if amount.lower() == "all":
        val = bank
    else:
        try:
            val = int(amount)
        except ValueError:
            return await interaction.response.send_message("❌ Invalid amount.", ephemeral=True)

    if val <= 0:
        return await interaction.response.send_message("❌ Amount must be > 0.", ephemeral=True)
    if bank < val:
        return await interaction.response.send_message("❌ Not enough money in bank.", ephemeral=True)

    cursor.execute("UPDATE users SET wallet = wallet + ?, bank = bank - ? WHERE user_id = ?", (val, val, user_id))
    db.commit()
    await interaction.response.send_message(f"🏦 Withdrew **{val:,}**.")


# =========================================================
# AFK
# =========================================================

@bot.tree.command(name="afk", description="Set your AFK status")
@app_commands.describe(reason="Why you're AFK")
@dmsafe
async def afk(interaction: discord.Interaction, reason: str = "AFK"):
    AFK_USERS[interaction.user.id] = {"reason": reason, "time": time.time()}
    embed = discord.Embed(title="AFK Set!", description=f"You are now AFK: **{reason}**", color=discord.Color.blue())
    await interaction.response.send_message(embed=embed)


# =========================================================
# AI CHAT
# =========================================================

@bot.tree.command(name="chat", description="Chat with the AI")
@app_commands.describe(message="Your message to the AI")
@dmsafe
async def chat(interaction: discord.Interaction, message: str):
    if groq_client is None:
        return await interaction.response.send_message("❌ AI is not configured on this bot.", ephemeral=True)

    await interaction.response.defer()

    hist = _groq_history.setdefault(interaction.channel.id, [])
    hist.append({"role": "user", "content": message})
    hist[:] = hist[-20:]

    try:
        res = groq_client.chat.completions.create(
            model="openai/gpt-oss-120b",
            messages=[{"role": "system", "content": "You are a helpful Discord assistant. Keep replies short."}] + hist,
            max_tokens=1024,
        )
        reply = res.choices[0].message.content.strip() or "(no reply)"
    except Exception as e:
        return await interaction.followup.send(f"❌ AI error: `{str(e)[:150]}`")

    hist.append({"role": "assistant", "content": reply})
    hist[:] = hist[-20:]

    for i in range(0, len(reply), 1900):
        await interaction.followup.send(reply[i:i + 1900])


@bot.tree.command(name="chatreset", description="Reset your AI chat history")
@dmsafe
async def chatreset(interaction: discord.Interaction):
    _groq_history.pop(interaction.channel.id, None)
    await interaction.response.send_message("🧹 Cleared.", ephemeral=True)


# =========================================================
# EVENTS
# =========================================================

@bot.event
async def on_ready():
    print(f"✅ DM Bot logged in as {bot.user}")
    print(f"📡 Connected to {len(bot.guilds)} servers")

    try:
        synced = await bot.tree.sync()
        print(f"🔄 Synced {len(synced)} slash commands")
    except Exception as e:
        print(f"⚠️ Sync failed: {e}")

    await bot.change_presence(
        activity=discord.Activity(
            type=discord.ActivityType.listening,
            name="DMs | /help",
        )
    )


# =========================================================
# RUN
# =========================================================

if __name__ == "__main__":
    bot.run(TOKEN)
