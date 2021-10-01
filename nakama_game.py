from time import sleep
import typing
import typing_extensions
import discord
from discord import message

from discord.channel import TextChannel, VoiceChannel
from discord.embeds import Embed
from discord_slash.context import SlashContext
from anime_apis import AnimeThemesApi, Anime, JikanApi, Theme
import random
import util


class GuessGame:
	def __init__(self, animelist: typing.List[Anime], data: util.Data):
		self.app_data = data

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
		curr_anime = self.current_anime()
		if curr_anime == None:
			await ctx.send('There is currently no theme playing to guess.')
			return
		
		if len(guess) < 3:
			await ctx.send('Your guess must be at least 3 letters in length.')
			return

		await ctx.send('Searching for anime named ' + guess, hidden=True)
		res = (await JikanApi.search(guess))[:3]
		titles = []
		for anime in res:
			titles.append('[' + anime.name + '](' + anime.mal_url + ')')

		embed = Embed()
		embed.title = 'You have made guesses for:'
		desc_text = ''
		embed.description = '\n'.join(titles)
		embed.set_footer(text='If your guess is not in the above list then retype /guess with more detail.')
		await ctx.send(embed=embed, hidden=True)

		success = False
		for a in res:
			if a.mal_id == curr_anime.mal_id:
				success = True
				break
		self.guesses.append((ctx.author, guess, success))
		await ctx.channel.send(str(ctx.author.display_name) + " has made a guess!")

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
		e.description = '\n'.join(correct_names)
		await ctx.send(embed=e)

	async def next_theme(self, ctx: SlashContext):
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

		embed = Embed()
		embed.title = 'Playing Anime Theme #' + str(self.quiz_item_number)
		embed.description = 'Place your guesses using /guess!\nThen type /next to show results and continue to the next anime theme.'
		embed.set_footer(text='Hype text still WIP')
		await ctx.send(embed=embed)
