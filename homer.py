# -*- coding: utf-8 -*-
import asyncio
import datetime
import functools
import json
import os
import traceback
from typing import List, Dict, Optional

import discord
import youtube_dl
from discord.ext import commands
from discord.ext.commands import when_mentioned_or
from dotenv import load_dotenv

# Suppress noise about console usage from errors
youtube_dl.utils.bug_reports_message = lambda: ''


def debug_log(fn):
    @functools.wraps(fn)
    async def wrapped(*args, **kwargs):
        if __DEBUG_ENABLED == 'true':
            print(f'FUN [{fn.__name__}] {args} {kwargs}')

        return await fn(*args, **kwargs)

    return wrapped


class YTDLSource(discord.PCMVolumeTransformer):
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
        'source_address': '0.0.0.0',
    }
    FFMPEG_OPTIONS = {
        'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
        'options': '-vn'
    }

    ytdl = youtube_dl.YoutubeDL(YTDL_OPTIONS)

    def __init__(self, source, data: dict, volume: float = 0.5):
        super().__init__(source, volume)

        self.title = data.get('title')
        self.url = data.get('url')
        self.duration = datetime.timedelta(seconds=int(data.get('duration')))

    @classmethod
    async def create_source(cls, url: str, loop: asyncio.BaseEventLoop = None):
        loop = loop or asyncio.get_event_loop()
        data = await loop.run_in_executor(None, lambda: cls.ytdl.extract_info(url, download=False))

        return cls(create_audio_source(data['url'], ffmpeg_options=cls.FFMPEG_OPTIONS), data)


@debug_log
async def create_audio_source(source: str, ffmpeg_options: dict = None, volume: float = 0.5) -> discord.AudioSource:
    options = ffmpeg_options or {
        'options': '-vn'
    }

    return discord.PCMVolumeTransformer(
        discord.FFmpegPCMAudio(source, **options), volume)


class Homer(commands.Bot):
    def __init__(self, token: str, authorized_guilds: List[str], intros: Dict[str, dict]):
        super().__init__(command_prefix=when_mentioned_or('!homer '),
                         description='Exclusive bot for Donut Hole server.',
                         case_insensitive=True, )

        self.authorized_guilds = authorized_guilds
        self.intros = intros

        self.add_cog(TextCommands(self))
        self.event(self.on_ready)
        self.event(self.on_command_error)
        self.event(self.on_voice_state_update)

        self.run(token)

    @debug_log
    async def on_ready(self):
        await self.__log_all_connected_guilds()

        if self.authorized_guilds is not None:
            guild = discord.utils.find(lambda g: str(g.id) not in self.authorized_guilds, self.guilds)
            if guild is None:
                raise RuntimeError(f'```guild [{guild}] not found in list of authorized guilds!```')

    async def on_command_error(self, ctx: commands.Context, error):
        traceback.print_exception(type(error), error, error.__traceback__)
        await ctx.send(f'```{error}```')

    @debug_log
    async def on_voice_state_update(self, member, before, after):

        # Don't react to bot's actions
        if member.id == self.user.id or member.bot:
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

        # Someone has joined the channel the bot is currently in.
        if after.channel is not None \
                and await self.__is_homer_in_this_channel(after.channel):
            print(f'{member.name}(id: {member.id}) join me in #{after.channel.name}!')
            await self.__play_intro(after.channel, member.id)

        # Someone left the channel the bot is currently in.
        if before.channel is not None \
                and await self.__is_homer_in_this_channel(before.channel):
            await self.__leave_voice_if_alone(before.channel)

    async def __log_all_connected_guilds(self):
        print(f'{self.user} is connected to the following guilds:')
        for guild in self.guilds:
            print(f'- {guild.name}(id: {guild.id})')
        print(f'homer bot: {self.user.name}(id: {self.user.id})')
        print('_____________________________________________')

    async def __play_intro(self, channel: discord.VoiceChannel, member_id: str):
        vc = discord.utils.find(lambda ch: ch.channel.id == channel.id, self.voice_clients)

        if vc is not None and not vc.is_playing():
            filename: Optional[str] = await self.__get_intro_for_member(member_id)

            if filename is not None:
                vc.play(
                    await create_audio_source(filename),
                    after=lambda e: print(f'Player error: {e}') if e else None)
        else:
            print('I can\'t play intro, because I am already playing something.')

    async def __get_intro_for_member(self, member_id: str) -> Optional[str]:
        intro: Optional[dict] = self.intros.get(member_id)

        if intro is not None:
            return os.path.join(os.path.dirname(__file__), 'resources', 'intro', intro['file'])
        else:
            print(f'A member with id [{member_id}] does not have an intro.')
            return None

    async def __is_homer_in_this_channel(self, channel: discord.VoiceChannel) -> bool:
        return discord.utils.find(lambda m: m.id == self.user.id, channel.members) is not None

    async def __leave_voice_if_alone(self, channel: discord.VoiceChannel):
        if len(channel.members) == 1:
            print(f'I\'m alone. I leave #{channel.name} too.')

            vc = discord.utils.find(lambda ch: ch.channel.id == channel.id, self.voice_clients)
            if vc is not None:
                await vc.disconnect()


class TextCommands(commands.Cog):
    def __init__(self, bot: Homer):
        self.bot = bot

    def cog_check(self, ctx: commands.Context):
        if not ctx.guild:
            raise commands.NoPrivateMessage('Homer can\'t be used in DM channels.')
        return True

    @commands.command(name='join',
                      aliases=['summon', 'connect'],
                      case_insensitive=True,
                      help='Joins the voice channel you\'re in.')
    @debug_log
    async def join(self, ctx, channel: discord.VoiceChannel = None):
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
    @debug_log
    async def leave(self, ctx: commands.Context):
        """
        Leaves a voice channel.
        """
        await ctx.send('```Ok. I\'m leaving.```')
        await ctx.voice_client.disconnect()

    @commands.command(name='play',
                      case_insensitive=True,
                      help='Plays audio from a url (doesn\'t pre-download). \n '
                           'Supported sites: https://ytdl-org.github.io/youtube-dl/supportedsites.html')
    @debug_log
    async def play(self, ctx: commands.Context, url: str):
        """
        Plays audio from a url (doesn't pre-download).
        """
        if ctx.voice_client is None or not ctx.voice_client.is_connected():
            if ctx.author.voice:
                await ctx.author.voice.channel.connect()
            else:
                return await ctx.send('```You are not connected to a voice channel.```')

        async with ctx.typing():
            source = await YTDLSource.create_source(url, loop=self.bot.loop)
            ctx.voice_client.play(source, after=lambda e: print(f'Player error: {e}') if e else None)
            await self.now_playing(ctx)

    @commands.command(name='stop',
                      aliases=['mute', 'shutup'],
                      case_insensitive=True,
                      help='Stops playing to voice.')
    @debug_log
    async def stop(self, ctx: commands.Context):
        """
        Stops playing to voice.
        """
        ctx.voice_client.stop()

    @commands.command(name='volume',
                      aliases=['vol'],
                      case_insensitive=True,
                      help='Changes the bot\'s volume. \
If the command is called without an argument, the bot will respond with the current sound level.')
    @debug_log
    async def volume(self, ctx: commands.Context, vol: int = None):
        """
        Changes the bot's volume.
        """
        if vol is None:
            return await ctx.send(f'```My volume is [{int(ctx.voice_client.source.volume * 100)}/100] now.```')

        if not 0 < vol < 101:
            return await ctx.send('```Please enter a value between 1 and 100.```')

        ctx.voice_client.source.volume = vol / 100
        await ctx.send(f'```Changed my volume to {vol}```')

    @commands.command(name='pause',
                      case_insensitive=True,
                      help='Pauses the audio playing.')
    @debug_log
    async def pause(self, ctx: commands.Context):
        """
        Pauses the audio playing.
        """
        ctx.voice_client.pause()
        await ctx.send(f'```Pause \'{ctx.voice_client.source.title}\'```')

    @commands.command(name='resume',
                      case_insensitive=True,
                      help='Resumes the audio playing.')
    @debug_log
    async def resume(self, ctx: commands.Context):
        """
        Resumes the audio playing.
        """
        ctx.voice_client.resume()
        await ctx.send(f'``` Resume \'{ctx.voice_client.source.title}\'```')

    @commands.command(name='now_playing',
                      aliases=['np', 'current', 'current-song', 'playing'],
                      help='Display information about the currently playing song.')
    @debug_log
    async def now_playing(self, ctx: commands.Context):
        """
        Display information about the currently playing song.
        """
        await ctx.send(f'''```Now Playing: \'{ctx.voice_client.source.title}\'
duration: [{ctx.voice_client.source.duration}]```''')

    @leave.before_invoke
    @stop.before_invoke
    @now_playing.before_invoke
    @pause.before_invoke
    @resume.before_invoke
    @volume.before_invoke
    async def __ensure_voice(self, ctx: commands.Context):
        if ctx.voice_client is None or not ctx.voice_client.is_connected():
            raise commands.CommandError('I\'m not connected to a voice channel.')

    @resume.before_invoke
    @pause.before_invoke
    @volume.before_invoke
    @now_playing.before_invoke
    @stop.before_invoke
    async def __ensure_playing(self, ctx: commands.Context):
        if ctx.voice_client is None or not ctx.voice_client.is_playing():
            raise commands.CommandError('I\'m not playing anything.')


def create_intros(env_name: str) -> Dict[str, dict]:
    result: Dict[str, dict] = {}

    env_value: Optional[str] = os.getenv(env_name)

    if env_value is not None:
        for intro in json.loads(env_value):
            result.update({intro['id']: intro})

    return result


if __name__ == '__main__':
    load_dotenv()

    __TOKEN: Optional[str] = os.getenv('DISCORD_TOKEN')
    __AUTHORIZED_GUILDS: Optional[List[str]] = os.getenv('AUTHORIZED_GUILDS')
    __DEBUG_ENABLED: Optional[bool] = os.getenv('DEBUG_ENABLED')
    __INTROS: Dict[str, dict] = create_intros('INTROS')

    # According to the discord.py docs (https://discordpy.readthedocs.io/en/latest/api.html#discord.opus.load_opus)
    # you should not need it on a windows environment,
    # which is why it worked on local machine and not on heroku (which is unix based).
    # 'nt' is the value for windows
    if os.name == 'nt' and discord.opus.is_loaded():
        discord.opus.load_opus('libopus.so')

    homer = Homer(__TOKEN, __AUTHORIZED_GUILDS, __INTROS)
