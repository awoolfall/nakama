import logging
import discord
from discord.ext import commands
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

	async def play_the_loop(self, message, voice_channel):
			print("playing the loop: requestor: {0.author.name}".format(message))
			print("    in channel: {0}".format(voice_channel))
			await message.channel.send("You got it boss")
			await message.channel.send(nakama_gif_link)
			self.voice_client = await voice_channel.connect()
			await message.guild.change_voice_state(channel=self.voice_client.channel, self_mute=False, self_deaf=True)
			self.play_music()
			self.continue_playing = True

	# ON MESSAGE
	# ------------------------------------------------------------
	async def on_message(self, message: discord.Message):
		if message.author == self.user:
			return

		#
		# play the loop <for @mention>
		#
		if message.content.lower().startswith('play the loop'):
			if self.voice_client != None:
				print("ISSUE: Nakama-san is already playing the loop")
				return

			voice_channel = None
			if message.content.lower().startswith('play the loop for'):
				msg = message.content.split()
				id = msg.pop()
				# hacky bs to convert @mention to member
				id = id.replace("<","")
				id = id.replace(">","")
				id = id.replace("@","")
				id = id.replace("!","")
				mem = await message.guild.fetch_member(id)
				voice_channel = mem.voice.channel
			else:
				if message.author.voice == None:
					print("ISSUE: requestor is not in a voice channel")
					return
				voice_channel = message.author.voice.channel

			await self.play_the_loop(message, voice_channel)
			return

		#
		#	stop the loop
		#
		if message.content.lower() == 'stop the loop':
			if self.voice_client != None:
				print("request to stop the loop: requestor: {0.author.name}".format(message))
				self.continue_playing = False
				self.voice_client.stop()
				await self.voice_client.disconnect()
				self.playcount = 0
				self.voice_client = None
			return
	# -----------------------------------------------------------


logging.basicConfig(level=logging.INFO)	

# if not discord.opus.is_loaded():
# 	discord.opus.load_opus('opus')

with open('token.txt') as f:
	client = MyClient()
	client.run(f.readline())
