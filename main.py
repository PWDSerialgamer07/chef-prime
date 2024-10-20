import os
import discord
from discord.ext import commands
from discord import FFmpegPCMAudio
from dotenv import load_dotenv
import yt_dlp
import nacl
import re


load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')

# Create intents with voice states enabled
intents = discord.Intents.default()
intents.voice_states = True
intents.message_content = True

# Create bot instance with command prefix and make slash command tree
bot = commands.Bot(command_prefix=">", intents=intents)
# tree = bot.tree
loop_enabled = 0

# Other functions
song_queue = []


# for syncing slash commands
@bot.command(name="sync", description="Syncs the slash command tree with the bot.")
async def sync(ctx):
    app_info = await bot.application_info()
    owner_id = app_info.owner.id
    if ctx.author.id == owner_id:
        await bot.tree.sync()
        await ctx.send('Command tree synced.')
    else:
        await ctx.send('You must be the owner to use this command!')


@bot.event
async def on_ready():
    print(f'Bot connected as {bot.user}')
    print(f"Registered commands: {bot.commands}")
    try:
        await bot.sync_commands()
        print("Synced commands")
    except Exception as e:
        print(f"Error syncing commands: {e}")


@bot.slash_command(name="join", description="Tells the bot to join the voice channel.")
# @app_commands.describe(message="The message to echo.")
async def join(interaction: discord.Interaction) -> None:
    user = interaction.user

    if not user.voice:
        await interaction.response.send_message(f"{user.name} is not connected to a voice channel", ephemeral=False)
        return

    channel = user.voice.channel
    print(
        f"Received join command from {user.name}, connecting to {channel.name}")

    # Attempt to connect to the voice channel
    try:
        await channel.connect()
        await interaction.response.send_message(f"Connected to {channel.name}")
    except Exception as e:
        print(f"Error occurred while connecting to the voice channel: {e}")
        await interaction.followup.send(f"Failed to connect to {channel.name}: {e}", ephemeral=False)


@bot.slash_command(name="leave", description="Tells the bot to leave the voice channel.")
async def leave(interaction: discord.Interaction) -> None:
    guild = interaction.guild
    voice_client = guild.voice_client

    if voice_client and voice_client.is_connected():
        print("Received leave command, disconnecting from the voice channel")
        song_queue.clear()  # Assuming `song_queue` is defined elsewhere in your code
        await voice_client.disconnect()
        await interaction.response.send_message("Disconnected from the voice channel.")
    else:
        await interaction.response.send_message("The bot is not connected to a voice channel.", ephemeral=False)


@bot.slash_command(name="play", description="Plays a song from YouTube.")
async def play(interaction: discord.Interaction, url: str, timestamp: str = None) -> None:
    await interaction.response.defer()
    ffmpeg_options = {
        'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
        'options': '-vn'
    }
    ydl_opts = {'format': 'bestaudio'}
    print("Received play command")

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            song_info = ydl.extract_info(url, download=False)
            song_url = song_info["url"]
            song_title = song_info['title']

            if timestamp:
                converted_timestamp = convert_timestamp_to_seconds(timestamp)
                if converted_timestamp:
                    ffmpeg_options['before_options'] += f" -ss {converted_timestamp}"
                else:
                    ffmpeg_options['before_options'] += f" -ss {timestamp}"

            # Ensure the user is in a voice channel
            if interaction.user.voice:
                voice_channel = interaction.user.voice.channel
                voice = discord.utils.get(
                    bot.voice_clients, guild=interaction.guild)

                if voice and voice.is_connected():
                    await voice.move_to(voice_channel)
                else:
                    voice = await voice_channel.connect()

                # Check if the bot is already playing music
                if voice.is_playing():
                    song_queue.append(url)
                    await interaction.followup.send(f"**Added to queue:** {song_title}")
                else:
                    await interaction.followup.send(f"**Now playing:** {song_title}")
                    voice.play(discord.FFmpegPCMAudio(song_url, **ffmpeg_options),
                               after=lambda e: bot.loop.create_task(play_next(interaction)))

            else:
                await interaction.response.send_message("You need to be in a voice channel to play music!", ephemeral=False)

    except Exception as e:
        await interaction.response.send_message(f"Error: {str(e)}", ephemeral=False)


@bot.slash_command(name="stop", description="Stops the music but stays in the voice channel.")
async def stop(interaction: discord.Interaction) -> None:
    voice_client = interaction.guild.voice_client

    if voice_client and voice_client.is_playing():
        voice_client.stop()
        await interaction.response.send_message("**Music stopped.**")
    else:
        await interaction.response.send_message("**No music is currently playing, starting the next one.**")
        if song_queue:
            await play_next(interaction)


@bot.slash_command(name="skip", description="Skips the current song.")
async def skip(interaction: discord.Interaction) -> None:
    await interaction.response.defer()
    voice_client = interaction.guild.voice_client

    if voice_client and voice_client.is_playing() and song_queue:
        voice_client.stop()
        await interaction.followup.send("**Skipped**")
        await play_next(interaction)
    else:
        await interaction.followup.send("**No song is playing to skip.**", ephemeral=False)


@bot.slash_command(name="queue", description="Displays the current music queue.")
async def queue(interaction: discord.Interaction) -> None:
    print(song_queue)
    if song_queue:
        song_titles = []
        for song in song_queue:
            with yt_dlp.YoutubeDL({'format': 'bestaudio'}) as ydl:
                song_info = ydl.extract_info(song, download=False)
                song_titles.append(song_info['title'])

        await interaction.response.send_message("**Queue:**")
        await interaction.followup.send("\n".join(song_titles))
    else:
        await interaction.response.send_message("**No songs in queue.**", ephemeral=False)


@bot.slash_command(name="loop", description="Toggles looping of the current song.")
async def loop(interaction: discord.Interaction) -> None:
    global loop_enabled
    loop_enabled = not loop_enabled  # Toggle the loop state

    if loop_enabled:
        await interaction.response.send_message("**Looping enabled**")
    else:
        await interaction.response.send_message("**Looping disabled**")


@bot.slash_command(name="playlist", description="Plays a playlist from YouTube.")
async def playlist(interaction: discord.Interaction, url: str) -> None:
    ydl_opts = {
        'extract_flat': True,  # This avoids downloading the videos and extracts URLs only
        'skip_download': True,
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        result = ydl.extract_info(url, download=False)
        if 'entries' in result:
            playlist_title = result.get(
                'title', 'Jte baise fdp ta playlist a pas de titre')
            await interaction.response.send_message(f"**Playlist added:** {playlist_title}", ephemeral=False)
            for entry in result['entries']:
                song_queue.append(entry['url'])
                await play_next(interaction)
        else:
            await interaction.response.send_message("**Playlist unavailable.**", ephemeral=False)


async def play_next(interaction: discord.Interaction, l=0):
    if not song_queue:
        return
    # Ensure the bot is connected to the voice channel
    voice_channel = interaction.user.voice.channel
    voice = discord.utils.get(bot.voice_clients, guild=interaction.guild)
    if voice and voice.is_connected():
        await voice.move_to(voice_channel)
    else:
        voice = await voice_channel.connect()

    if loop_enabled and interaction.guild.voice_client.is_playing():
        # Get the current song that's playing
        current_song = song_queue[0] if song_queue else None

        if current_song:
            with yt_dlp.YoutubeDL({'format': 'bestaudio'}) as ydl:
                song_info = ydl.extract_info(current_song, download=False)
                song_title = song_info['title']
                await interaction.followup.send(f"**Looping song:** {song_title}")
                interaction.guild.voice_client.play(discord.FFmpegPCMAudio(
                    song_info["url"], options={'options': '-vn'}), after=lambda e: bot.loop.create_task(play_next(interaction)))
        return

    if song_queue:
        next_song = song_queue.pop(0)
        with yt_dlp.YoutubeDL({'format': 'bestaudio'}) as ydl:
            song_info = ydl.extract_info(next_song, download=False)
            song_title = song_info['title']
            await interaction.followup.send(f"**Now playing:** {song_title}")
            interaction.guild.voice_client.play(discord.FFmpegPCMAudio(
                song_info["url"], options={'options': '-vn'}), after=lambda e: bot.loop.create_task(play_next(interaction)))


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
        # If it doesn't match any format, return None
        return None


# Run the bot
bot.run(TOKEN)
