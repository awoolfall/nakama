from anime_apis import AnimeThemesApi, Anime, Theme
from math import floor
from typing import Any, Dict
from jikanpy import Jikan
import random

from jikanpy.exceptions import APIException

class GuessGame:
	def __init__(self, mal_name: str):
		self.statistics = {}
		self.mal = mal_name
		self.jikan = Jikan()

		# Get the animelist of the input mal user
		try:
			self.animelist = self.jikan.user(
				username=mal_name, 
				request='animelist', 
				argument='completed'
			)
		except(APIException):
			self.error = True
			return

		# We want the animelist in a random order, 
		# so we can go through the entire list with no repeats
		self.idx = -1
		self.order = list(range(0, len(self.animelist['anime'])))
		self.anime_len = len(self.order)

		self.error = False


	def next_anime(self) -> Anime:
		self.idx += 1

		# Re-shuffle list if we have reached the end
		if self.idx % len(self.animelist['anime']) == 0:
			random.shuffle(self.order)
			print("Animelist has been completed, re-shuffling")

		# Return the anime at idx given the order list
		anime_dat = self.animelist['anime'][self.order[self.idx % self.anime_len]]
		return Anime(anime_dat)
