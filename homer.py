# -*- coding: utf-8 -*-
import asyncio
import functools
import os
import traceback

import discord
import youtube_dl
from discord.ext import commands
from discord.ext.commands import when_mentioned_or
from dotenv import load_dotenv

# Suppress noise about console usage from errors
youtube_dl.utils.bug_reports_message = lambda: ''

YTDL_OPTIONS = {
    'format': 'bestaudio/best',
    'extractaudio': True,
    'audioformat': 'mp3',
    'outtmpl': '%(extractor)s-%(id)s-%(title)s.%(ext)s',
    'restrictfilenames': True,
    'noplaylist': True,
    'nocheckcertificate': True,
    'ignoreerrors': False,
    'logtostderr': False,
    'quiet': True,
    'no_warnings': True,
    'default_search': 'auto',
    'source_address': '0.0.0.0',  # bind to ipv4 since ipv6 addresses cause issues sometimes
}


def debug(fn):
    @functools.wraps(fn)
    async def wrapped(*args, **kwargs):
        if __DEBUG_ENABLED is True:
            print(f'FUN [{fn.__name__}] {args} {kwargs}')

        return await fn(*args, **kwargs)

    return wrapped


class YTDLSource(discord.PCMVolumeTransformer):
    def __init__(self, source, *, data, volume=0.5):
        super().__init__(source, volume)

        self.data = data

        self.title = data.get('title')
        self.url = data.get('url')

    @classmethod
    async def from_url(cls, url, *, loop=None, stream=False):
        loop = loop or asyncio.get_event_loop()
        data = await loop.run_in_executor(None, lambda: ytdl.extract_info(url, download=not stream))

        if 'entries' in data:
            # take first item from a playlist
            data = data['entries'][0]

        filename = data['url'] if stream else ytdl.prepare_filename(data)

        return cls(await play_file(filename), data=data)


class TextCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name='join',
                      aliases=['summon'],
                      case_insensitive=True,
                      help='Joins the voice channel you\'re in.  Aliases=[summon].')
    @debug
    async def join(self, ctx, *, channel: discord.VoiceChannel = None):
        """
        Joins a voice channel.
        """
        await ctx.send('```Ok. I\'m on my way.```')

        if channel is None:
            try:
                channel = ctx.author.voice.channel
            except AttributeError:
                return await ctx.send('```No channel to join. Please either specify a valid channel or join one.```')

        print(f'Joins the voice channel #{channel.name}')

        await channel.connect()

    @commands.command(name='leave',
                      case_insensitive=True,
                      help='Leaves a voice channel.')
    @debug
    async def leave(self, ctx):
        """
        Leaves a voice channel.
        """
        await ctx.send('```Ok. I\'m leaving.```')

        if ctx.voice_client is None:
            return await ctx.send('```I\'m not connected to a voice channel.```')

        await ctx.voice_client.disconnect()

    @commands.command(name='play',
                      case_insensitive=True,
                      help='Plays audio from a url (doesn\'t pre-download).')
    @debug
    async def play(self, ctx, *, url):
        """
        Plays audio from a url (doesn't pre-download).
        """
        if ctx.voice_client is None:
            if ctx.author.voice:
                await ctx.author.voice.channel.connect()
            else:
                return await ctx.send("```You are not connected to a voice channel.```")

        async with ctx.typing():
            player = await YTDLSource.from_url(url, loop=self.bot.loop, stream=True)
            ctx.voice_client.play(player, after=lambda e: print(f'Player error: {e}') if e else None)

        await ctx.send(f'```Now playing: \'{player.title}\'```')

    @commands.command(name='stop',
                      aliases=['mute', 'shutup'],
                      case_insensitive=True,
                      help='Stops playing to voice. Aliases=[mute, shutup].')
    @debug
    async def stop(self, ctx):
        """
        Stops playing to voice.
        """
        if ctx.voice_client is None:
            return await ctx.send('```I\'m not connected to a voice channel.```')
        else:
            ctx.voice_client.stop()

    @commands.command(name='volume',
                      aliases=['vol'],
                      case_insensitive=True,
                      help='Changes the bot\'s volume. Aliases=[vol].')
    @debug
    async def volume(self, ctx, vol: int = None):
        """
        Changes the bot's volume.
        """
        if ctx.voice_client is None:
            return await ctx.send('```I\'m not connected to a voice channel.```')

        if vol is None:
            return await ctx.send(f'```My volume is [{ctx.voice_client.source.volume * 100}] now.```')

        ctx.voice_client.source.volume = vol / 100
        await ctx.send(f'```Changed my volume to {vol}```')

    @commands.command(name='pause',
                      case_insensitive=True,
                      help='Pauses the audio playing.')
    @debug
    async def pause(self, ctx):
        """
        Pauses the audio playing.
        """
        if ctx.voice_client is None:
            await ctx.send('```I\'m not connected to a voice channel.```')
            return

        ctx.voice_client.pause()
        await ctx.send(f'```Pause \'{ctx.voice_client.source.title}\'```')

    @commands.command(name='resume',
                      case_insensitive=True,
                      help='Resumes the audio playing.')
    @debug
    async def resume(self, ctx):
        """
        Resumes the audio playing.
        """
        if ctx.voice_client is None:
            await ctx.send('```I\'m not connected to a voice channel.```')
            return

        ctx.voice_client.resume()
        await ctx.send(f'``` Resume \'{ctx.voice_client.source.title}\'```')


@debug
async def play_file(filename):
    ffmpeg_options = {
        'options': '-vn',
    }

    return discord.FFmpegPCMAudio(filename, **ffmpeg_options)


class Homer(commands.Bot):
    def __init__(self, token, authorized_guild_id):
        super().__init__(command_prefix=when_mentioned_or('!homer '),
                         description='Exclusive bot for Donut Hole server.',
                         case_insensitive=True, )

        self.authorized_guild_id = authorized_guild_id

        self.add_cog(TextCommands(self))
        self.event(self.on_ready)
        self.event(self.on_command_error)
        self.event(self.on_voice_state_update)

        self.run(token)

    @debug
    async def on_ready(self):
        await self.__log_all_connected_guilds()

        guild = discord.utils.find(lambda g: str(g.id) == self.authorized_guild_id, self.guilds)
        if guild is None:
            raise RuntimeError(f'```guild [{self.authorized_guild_id}] not found in list of authorized guilds!```')

    async def on_command_error(self, ctx, error):
        traceback.print_exception(type(error), error, error.__traceback__)
        await ctx.send(f'```{error}```')

    @debug
    async def on_voice_state_update(self, member, before, after):

        # Don't react to bot own actions
        if member.id == self.user.id:
            return

        # Don't react to actions like 'self mute'
        if before.channel is not None \
                and after.channel is not None \
                and after.channel.id == before.channel.id:
            return

        if after.channel is not None \
                and not await self.__is_homer_in_this_channel(after.channel) \
                and not self.voice_clients:
            print(f'Joins {member.name} in the voice channel #{after.channel.name}')
            await after.channel.connect()
        elif after.channel is not None and await self.__is_homer_in_this_channel(after.channel):
            print(f'{member.name}(id: {member.id}) join me in #{after.channel.name}!')
            await self.__play_intro(after.channel, member.id)
        elif before.channel is not None and await self.__is_homer_in_this_channel(before.channel):
            await self.__leave_voice_if_alone(before.channel)

    async def __log_all_connected_guilds(self):
        print(f'{self.user} is connected to the following guilds:')
        for guild in self.guilds:
            print(f'- {guild.name}(id: {guild.id})')
        print(f'homer bot: {self.user.name}(id: {self.user.id})')
        print('_____________________________________________')

    async def __play_intro(self, channel, member_id):
        vc = discord.utils.find(lambda ch: ch.channel.id == channel.id, self.voice_clients)

        if vc is not None:
            resources_dir = os.path.dirname(__file__) + 'resources/'

            if member_id == 141471739258339328:  # Reif
                filename = os.path.join(resources_dir, 'DelRio.mp3')
            elif member_id == 94541638709293056:  # KIFFIR
                filename = os.path.join(resources_dir, 'Voices.mp3')
            else:
                filename = os.path.join(resources_dir, 'JohnCena.mp3')

            player = await play_file(filename)
            vc.play(player, after=lambda e: print(f'Player error: {e}') if e else None)

    async def __is_homer_in_this_channel(self, channel):
        return discord.utils.find(lambda m: m.id == self.user.id, channel.members) is not None

    async def __leave_voice_if_alone(self, channel):
        if len(channel.members) == 1:
            print(f'I\'m alone. I leave #{channel.name} too.')

            vc = discord.utils.find(lambda ch: ch.channel.id == channel.id, self.voice_clients)
            if vc is not None:
                await vc.disconnect()


if __name__ == '__main__':
    load_dotenv()
    __TOKEN = os.getenv('DISCORD_TOKEN')
    __AUTHORIZED_GUILD_ID = os.getenv('AUTHORIZED_GUILD_ID')
    __DEBUG_ENABLED = os.getenv('DEBUG_ENABLED')

    ytdl = youtube_dl.YoutubeDL(YTDL_OPTIONS)

    # According to the discord.py docs (https://discordpy.readthedocs.io/en/latest/api.html#discord.opus.load_opus)
    # you should not need it on a windows environnement,
    # which is why it worked on local machine and not on heroku (which is unix based).
    # 'nt' is the value for windows
    if os.name == 'nt' and discord.opus.is_loaded():
        discord.opus.load_opus('libopus.so')

    homer = Homer(__TOKEN, __AUTHORIZED_GUILD_ID)
