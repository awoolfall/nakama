import logging
import discord
from discord.channel import VoiceChannel
import time

nakama_gif_link = 'https://tenor.com/view/one-piece-fight-zoro-vs-ain-anime-sword-gif-17138145'
blankz_nakama_path = 'Blankz-Nakama.ogg'

continue_playing = False

class MyClient(discord.Client):
	def __init__(self):
		self.voice_client = None
		self.playcount = 0
		self.continue_playing = False

		super().__init__(loop=None) 

	async def on_ready(self):
		print('Logged on as {0}!'.format(self.user))

	def play_music(self):
		if self.voice_client != None:
			self.voice_client.play(discord.FFmpegOpusAudio(blankz_nakama_path), after=lambda e: self.after_music(e))
			self.playcount = self.playcount + 1
			print("    C-C-COMBO x{0}".format(self.playcount))

	def after_music(self, e):
		if e == None and self.continue_playing:
			self.play_music()

	async def on_message(self, message):
		if message.author == self.user:
			return

		if message.content.lower() == 'play the loop':
			if self.voice_client != None:
				print("ISSUE: Nakama-san is already playing the loop")
				return

			if message.author.voice == None:
				print("ISSUE: requestor is not in a voice channel")
				return

			print("playing the loop: requestor: {0.author.name}".format(message))
			print("    in channel: {0.author.voice.channel}".format(message))
			await message.channel.send("You got it boss")
			await message.channel.send(nakama_gif_link)
			self.voice_client = await message.author.voice.channel.connect()
			await message.guild.change_voice_state(channel=self.voice_client.channel, self_mute=False, self_deaf=True)
			self.play_music()
			self.continue_playing = True
			return;

		if message.content.lower() == 'stop the loop':
			if self.voice_client != None:
				print("request to stop the loop: requestor: {0.author.name}".format(message))
				self.continue_playing = False
				self.voice_client.stop()
				await self.voice_client.disconnect()
				self.playcount = 0
				self.voice_client = None
			return



logging.basicConfig(level=logging.INFO)	

# if not discord.opus.is_loaded():
# 	discord.opus.load_opus('opus')

with open('token.txt') as f:
	client = MyClient()
	client.run(f.readline())
