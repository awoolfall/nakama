
from typing import Any, Dict, List
import jikanpy
import requests

class NoThemesForAnime(Exception):
	pass

class NoVideoFoundForTheme(Exception):
	pass

class AnimeDoesNotExistInAnimeThemes(Exception):
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

		if len(entry['videos']) == 0:
			raise NoVideoFoundForTheme
		video = entry['videos'][0]
		self.basename = video['basename']
		self.url = "https://animethemes.moe/video/" + self.basename
		self.size = video['size']
		self.mimetype = video['mimetype']
		self.overlap = video['overlap']

class AnimeThemes:
	def __init__(self, data: Dict[str, Any]):
		anime = data[0]
		self.name = anime['name']
		self.year = anime['year']
		self.synopsis = anime['synopsis']

		self.themes = []
		for theme_data in anime['animethemes']:
			try:
				self.themes.append(Theme(theme_data))
			except NoThemesForAnime:
				print("No video found for anime " + self.name + " for theme " + theme_data['slug'])
		

class AnimeThemesApi:
	header = {"User-Agent":"NakamaDiscordBotUA"}

	def anime_from_mal_id(mal_id: int) -> AnimeThemes:
		addr = "https://staging.animethemes.moe/api/anime?include=animethemes.animethemeentries.videos&filter[has]=resources&filter[site]=MyAnimeList&filter[external_id]=" + str(mal_id)
		try:
			res = requests.get(addr, headers=AnimeThemesApi.header)
			if res.status_code == 200:
				if len(res.json()['anime']) > 0:
					return Anime(res.json()['anime'][0])
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
	def search(name: str) -> List[Anime]:
		jikan = jikanpy.Jikan()
		res = jikan.search('anime', name)
		list = []
		for anime in res['results']:
			list.append(Anime(anime))
		return list
