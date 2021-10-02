
import time
import asyncio
from typing import Any, Dict, List
from discord.utils import sleep_until
import jikanpy
import requests
import datetime
from threading import Lock

class NoThemesForAnime(Exception):
	pass

class NoVideoFoundForTheme(Exception):
	pass

class AnimeDoesNotExistInAnimeThemes(Exception):
	pass

class JikanSearchRequiresThreeCharacters(Exception):
	pass


class Theme:
	def __init__(self, data: Dict[str, Any]):
		self.type = data['type']
		self.slug = data['slug']

		if len(data['animethemeentries']) == 0:
			raise NoVideoFoundForTheme
		entry = data['animethemeentries'][0]
		self.nsfw = entry['nsfw']
		self.episodes = entry['episodes']
		self.song_name = data['song']['title']
		self.song_artists = []
		for a in data['song']['artists']:
			self.song_artists.append(a['name'])

		video = None
		if len(entry['videos']) == 0:
			raise NoVideoFoundForTheme
		elif len(entry['videos']) > 1:
			lowest_res = int(entry['videos'][0]['resolution'])
			video = entry['videos'][0]
			for v in entry['videos']:
				if int(v['resolution']) < lowest_res:
					video = v
		else:
			video = entry['videos'][0]
		self.basename = video['basename']
		self.url = "https://animethemes.moe/video/" + self.basename
		self.size = video['size']
		self.mimetype = video['mimetype']
		self.overlap = video['overlap']

class AnimeThemes:
	def __init__(self, data: Dict[str, Any]):
		self.name = data['name']
		self.year = data['year']
		self.season = data['season']
		self.synopsis = data['synopsis']
		self.studios = []
		for s in data['studios']:
			self.studios.append(s['name'])

		self.themes: List[Theme] = []
		for theme_data in data['animethemes']:
			try:
				self.themes.append(Theme(theme_data))
			except NoThemesForAnime:
				print("No video found for anime " + self.name + " for theme " + theme_data['slug'])
		

class AnimeThemesApi:
	header = {"User-Agent":"NakamaDiscordBotUA"}

	def anime_from_mal_id(mal_id: int) -> AnimeThemes:
		addr = "https://staging.animethemes.moe/api/anime?include=animethemes.animethemeentries.videos,animethemes.song,animethemes.song.artists,series,studios&filter[has]=resources&filter[site]=MyAnimeList&filter[external_id]=" + str(mal_id)
		try:
			res = requests.get(addr, headers=AnimeThemesApi.header)
			if res.status_code == 200:
				if len(res.json()['anime']) > 0:
					return AnimeThemes(res.json()['anime'][0])
			raise AnimeDoesNotExistInAnimeThemes
		except Exception as e:
			raise e


class Anime:
	def __init__(self, mal_data: Dict[str, Any]):
		self.name = mal_data['title']
		self.mal_id = mal_data['mal_id']
		self.mal_url = mal_data['url']
		self.image_url = mal_data['image_url']
		self.anime_type = mal_data['type']
		self.animethemes = None
		self.animethemeserror = False

		self.genres = []
		if 'genres' in mal_data.keys():
			for genre_data in mal_data['genres']:
				self.genres.append(genre_data['name'])
			for demo_data in mal_data['demographics']:
				self.genres.append(demo_data['name'])

		self.studios = []
		if 'studios' in mal_data.keys():
			for studio_data in mal_data['studios']:
				self.studios.append(studio_data['name'])

	def get_themes(self) -> AnimeThemes:
		if self.animethemeserror:
			raise NoThemesForAnime

		if self.animethemes == None:
			try:
				self.animethemes = AnimeThemesApi.anime_from_mal_id(self.mal_id)
			except Exception as e:
				self.animethemeserror = True
				raise e

		return self.animethemes


class JikanApi:
	next_command_time = datetime.datetime.utcnow()
	mutex = Lock()

	async def _wait_for_rate_limit():
		JikanApi.mutex.acquire()
		await sleep_until(JikanApi.next_command_time)
		JikanApi.next_command_time = datetime.datetime.utcnow() + datetime.timedelta(milliseconds=550)
		JikanApi.mutex.release()

	async def search(name: str) -> List[Anime]:
		if len(name) < 3:
			raise JikanSearchRequiresThreeCharacters

		await JikanApi._wait_for_rate_limit()
		jikan = jikanpy.AioJikan()
		res = await jikan.search(search_type='anime', query=name)
		await jikan.close()

		list = []
		for anime in res['results']:
			list.append(Anime(anime))
		return list

	# types can be 'completed', 'ptw', etc. Check jikan api
	async def animelist(mal_name: str, type: str) -> List[Anime]:
		try:

			await JikanApi._wait_for_rate_limit()
			jikan = jikanpy.AioJikan()
			res = await jikan.user(username=mal_name, request='animelist', argument=type)
			await jikan.close()

			list = []
			for anime_data in res['anime']:
				list.append(Anime(anime_data))
			return list
		except Exception as e:
			raise e
