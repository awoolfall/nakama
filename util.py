from discord.channel import TextChannel, VoiceChannel
from discord.message import Message
from discord.player import FFmpegOpusAudio
from discord.voice_client import VoiceClient
from anime_apis import Anime, Theme
import discord
import asyncio
import os
import requests
import shutil
import functools
import typing

def to_thread(func: typing.Callable) -> typing.Coroutine:
	@functools.wraps(func)
	async def wrapper(*args, **kwargs):
		return await asyncio.to_thread(func, *args, **kwargs)
	return wrapper


@to_thread
def download_theme(url: str, file_loc: str):
	if not os.path.exists(file_loc):
		header = {"User-Agent":"NakamaDiscordBotUA"}
		with requests.get(url, headers=header, stream=True) as r:
			r.raise_for_status()
			with open(file_loc, 'wb') as f:
				shutil.copyfileobj(r.raw, f)


class Data:
	def __init__(self):
		self.voice_client: VoiceClient = None
		self.audio: FFmpegOpusAudio = None
		self.audio_anime_data: Anime = None
		self.audio_theme_data: Theme = None
		self.audio_location = None
		self.mal_animelist = None
		self.theme_quiz = None
	
	async def connect_voice(self, channel: VoiceChannel):
		await self.disconnect_voice()
		self.voice_client = await channel.connect()
		await self.voice_client.guild.change_voice_state(channel=self.voice_client.channel, self_deaf=True, self_mute=False)

	async def disconnect_voice(self):
		await self.unload_audio()
		if self.voice_client != None:
			await self.voice_client.disconnect()
			self.voice_client = None

	async def load_audio(self, file_loc: str, theme_data: Theme, anime_data: Anime):
		await self.unload_audio()
		self.audio_location = file_loc
		await self.reload_audio()
		self.audio_theme_data = theme_data
		self.audio_anime_data = anime_data

	async def reload_audio(self):
		if self.audio != None:
			self.audio.cleanup()
			self.audio = None
		self.audio = await FFmpegOpusAudio.from_probe(self.audio_location)

	async def unload_audio(self):
		if self.audio != None:
			self.audio.cleanup()
			self.audio = None
		self.audio_theme_data = None
		self.audio_anime_data = None


async def play_anime_theme(anime: Anime, theme: Theme, channel: TextChannel, voice_channel: VoiceChannel, data: Data) -> Message:
	# join channel
	if data.voice_client == None or data.voice_client.channel != voice_channel:
		await data.connect_voice(voice_channel)

	# download theme if required
	message: discord.Message = await channel.send("Downloading theme...")
	file_loc = 'temp/' + theme.basename
	try:
		await download_theme(theme.url, file_loc)
	except Exception as e:
		await channel.send("An error occured trying to download the theme :( [" + anime.name + " " + theme.slug + "]")
		return
	await message.edit(content="Finished downloading theme!")

	# play theme
	if data.voice_client.is_playing():
		data.voice_client.stop()
		await data.unload_audio()
	await data.load_audio(file_loc, theme, anime)
	data.voice_client.play(data.audio)

	return message

def create_anime_theme_embed(anime: Anime, theme: Theme) -> discord.Embed:
	e = discord.Embed()
	e.set_thumbnail(url=anime.image_url)
	e.title = anime.name if len(anime.name)>0 else 'N/A'
	e.url = anime.mal_url if len(anime.mal_url)>0 else None

	studios_text = ''
	if len(anime.studios) == 0:
		themes = anime.get_themes()
		if len(themes.studios) > 0:
			studios_text = ', '.join(themes.studios)
	else:
		studios_text = ', '.join(anime.studios)

	if len(studios_text) > 0:
		e.set_author(name=studios_text)

	genres_text = ''
	if len(anime.genres) == 0:
		genres_text = 'None?'
	else:
		genres_text = ', '.join(anime.genres)

	song_artists_text = ''
	if len(theme.song_artists) > 0:
		song_artists_text = ' by ' + ', '.join(theme.song_artists)
	if len(theme.song_name) > 0:
		e.add_field(name="Song", value=theme.song_name + song_artists_text, inline=False)

	e.add_field(name="Genres", value=genres_text, inline=False)
	e.add_field(name="Theme", value=theme.slug if len(theme.slug)>0 else 'N/A')
	e.add_field(name="Episodes", value=theme.episodes if len(theme.episodes)>0 else 'N/A')
	return e