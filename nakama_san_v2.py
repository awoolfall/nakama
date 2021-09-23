# -- install --
# pip install jikanpy
# python3 -m pip install -U discord.py[voice]
# -------------
# -------------

import asyncio
from asyncio.tasks import sleep
import functools
import os
import random
import typing
import discord
from discord.ext.commands.converter import EmojiConverter
from discord.member import VoiceState
from discord.player import AudioSource, FFmpegOpusAudio
from discord.voice_client import VoiceClient, VoiceProtocol
from jikanpy import Jikan, APIException as JikanAPIException

from anime_apis import JikanApi, Anime, AnimeThemes, NoThemesForAnime, Theme

import logging
from discord import Client, Intents, Embed, file
from discord.channel import VoiceChannel
from discord_slash import SlashCommand, SlashContext

import requests
import shutil


logging.basicConfig(level=logging.INFO)	
bot = Client(command_prefix="`", intents = Intents.default())
slash = SlashCommand(bot, sync_commands=True, debug_guild=175865262866825216)

class Data:
	def __init__(self):
		self.voice_client: VoiceClient = None
		self.audio: FFmpegOpusAudio = None
		self.audio_anime_data: Anime = None
		self.audio_theme_data: Theme = None
		self.game = None
		self.mal_animelist = None
	
	async def connect_voice(self, channel: VoiceChannel):
		await self.disconnect_voice()
		self.voice_client = await channel.connect()

	async def disconnect_voice(self):
		await self.unload_audio()
		if self.voice_client != None:
			await self.voice_client.disconnect()
			self.voice_client = None

	async def load_audio(self, file_loc: str, theme_data: Theme, anime_data: Anime):
		await self.unload_audio()
		self.audio = await FFmpegOpusAudio.from_probe(file_loc)
		self.audio_theme_data = theme_data
		self.audio_anime_data = anime_data

	async def unload_audio(self):
		if self.audio != None:
			self.audio.cleanup()
			self.audio = None
		self.audio_theme_data = None
		self.audio_anime_data = None

data = Data()
header = {"User-Agent":"NakamaDiscordBotUA"}



def to_thread(func: typing.Callable) -> typing.Coroutine:
	@functools.wraps(func)
	async def wrapper(*args, **kwargs):
		return await asyncio.to_thread(func, *args, **kwargs)
	return wrapper


@to_thread
def download_theme(url: str, file_loc: str):
	if not os.path.exists(file_loc):
		with requests.get(url, headers=header, stream=True) as r:
			r.raise_for_status()
			with open(file_loc, 'wb') as f:
				shutil.copyfileobj(r.raw, f)


# ------------------------- jikan -----------------------------
@slash.slash(name = "jikan")
async def _jikan(ctx: SlashContext, name: str):
	jikan = Jikan()
	e = Embed()
	res = jikan.search('anime', name)
	anime = res['results'][0]
	e.title = anime['title']
	e.description = anime['synopsis']
	await ctx.send(embed=e)


# ------------------------- animelist -----------------------------
@slash.slash(name = "animelist")
async def _anime_list(ctx: SlashContext, name: str):
	jikan = Jikan()
	try:
		res = jikan.user(username=name, request='animelist', argument='completed')
		ln = len(res['anime'])
		embed = Embed()
		embed.title = name + ' has completed ' + str(ln) +' japanese animes'
		embed.description = 'And the first one found was ' + res['anime'][0]['title']
		await ctx.send(embed=embed)
	except(JikanAPIException):
		await ctx.send("Something went wrong, maybe " + name + " doesn't have a myanimelist?")
	

# ------------------------- op -----------------------------
@slash.slash(name = "op")
async def _op(ctx: SlashContext, name: str):
	if ctx.author.voice == None:
		await ctx.send("You need to be in a voice channel to use this command")
		return

	vs: VoiceState = ctx.author.voice
	if vs.channel == None:
		await ctx.send("You need to be in a voice channel to use this command")
		return

	await ctx.send("You got it boss")
	await ctx.channel.send("Searching for an anime named " + name)

	vc: VoiceChannel = vs.channel
	voice_client: VoiceClient = await vc.connect()
	await ctx.guild.change_voice_state(channel=vc, self_deaf=True, self_mute=False)

	jikan = Jikan()
	res = jikan.search('anime', name)
	id = res['results'][0]['mal_id']
	
	await ctx.channel.send("Downloading OP for " + res['results'][0]['title'])
	
	adr = "https://staging.animethemes.moe/api/anime?include=animethemes.animethemeentries.videos&filter[has]=resources&filter[site]=MyAnimeList&filter[external_id]=" + str(id)
	res = requests.get(adr, headers=header)

	if res.status_code == 200:
		theme_slug = res.json()['anime'][0]['animethemes'][0]['animethemeentries'][0]['videos'][0]['basename']
		video_addr = "https://animethemes.moe/video/" + theme_slug
		file_loc = 'temp/' + theme_slug

		# await ctx.send("Downloading OP...")
		print("video address for " + name + " is " + video_addr)

		if not os.path.exists(file_loc):
			with requests.get(video_addr, headers=header, stream=True) as r:
				print("downloading...")
				r.raise_for_status()
				with open(file_loc, 'wb') as f:
					for chunk in r.iter_content(chunk_size=8192):
						f.write(chunk)
				print("finished!")

		audio = FFmpegOpusAudio(file_loc)
		voice_client.play(audio)
		await sleep(5)
		voice_client.stop()
		audio.cleanup()
	else:
		await ctx.send("We ran into an issue looking for the theme")
	
	await voice_client.disconnect()


#------------------------ audio controls ----------------------
@slash.slash(name = "stop")
async def _stop(ctx: SlashContext):
	if data.voice_client != None:
		if data.voice_client.is_playing():
			data.voice_client.stop()
	await ctx.send("⏹")

@slash.slash(name = "pause")
async def _pause(ctx: SlashContext):
	if data.voice_client != None:
		if data.voice_client.is_playing():
			data.voice_client.pause()
	await ctx.send("⏸")

@slash.slash(name = "continue")
async def _continue(ctx: SlashContext):
	if data.voice_client != None:
		if data.voice_client.is_paused():
			if data.audio != None:
				data.voice_client.play(data.audio)
	await ctx.send("▶")

@slash.slash(name = "disconnect")
async def _disconnect(ctx: SlashContext):
	await data.disconnect_voice()
	await ctx.send("✔")

@slash.slash(name = "playing")
async def _playing(ctx: SlashContext):
	if data.voice_client != None:
		if data.audio_theme_data != None:
			anime = data.audio_anime_data
			theme = data.audio_theme_data
			e = Embed()
			e.set_thumbnail(url=anime.image_url)
			e.title = anime.name if len(anime.name)>0 else 'N/A'
			e.url = anime.mal_url if len(anime.mal_url)>0 else None

			studios_text = ''
			if len(anime.studios) == 0:
				studios_text = 'None?'
			else:
				studios_text = ', '.join(anime.studios)

			genres_text = ''
			if len(anime.genres) == 0:
				genres_text = 'None?'
			else:
				genres_text = ', '.join(anime.genres)

			e.add_field(name="Studios", value=studios_text, inline=False)
			e.add_field(name="Genres", value=genres_text, inline=False)
			e.add_field(name="Theme", value=theme.slug if len(theme.slug)>0 else 'N/A')
			e.add_field(name="Episodes", value=theme.episodes if len(theme.episodes)>0 else 'N/A')
			await ctx.send(embed=e)
			return
	await ctx.send("Not currently playing anything")

#------------------------ play random ------------------------
class RandomData:
	def __init__(self) -> None:
		self.mal_name = ''
		self.animelist = []
		self.order = []
		self.idx = 0
random_data = RandomData()


@slash.slash(name = "random")
async def _random(ctx: SlashContext, mal_name: str):
	# check for issues
	if ctx.author.voice == None or ctx.author.voice.channel == None:
		await ctx.send("You need to be in a voice channel to use this command")
		return

	await ctx.send("You got it boss")
	c = ctx.channel

	# init
	if random_data.mal_name != mal_name:
		try:
			random_data.animelist = JikanApi.animelist(mal_name, 'completed')
			if len(random_data.animelist) == 0:
				await c.send(mal_name + " doesn't have any anime in their list....")
				return
			random_data.order = list(range(0, len(random_data.animelist)))
			random.shuffle(random_data.order)
			random_data.mal_name = mal_name
		except:
			await c.send("An error occured, does " + mal_name + " have an animelist?")
			return

	# select the random anime
	t = 0
	themes = None
	while themes == None and t < 5:
		t += 1
		if random_data.idx >= len(random_data.order):
			random.shuffle(random_data.order)
			random_data.idx = 0
		else:
			random_data.idx += 1
		anime = random_data.animelist[random_data.order[random_data.idx]]
		try:
			themes = anime.get_themes()
			if len(themes.themes) == 0:
				raise NoThemesForAnime
		except:
			pass
	
	if t >= 5:
		await c.send("Cant find any anime themes in " + mal_name + "'s animelist")
		return

	# select the random theme
	theme = themes.themes[random.randint(0, len(themes.themes)-1)]

	# join channel
	if data.voice_client == None or data.voice_client.channel != ctx.author.voice.channel:
		await data.connect_voice(ctx.author.voice.channel)
		await ctx.guild.change_voice_state(channel=ctx.author.voice.channel, self_deaf=True, self_mute=False)

	# download theme
	message: discord.Message = await c.send("Downloading theme from " + random_data.mal_name + "'s animelist...")
	file_loc = 'temp/' + theme.basename
	try:
		await download_theme(theme.url, file_loc)
	except Exception as e:
		await c.send("An error occured trying to download the theme :(")
		return
	await message.edit(content="Finished downloading theme from " + random_data.mal_name + "'s animelist!")

	# play theme
	if data.voice_client.is_playing():
		data.voice_client.stop()
		await data.unload_audio()
	await data.load_audio(file_loc, theme, anime)
	data.voice_client.play(data.audio)


# ------------------------- GAME COMMANDS -----------------------------
@slash.slash(name = "theme_quiz")
async def _theme_quiz(ctx: SlashContext, mal_name: str):
	pass




# ------------- MAIN --------------
with open('token.txt') as f:
	print("running")
	bot.run(f.readline())





# @TODO: 	change _op to _play_theme, play the entire theme, add a _stop command, use the new JikanApi to search and then play the OP
#					maybe add in a selection box to select the anime from the search list and then the theme to play?
# @TODO:  Add an option to play random themes from an animelist, may require a /init_animelist command. Add options to not print the anime info
#					Unitl x seconds has passed. i.e. a precursor to the guessing game