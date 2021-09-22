# -- install --
# pip install jikanpy
# python3 -m pip install -U discord.py[voice]
# -------------
# -------------

from asyncio.tasks import sleep
import os
from discord.member import VoiceState
from discord.player import FFmpegOpusAudio
from discord.voice_client import VoiceClient, VoiceProtocol
from jikanpy import Jikan, APIException as JikanAPIException

from anime_apis import JikanApi, Anime, AnimeThemes, Theme

import logging
from discord import Client, Intents, Embed
from discord.channel import VoiceChannel
from discord_slash import SlashCommand, SlashContext

import requests


logging.basicConfig(level=logging.INFO)	
bot = Client(command_prefix="`", intents = Intents.default())
slash = SlashCommand(bot, sync_commands=True, debug_guild=175865262866825216)

@slash.slash(name = "jikan")
async def _jikan(ctx: SlashContext, name: str):
	jikan = Jikan()
	e = Embed()
	res = jikan.search('anime', name)
	anime = res['results'][0]
	e.title = anime['title']
	e.description = anime['synopsis']
	await ctx.send(embed=e)


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
	header = {"User-Agent":"NakamaDiscordBotUA"}
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


# ------------- MAIN --------------
with open('token.txt') as f:
	print("running")
	bot.run(f.readline())





# @TODO: 	change _op to _play_theme, play the entire theme, add a _stop command, use the new JikanApi to search and then play the OP
#					maybe add in a selection box to select the anime from the search list and then the theme to play?
# @TODO:  Add an option to play random themes from an animelist, may require a /init_animelist command. Add options to not print the anime info
#					Unitl x seconds has passed. i.e. a precursor to the guessing game