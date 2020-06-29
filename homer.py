# -*- coding: utf-8 -*-
import asyncio
import logging
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

log = logging.getLogger(__name__)


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

        await channel.connect()

    @commands.command(name='leave',
                      case_insensitive=True,
                      help='Leaves a voice channel.')
    async def leave(self, ctx):
        """
        Leaves a voice channel.
        """
        await ctx.send('```Ok. I\'m leaving.```')

        if ctx.voice_client is None:
            return await ctx.send('```I\'m not connected to a voice channel.```')

        ctx.voice_client.disconnect()

    @commands.command(name='play',
                      case_insensitive=True,
                      help='Plays audio from a url (doesn\'t pre-download).')
    async def stream(self, ctx, *, url):
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

        await ctx.send(f'```Now playing: {player.title}```')

    @commands.command(name='stop',
                      aliases=['mute', 'shutup'],
                      case_insensitive=True,
                      help='Stops playing to voice. Aliases=[mute, shutup].')
    async def stop(self, ctx):
        """
        Stops playing to voice.
        """
        if ctx.voice_client is None:
            return await ctx.send('```I\'m not connected to a voice channel.```')
        else:
            ctx.voice_client.stop()

    @commands.command(name='volume',
                      case_insensitive=True,
                      help='Changes the bot\'s volume.')
    async def volume(self, ctx, vol: int):
        """
        Changes the bot's volume.
        """
        if ctx.voice_client is None:
            return await ctx.send('```I\'m not connected to a voice channel.```')

        ctx.voice_client.source.volume = vol / 100
        await ctx.send(f'```Changed my volume to {vol}```')


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

    async def on_ready(self):
        await self.__log_all_connected_guilds()

        guild = discord.utils.find(lambda g: str(g.id) == self.authorized_guild_id, self.guilds)
        if guild is None:
            raise RuntimeError(f'```guild [{self.authorized_guild_id}] not found in list of authorized guilds!```')

    async def on_command_error(self, ctx, error):
        traceback.print_exception(type(error), error, error.__traceback__)
        await ctx.send(f'```{error}```')

    async def on_voice_state_update(self, member, before, after):
        if member.id == self.user.id:
            return

        if before.channel is not None \
                and after.channel is not None \
                and after.channel.id == before.channel.id:
            return

        if after.channel is not None and await self.__is_homer_in_this_channel(after.channel):
            print(f'{member.name} join me in #{after.channel}!')
            await self.__play_intro(after.channel)
        elif before.channel is not None and await self.__is_homer_in_this_channel(before.channel):
            await self.__leave_voice_if_alone(before.channel)

    async def __log_all_connected_guilds(self):
        print(f'{self.user} is connected to the following guilds:')
        for guild in self.guilds:
            print(f'- {guild.name}(id: {guild.id})\n')
        print(f'bot ID: {self.user.id}')
        print('_____________________________________________')

    async def __play_intro(self, channel):
        vc = discord.utils.find(lambda ch: ch.channel.id == channel.id, self.voice_clients)

        if vc is not None:
            filename = 'D:\\Python\\workspace\\homer-discord-bot\\resources'

            player = await play_file(filename)
            vc.play(player, after=lambda e: print(f'Player error: {e}') if e else None)

    async def __is_homer_in_this_channel(self, channel):
        return discord.utils.find(lambda m: m.id == self.user.id, channel.members) is not None

    async def __leave_voice_if_alone(self, channel):
        if len(channel.members) == 1:
            print(f'I\'m alone. I leave #{channel} too.')

            vc = discord.utils.find(lambda ch: ch.channel.id == channel.id, self.voice_clients)
            if vc is not None:
                await vc.disconnect()


if __name__ == '__main__':
    load_dotenv()
    __TOKEN = os.getenv('DISCORD_TOKEN')
    __AUTHORIZED_GUILD_ID = os.getenv('AUTHORIZED_GUILD_ID')

    ytdl = youtube_dl.YoutubeDL(YTDL_OPTIONS)

    homer = Homer(__TOKEN, __AUTHORIZED_GUILD_ID)
