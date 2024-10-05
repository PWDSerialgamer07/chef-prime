import os
import discord
from discord.ext import commands
from discord import FFmpegPCMAudio
from dotenv import load_dotenv
import yt_dlp
import nacl


load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')

# Create intents with voice states enabled
intents = discord.Intents.default()
intents.voice_states = True
intents.message_content = True

# Create bot instance with command prefix
bot = commands.Bot(command_prefix=">", intents=intents)

# Other functions
song_queue = []


@bot.event
async def on_ready():
    print(f'Bot connected as {bot.user}')
    print(f"Registered commands: {bot.commands}")


@bot.command(name='join', help='Tells the bot to join the voice channel')
async def join(ctx):
    if not ctx.message.author.voice:
        await ctx.send(f"{ctx.message.author.name} is not connected to a voice channel")
        return

    channel = ctx.message.author.voice.channel
    print(
        f"Received join command from {ctx.message.author.name}, connecting to {channel.name}")

    # Attempt to connect to the voice channel
    try:
        await channel.connect()
    except Exception as e:
        print(f"Error occurred while connecting to the voice channel: {e}")


@bot.command(name='leave', help='Tells the bot to leave the voice channel')
async def leave(ctx):
    voice_client = ctx.message.guild.voice_client
    if voice_client and voice_client.is_connected():
        print("Received leave command, disconnecting from the voice channel")
        await voice_client.disconnect()
    else:
        await ctx.send("The bot is not connected to a voice channel.")


@bot.command(name="play", help="Plays a song from YouTube")
async def play(ctx, url):
    ffmpeg_options = {
        'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5', 'options': '-vn'}
    ydl_opts = {'format': 'bestaudio'}
    print("Received play command")

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            song_info = ydl.extract_info(url, download=False)
            song_url = song_info["url"]
            song_title = song_info['title']

            if ctx.author.voice:
                voice_channel = ctx.author.voice.channel
                voice = discord.utils.get(bot.voice_clients, guild=ctx.guild)

                if voice and voice.is_connected():
                    await voice.move_to(voice_channel)
                else:
                    voice = await voice_channel.connect()

                # Check if there's already something playing
                if voice.is_playing():
                    song_queue.append(url)
                    await ctx.send(f"**Added to queue:** {song_title}")
                else:
                    await ctx.send(f"**Now playing:** {song_title}")
                    ctx.voice_client.play(discord.FFmpegPCMAudio(
                        song_url, **ffmpeg_options), after=lambda e: bot.loop.create_task(play_next(ctx)))

            else:
                await ctx.send("You need to be in a voice channel to play music!")

    except Exception as e:
        await ctx.send(f"Error: {str(e)}")


@bot.command(name="stop", help="Stops the music but stays in the voice channel")
async def stop(ctx):
    if ctx.voice_client.is_playing():
        ctx.voice_client.stop()
        await ctx.send("**Music stopped.**")
    else:
        await ctx.send("**No music is currently playing, starting the next one.**")
        if song_queue:
            play_next(ctx)


@bot.command(name="skip", help="Skips the current song")
async def skip(ctx):
    if ctx.voice_client.is_playing() and song_queue:
        ctx.voice_client.stop()
        await ctx.send("**Skipped**")
        await play_next(ctx)  # Make sure to await the function
print("a")


@bot.command(name="queue", help="Displays the queue")
async def queue(ctx):
    print(song_queue)
    if song_queue:
        song_titles = []
        for song in song_queue:
            with yt_dlp.YoutubeDL({'format': 'bestaudio'}) as ydl:
                song_info = ydl.extract_info(song, download=False)
                song_titles.append(song_info['title'])
        await ctx.send("**Queue:**")
        await ctx.send("\n".join(song_titles))
    else:
        await ctx.send("**No songs in queue.**")


async def play_next(ctx):
    if song_queue:
        next_song = song_queue.pop(0)
        with yt_dlp.YoutubeDL({'format': 'bestaudio'}) as ydl:
            song_info = ydl.extract_info(next_song, download=False)
            song_title = song_info['title']
            await ctx.send(f"**Now playing:** {song_title}")
            ctx.voice_client.play(discord.FFmpegPCMAudio(
                song_info["url"], options={'options': '-vn'}), after=lambda e: bot.loop.create_task(play_next(ctx)))


# Run the bot
bot.run(TOKEN)
