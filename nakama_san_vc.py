from cgitb import text
import dis
from unicodedata import category
import discord

bot = discord.Client()

# ------------- VOICE CHAT CHAT --------------

channel_dict = {}

def channel_role_name(channel: discord.VoiceChannel):
	return str(channel.id) + "_vc_role"

def vc_text_channel_name():
	return "voice-text-channel"

async def enter_voice_channel(member: discord.Member, channel: discord.VoiceChannel):
	guild: discord.Guild = channel.guild
	text_channel_name = vc_text_channel_name()

	# find private text channel for this voice channel
	text_channel = channel_dict.get(channel)
	
	# no private channel currently exists, need to create a new one and the text channel
	if text_channel == None:
		print("  Creating text channel for " + channel.name)
		overwrites = {
			guild.default_role: discord.PermissionOverwrite(read_messages=False),
			guild.me: discord.PermissionOverwrite(read_messages=True),
		}
		text_channel: discord.TextChannel = await guild.create_text_channel(text_channel_name, overwrites=overwrites)
		await text_channel.edit(topic=channel.name + "'s text channel", category=channel.category)
		channel_dict[channel] = text_channel

	# clear text channel as new member enters (except for channel identifier message)
	msgs = []
	async for m in text_channel.history():
		msgs.append(m)
	await text_channel.delete_messages(msgs)

	# add user to private text channel
	print("  Adding " + member.display_name + " to " + channel.name + "'s text channel")
	overwrites = discord.PermissionOverwrite(read_messages=True)
	if member != guild.me:
		await text_channel.set_permissions(member, overwrite=overwrites)

async def exit_voice_channel(member: discord.Member, channel: discord.VoiceChannel):
	guild: discord.Guild = channel.guild

	# find private text channel for this voice channel
	text_channel = channel_dict.get(channel)

	# if private text chat for voice channel is found, remove user from channel
	if text_channel != None:
		print("  Removing " + member.display_name + " from " + channel.name + "'s text channel")
		overwrites = discord.PermissionOverwrite(read_messages=False)
		if member != guild.me:
			await text_channel.set_permissions(member, overwrite=overwrites);

		# if no more members exist in the voice channel, then delete its private text channel
		if len(channel.members) == 0:
			print("  Deleting " + channel.name + "'s text channel")
			await text_channel.delete()
			channel_dict.pop(channel)

@bot.event
async def on_voice_state_update(member: discord.Member, before: discord.VoiceState, after: discord.VoiceState):
	if before.channel != after.channel:
		if before.channel != None:
			# they left a channel
			print("User " + member.name + " left a channel")
			await exit_voice_channel(member, before.channel)
		if after.channel != None:
			# they joined a channel
			print("User " + member.name + " joined a channel")
			await enter_voice_channel(member, after.channel)
		

# ------------- MAIN --------------
with open('token.txt') as f:
	print("running")
	bot.run(f.readline())
