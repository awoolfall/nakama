from inspect import ismodule
from time import sleep
import typing
import typing_extensions
import discord
from discord import message

from discord.channel import TextChannel, VoiceChannel
from discord.embeds import Embed, EmptyEmbed
from discord.enums import Enum
from discord_slash.context import ComponentContext, SlashContext
from discord_slash.model import SlashMessage
from discord_slash.utils.manage_components import create_actionrow, create_select, create_select_option, wait_for_component
from anime_apis import AnimeThemesApi, Anime, JikanApi, Theme
import random
import util

class GuessGameState(Enum):
	IDLE = 1
	WAITING_FOR_GUESSES = 2
	CONCLUDING_ROUND = 3

class GuessGame:
	def __init__(self, animelist: typing.List[Anime], data: util.Data):
		self.app_data = data

		self.state = GuessGameState.IDLE

		self.quiz_item_number = 0
		self.animelist = animelist
		# We want the animelist in a random order, 
		# so we can go through the entire list with no repeats
		self.idx = -1
		self.order = list(range(0, len(self.animelist)))
		self._randomise_animelist()
		self.currnet_theme: Theme = None

		self.guesses = [(discord.Member, str, bool)]

	def current_anime(self) -> typing.Union[Anime, None]:
		if self.idx < 0:
			return None
		else:
			return self.animelist[self.order[self.idx]]

	def current_theme(self) -> typing.Union[Theme, None]:
		return self.currnet_theme

	def _randomise_animelist(self):
		self.idx = 0
		random.shuffle(self.order)

	async def make_guess(self, ctx: SlashContext, guess: str):
		round_number = self.quiz_item_number

		curr_anime = self.current_anime()
		if curr_anime == None or self.state != GuessGameState.WAITING_FOR_GUESSES:
			await ctx.send('There is currently no theme playing to guess.', hidden=True)
			return
		
		if len(guess) < 3:
			await ctx.send('Your guess must be at least 3 letters in length.', hidden=True)
			return

		await ctx.defer(hidden=True)
		res = (await JikanApi.search(guess))
		titles = []
		for anime in res[:3]:
			titles.append('[' + anime.name + '](' + anime.mal_url + ')')

		success = False
		for a in res[:3]:
			if a.mal_id == curr_anime.mal_id:
				success = True
				break
		self.guesses.append((ctx.author, guess, success))

		embed = Embed()
		embed.title = 'You have made guesses for:'
		embed.description = '\n'.join(titles)
		embed.set_footer(text='If your guess is not in the above list or the below selection then retype /guess with more detail.')

		anime_options = []
		for index, a in enumerate(res):
			if index >= 25:
				break
			anime_options.append(create_select_option(
				a.name[:99],
				value=str(index)
			))
		anime_selection = create_select(
			options=anime_options,
			placeholder="Optionally replace third guess with:",
			min_values=1,
			max_values=1
		)
		ar = create_actionrow(anime_selection)

		await ctx.send(embed=embed, components=[ar], hidden=True)
		await ctx.channel.send(str(ctx.author.display_name) + " has made a guess!")

		while True:
			try:
				selection_ctx: ComponentContext = await wait_for_component(ctx.bot, components=ar, timeout=30)
			except:
				return

			if round_number == self.quiz_item_number:
				sel_anime = res[int(selection_ctx.selected_options[0])]
				if sel_anime.mal_id == curr_anime.mal_id:
					for t in self.guesses:
						if t[0] == ctx.author:
							t[2] = True
				elif res[2].mal_id == curr_anime.mal_id:
					for t in self.guesses:
						if t[0] == ctx.author:
							t[2] = False

				titles.pop()
				titles.append('[' + sel_anime.name + '](' + sel_anime.mal_url + ')')
				embed.description = '\n'.join(titles)
				await selection_ctx.edit_origin(embed=embed)
			else:
				return


	async def _finish_round(self, ctx: SlashContext):
		e = util.create_anime_theme_embed(self.current_anime(), self.current_theme())
		await ctx.send('The Theme was:')
		sleep(1)
		await ctx.send(embed=e)
		sleep(1)
		e = Embed()
		e.title = 'The following people made correct guesses:'
		correct = filter(lambda x: x[2], self.guesses)
		correct_names = []
		for m in correct:
			correct_names.append(str(m[0].mention))
		e.description = ', '.join(correct_names)
		await ctx.send(embed=e)

	async def next_theme(self, ctx: SlashContext):
		if not (self.state == GuessGameState.WAITING_FOR_GUESSES or self.state == GuessGameState.IDLE):
			await ctx.send("/next has already been called by another user", hidden=True)
			return

		self.state = GuessGameState.CONCLUDING_ROUND
		if self.current_anime() != None and self.current_theme() != None:
			await self._finish_round(ctx)

		self.quiz_item_number += 1
		self.guesses.clear()

		animethemes = None
		while (animethemes == None):
			self.idx += 1
			if self.idx >= len(self.order):
				self._randomise_animelist()
		
			anime = self.animelist[self.order[self.idx]]
			try:
				animethemes = anime.get_themes()
			except:
				print("No themes found for " + anime.name)
		
		self.currnet_theme = animethemes.themes[random.randint(0, len(animethemes.themes)-1)]

		msg: message.Message = await util.play_anime_theme(anime, self.currnet_theme, ctx.channel, ctx.author.voice.channel, self.app_data)
		await msg.delete()

		self.state = GuessGameState.WAITING_FOR_GUESSES
		embed = Embed()
		embed.title = 'Playing Anime Theme #' + str(self.quiz_item_number)
		embed.description = 'Place your guesses using /guess!\nThen type /next to show results and continue to the next anime theme.'
		embed.set_footer(text='Hype text still WIP')
		await ctx.send(embed=embed)
