import os
import discord
from discord.ext import commands
from discord import FFmpegPCMAudio
from dotenv import load_dotenv
import yt_dlp
import nacl
import re
from libs import *
import asyncio

load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')

# Create intents with voice states enabled
intents = discord.Intents.default()
intents.voice_states = True
intents.message_content = True

# Create bot instance with command prefix and make slash command tree
bot = commands.Bot(command_prefix=">", intents=intents)
# initialize logger
logger = Logger()
log_printer = logger.LogPrint(logger)
# temp folder for downloading audios
temp_folder = "temp"
os.makedirs(temp_folder, exist_ok=True)
downloaded_file_path = None  # Variable to store the file path
# ffmpeg and ytdlp options
ffmpeg_options = {
    'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
    'options': '-vn'
}
ydl_opts = {
    'format': 'bestaudio',
    'outtmpl': os.path.join(temp_folder, '%(title)s.%(ext)s'),
}


class queue:
    """
    Queue class for storing video URLs and timestamps.
    Might be overengineered for nothing but eh
    """

    def __init__(self):
        self.queue = []

    def append(self, url, timestamp=0):
        """
        Adds an element to the queue.
        IMPORTANT: Timestamps are stored in seconds like "360" for 5 minutes instead of "00:05:00"
        """
        self.queue.append({"url": url, "timestamp": timestamp})

    def pop(self):
        """Removes and returns the first element from the queue."""
        if self.queue:
            return self.queue.pop(0)
        else:
            return None

    def display(self):
        """Returns the current queue as a formatted string."""
        if self.queue:
            # Create the formatted string for each video
            queue_str = "\n".join(
                [f"{index + 1}: URL: {video['url']}, Timestamp: {video['timestamp']}"
                 for index, video in enumerate(self.queue)])
            return queue_str
        else:
            return "Queue is empty"

    def is_empty(self):
        """To check if the queue is empty
        Returns True if the queue is empty, False if it contains something
        """
        return not self.queue


url_queue = queue()


@bot.command(name="sync", description="Syncs the slash command tree with the bot.")
async def sync(ctx):
    app_info = await bot.application_info()
    owner_id = app_info.owner.id
    if ctx.author.id == owner_id:
        await bot.sync_commands()
        await ctx.send('Command tree synced.')
    else:
        await ctx.send('You must be the owner to use this command!')


@bot.event
async def on_ready():
    log_printer.info(f"Bot connected as {bot.user}")
    log_printer.info(f"Registered commands: {bot.commands}")
    try:
        await bot.sync_commands()
        log_printer.info(f"Synced commands")
    except Exception as e:
        log_printer.error(f"Error syncing commands: {e}")


@bot.slash_command(name="join", description="Tells the bot to join the voice channel.")
async def join(interaction: discord.Interaction) -> None:
    user = interaction.user
    await interaction.response.defer()
    log_printer.info(f"Received join command from {user.name}")
    if not user.voice:
        await interaction.followup.send(f"{user.name} is not connected to a voice channel.", ephemeral=True)
        log_printer.error(f"{user.name} is not connected to a voice channel")
        return

    channel = user.voice.channel
    log_printer.info(f"Connecting to {channel.name}")

    try:
        await channel.connect()
        await interaction.followup.send(f"Connected to {channel.name}")
        log_printer.info(f"Connected to {channel.name}")
    except discord.errors.Forbidden:
        await interaction.followup.send("I do not have permission to join this voice channel.", ephemeral=True)
        log_printer.error(f"Permission error: Cannot join {channel.name}")
    except discord.errors.ClientException as e:
        await interaction.followup.send(f"Failed to connect: {e}", ephemeral=True)
        log_printer.error(f"Error connecting to {channel.name}: {e}")
    except Exception as e:
        await interaction.followup.send(f"Failed to connect to {channel.name}: {e}", ephemeral=True)
        log_printer.error(f"Unexpected error: {e}")


@bot.slash_command(name="play", description="Plays a song from YouTube.")
async def play(interaction: discord.Interaction, url: str, timestamp: str = None) -> None:
    await interaction.response.defer()
    log_printer.info(
        f"Received play command from {interaction.user.name} with URL: {url}")
    try:
        # Attempt to download and play the song
        timestamp = convert_timestamp_to_seconds(timestamp)
        print(url)
        url_queue.append(url, timestamp)
        await play_next(interaction)
    except yt_dlp.utils.DownloadError as e:
        await interaction.followup.send(f"Failed to download audio from the URL: {e}", ephemeral=True)
        log_printer.error(f"Download error: {e}")
    except Exception as e:
        await interaction.followup.send(f"An error occurred while trying to play the song: {e}", ephemeral=True)
        log_printer.error(f"Unexpected error in play command: {e}")


async def play_next(interaction: discord.Interaction, l=0):
    # Ensure the bot is connected to the voice channel
    voice_channel = interaction.user.voice.channel
    voice = discord.utils.get(bot.voice_clients, guild=interaction.guild)
    if voice and voice.is_connected():
        await voice.move_to(voice_channel)
    else:
        voice = await voice_channel.connect()
    if interaction.guild.voice_client.is_playing() or interaction.guild.voice_client.is_paused():
        # If something is already playing, do nothing
        return
    if url_queue.is_empty():  # If the queue is empty, return nothing
        return
    next_song = url_queue.pop()
    timestamp = next_song['timestamp']

    def on_download_complete(d):
        global downloaded_file_path
        downloaded_file_path = d['filename']  # Store the file path
        log_printer.info(f"Download complete! File saved to: {d['filename']}")

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.add_post_processor(on_download_complete)
        ydl.download(next_song['url'])
    if timestamp:
        converted_timestamp = convert_timestamp_to_seconds(timestamp)
        if converted_timestamp:
            ffmpeg_options['before_options'] += f" -ss {converted_timestamp}"
        else:
            ffmpeg_options['before_options'] += f" -ss {timestamp}"
    if downloaded_file_path:
        await voice.play(discord.FFmpegPCMAudio(downloaded_file_path, **ffmpeg_options),
                         after=lambda e: bot.loop.create_task(play_next(interaction)))


@bot.slash_command(name="playlist", description="Plays a playlist from YouTube.")
async def playlist(interaction: discord.Interaction, url: str) -> None:
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            result = ydl.extract_info(url, download=False)
            if 'entries' in result:
                playlist_title = result.get('title', 'Unnamed playlist')
                await interaction.response.send_message(f"**Playlist added:** {playlist_title}", ephemeral=False)
                log_printer.info(f"Playlist added: {playlist_title}")
                for entry in result['entries']:
                    try:
                        url_queue.append(entry['url'], 0)
                        await play_next(interaction)
                    except yt_dlp.utils.DownloadError:
                        await interaction.followup.send(f"**Skipped unavailable video:** {entry.get('title', 'Unknown title')}")
                        log_printer.warn(
                            f"**Skipped unavailable video:** {entry.get('title', 'Unknown title')}")
            else:
                await interaction.response.send_message("**Playlist unavailable.**", ephemeral=False)
                log_printer.error("Playlist unavailable")

    except yt_dlp.utils.DownloadError as e:
        await interaction.response.send_message(f"**Error retrieving playlist:** {str(e)}", ephemeral=False)
        log_printer.error(f"Error retrieving playlist: {str(e)}")


def convert_timestamp_to_seconds(timestamp):
    # Regular expression patterns for "HH:MM:SS", "MM:SS", and "SS"
    pattern_hms = r"^\d{1,2}:\d{2}:\d{2}$"  # HH:MM:SS
    pattern_ms = r"^\d{1,2}:\d{2}$"         # MM:SS
    pattern_s = r"^\d{1,2}$"                # SS

    if re.match(pattern_hms, timestamp):
        # Split and convert "HH:MM:SS"
        parts = timestamp.split(":")
        hours = int(parts[0])
        minutes = int(parts[1])
        seconds = int(parts[2])
        total_seconds = hours * 3600 + minutes * 60 + seconds
        return total_seconds

    elif re.match(pattern_ms, timestamp):
        # Split and convert "MM:SS"
        parts = timestamp.split(":")
        minutes = int(parts[0])
        seconds = int(parts[1])
        total_seconds = minutes * 60 + seconds
        return total_seconds

    elif re.match(pattern_s, timestamp):
        # Convert "SS"
        seconds = int(timestamp)
        return seconds

    else:
        # If it doesn't match any format, return 0
        return "0"


bot.run(TOKEN)
