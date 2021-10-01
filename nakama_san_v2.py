# -- install --
# pip install jikanpy
# python3 -m pip install -U discord.py[voice]
# pip install -U discord-interactions
# -------------
# -------------

from ctypes import util
import os
import random
import discord
from discord import utils
from discord.member import VoiceState
from discord.player import AudioSource, FFmpegOpusAudio
from discord.voice_client import VoiceClient, VoiceProtocol
from discord_slash.context import ComponentContext
from discord_slash.model import SlashCommandOptionType
from discord_slash.utils.manage_commands import create_option
from jikanpy import Jikan, APIException as JikanAPIException
from nakama_game import GuessGame

from util import Data, to_thread, play_anime_theme, create_anime_theme_embed
from anime_apis import JikanApi, Anime, AnimeThemes, JikanSearchRequiresThreeCharacters, NoThemesForAnime, Theme

import logging
from discord import Client, Intents, Embed, file
from discord.channel import VoiceChannel
from discord_slash import SlashCommand, SlashContext
from discord_slash.utils.manage_components import create_select, create_select_option, create_actionrow, wait_for_component

import requests
import shutil

import ffmpy


logging.basicConfig(level=logging.INFO)	
bot = Client(command_prefix="`", intents = Intents.default())
slash = SlashCommand(bot, sync_commands=True, debug_guild=175865262866825216)

data = Data()

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
@slash.slash(
	name = "op",
	description="Select and play a theme from an anime",
	options=[
		create_option(
			name="anime_title",
			description="The anime to play a theme from",
			option_type=SlashCommandOptionType.STRING,
			required=True
		)
	]
)
async def _op(ctx: SlashContext, anime_title: str):
	if ctx.author.voice == None:
		await ctx.send("You need to be in a voice channel to use this command")
		return

	if ctx.author.voice.channel == None:
		await ctx.send("You need to be in a voice channel to use this command")
		return

	await ctx.send("You got it boss")
	status_msg = await ctx.channel.send("Searching for an anime named " + anime_title)

	animes = await JikanApi.search(anime_title)
	if len(animes) == 0:
		await status_msg.edit("No anime named '" + anime_title + "' found")
		return

	anime: Anime = None
	if len(animes) == 1:
		await status_msg.edit(content="Found " + animes[0].name)
		anime = animes[0]
	else:
		anime_options = []
		for index, anime in enumerate(animes):
			if index >= 5:
				break
			anime_options.append(create_select_option(
				anime.name,
				value=str(index)
			))
		anime_selection = create_select(
			options=anime_options,
			placeholder="Choose the desired anime",
			min_values=1,
			max_values=1
		)
		ar = create_actionrow(anime_selection)
		sel_msg = await ctx.send("Select:", components=[ar])
		try:
			selection_ctx: ComponentContext = await wait_for_component(bot, components=ar, timeout=30)
		except:
			await sel_msg.delete()
			await status_msg.edit(content="Selection timed out")
			return
		await sel_msg.delete()
		anime = animes[int(selection_ctx.selected_options[0])]

	themes = anime.get_themes()	

	theme: Theme = None
	if len(themes.themes) == 0:
		await status_msg.edit(content="No themes exist for " + anime.name)
		return
	elif len(themes.themes) == 1:
		theme = themes.themes[0]
	else:
		theme_options = []
		for index, theme in enumerate(themes.themes):
			if index >= 25:
				break
			option_txt = theme.slug
			if len(theme.song_name) > 0:
				option_txt += (": " + theme.song_name)
			theme_options.append(create_select_option(
				option_txt,
				value=str(index)
			))
		theme_selection = create_select(
			options=theme_options,
			placeholder="Choose the desired theme",
			min_values=1,
			max_values=1
		)
		ar = create_actionrow(theme_selection)
		sel_msg = await ctx.send("Select:" + (" truncated :(" if len(theme_options)==25 else ""), components=[ar])
		try:
			selection_ctx: ComponentContext = await wait_for_component(bot, components=ar, timeout=30)
		except:
			await sel_msg.delete()
			await status_msg.edit(content="Selection timed out")
			return
		await sel_msg.delete()
		theme = themes.themes[int(selection_ctx.selected_options[0])]

	# play the theme
	await play_anime_theme(anime, theme, ctx.channel, ctx.author.voice.channel, data)


#------------------------ audio controls ----------------------
@slash.slash(name = "stop")
async def _stop(ctx: SlashContext):
	if data.voice_client != None:
		if data.voice_client.is_playing():
			data.voice_client.stop()
	await ctx.send("ok")

@slash.slash(name = "pause")
async def _pause(ctx: SlashContext):
	if data.voice_client != None:
		if data.voice_client.is_playing():
			data.voice_client.pause()
	await ctx.send("ok")

@slash.slash(name = "continue")
async def _continue(ctx: SlashContext):
	if data.voice_client != None:
		if data.voice_client.is_paused():
			if data.audio != None:
				data.voice_client.play(data.audio)
	await ctx.send("ok")

async def repeat_audio_func():
	if data.voice_client != None:
		if not data.voice_client.is_playing():
			if data.audio != None:
				await data.reload_audio()
				data.voice_client.play(data.audio)

@slash.slash(name = "repeat")
async def _repeat(ctx: SlashContext):
	await repeat_audio_func()
	await ctx.send("ok")

@slash.slash(name = "disconnect")
async def _disconnect(ctx: SlashContext):
	await data.disconnect_voice()
	await ctx.send("ok")

@slash.slash(name = "playing")
async def _playing(ctx: SlashContext):
	if data.voice_client != None:
		if data.audio_theme_data != None:
			anime = data.audio_anime_data
			theme = data.audio_theme_data
			e = create_anime_theme_embed(anime, theme)
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


@slash.slash(
	name = "random",
	description="Play a random theme from a random anime from the given user's myanimelist",
	options=[
		create_option(
			name="mal_name",
			description="The desired MyAnimeList to retrieve a random anime from",
			option_type=SlashCommandOptionType.STRING,
			required=False
		)
	]
)
async def _random(ctx: SlashContext, mal_name: str = None):
	logging.log(logging.INFO, "Running /random")
	# check for issues
	if ctx.author.voice == None or ctx.author.voice.channel == None:
		await ctx.send("You need to be in a voice channel to use this command")
		return

	await ctx.send("You got it boss")
	c = ctx.channel

	# init
	if mal_name == None:
		if random_data.mal_name == '':
			await c.send("No MAL user has been provided, for the first usage of /random a MAL user must be provided")
			return
		else:
			mal_name = random_data.mal_name

	if random_data.mal_name != mal_name:
		try:
			random_data.animelist = await JikanApi.animelist(mal_name, 'completed')
			try:
				random_data.animelist.extend(await JikanApi.animelist(mal_name, 'watching'))
			except:
				pass
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
			await c.send("Re-shuffling anime list")
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

	# play the theme
	await play_anime_theme(anime, theme, c, ctx.author.voice.channel, data)


# ------------------------- GAME COMMANDS -----------------------------
@slash.slash(name = "theme_quiz")
async def _theme_quiz(ctx: SlashContext, mal_name: str):
	if ctx.author.voice == None:
		await ctx.send("You must be in a voice channel to use this commad.")
		return

	try:
		status_msg = await ctx.send("Looking for " + mal_name + " on myanimelist...")
		animelist = await JikanApi.animelist(mal_name, 'completed')
		animelist.append(await JikanApi.animelist(mal_name, 'watching'))
	except:
		await ctx.channel.send("An error occured retrieving the animelist, does " + mal_name + ' have a myanimelist?')

	data.theme_quiz = GuessGame(animelist, data)
	await data.connect_voice(ctx.author.voice.channel)
	await status_msg.edit(content="Theme guessing game has begun based on " + mal_name + "'s myanimelist!")
	await data.theme_quiz.next_theme(ctx)

@slash.slash(name = "guess")
async def _guess(ctx: SlashContext, anime: str):
	if data.theme_quiz != None:
		await data.theme_quiz.make_guess(ctx, anime)
	else:
		await ctx.send('No theme guessing game is currently running.')

@slash.slash(name = "next")
async def _next(ctx: SlashContext):
	if data.theme_quiz != None:
		await data.theme_quiz.next_theme(ctx)
	else:
		await ctx.send('No theme guessing game is currently running.')


# ------------- MAIN --------------
with open('token.txt') as f:
	print("running")
	bot.run(f.readline())
