import os
import discord
from discord.ext import commands
from discord import FFmpegPCMAudio
from dotenv import load_dotenv

load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')

# Create intents with voice states enabled
intents = discord.Intents.default()
intents.voice_states = True
intents.message_content = True
bot = commands.Bot(command_prefix=">", intents=intents)


@bot.slash_command(name="join", description="Tells the bot to join the voice channel.")
async def join(interaction: discord.Interaction) -> None:
    user = interaction.user
    await interaction.response.defer()
    if not user.voice:
        await interaction.followup.send(f"{user.name} is not connected to a voice channel.", ephemeral=True)
        return

    channel = user.voice.channel

    await channel.connect()
    await interaction.followup.send(f"Connected to {channel.name}")
