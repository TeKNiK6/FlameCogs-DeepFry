import discord
from redbot.core import commands
from redbot.core import Config
from redbot.core import checks
from PIL import Image
from random import randint
from io import BytesIO
import functools
import asyncio
import urllib
import ffmpeg
import tempfile
import os

MAX_SIZE = 10 * 1000 * 1000

class ImageFindError(Exception):
	"""Generic error for the _get_image function."""
	pass

class Deepfry(commands.Cog):
	"""Deepfries memes."""
	def __init__(self, bot):
		self.bot = bot
		self.config = Config.get_conf(self, identifier=7345167900)
		self.config.register_guild(
			fryChance = 0
		)
		self.imagetypes = ['png', 'jpg', 'jpeg','gif', 'webp', 'mp4']
		
	#@staticmethod
	def _fry(self,imgLink):
		path = urllib.parse.urlparse(imgLink).path
		outputFile = None
		fileExt = None
		for x in self.imagetypes:
			if path.lower().endswith(x):
				fileExt = x
				outputFile = "Temp." + fileExt
				break
		if outputFile == None:
			raise ImageFindError(
				f'Unsupported filetype'
			)
		tmpPath = "/tmp/temp_deepfry/"
		if not os.path.exists(tmpPath):
			try:
				os.makedirs(tmpPath)
			except OSError as e:
				raise ImageFindError(f"Error frying image - {e}")

		outputFileFullPath = tmpPath + "/" + outputFile

		try:
			ffmpeg.input(imgLink).output(outputFileFullPath, vf='scale=320:-1:flags=lanczos,eq=saturation=2.547872526587171:contrast=1.663945577845754:gamma_r=1.9468562525223558:gamma_g=1.982674184755574:gamma_b=1.884297295698892,noise=alls=15.554466360495802:allf=t,unsharp=5:5:3.25:5:5:3,split[s0][s1];[s0]palettegen[p];[s1][p]paletteuse').overwrite_output().run(capture_stderr=True)
		except ffmpeg.Error as e:
			raise ImageFindError(
					f"Error frying image - {e.stderr.decode('utf8')}"
				)

		# img = Image.open(outputFileFullPath)
		# imgBytes = BytesIO()
		# imgBytes.name = "temp." + fileExt
		# img.save(imgBytes, fileExt)
		# imgBytes.seek(0)
		# tempDir.cleanup()
		#img = img.convert('RGB')
		pathFile = os.path.normpath(outputFileFullPath)
		return pathFile

	async def _get_image(self, ctx, link: str):
		"""Helper function to find an image."""
		if ctx.guild:
			filesize_limit = ctx.guild.filesize_limit
		else:
			filesize_limit = MAX_SIZE

		if not ctx.message.attachments and not link:
			async for msg in ctx.channel.history(limit=10):
				for a in msg.attachments:
					path = urllib.parse.urlparse(a.url).path
					if (
						any(path.lower().endswith(x) for x in self.imagetypes)
						or allowAllTypes
					):
						link = a.url
						break
				if link:
					break
			if not link:
				raise ImageFindError('Please provide an attachment.')
	
		if link: #linked image
			path = urllib.parse.urlparse(link).path
			if not any(path.lower().endswith(x) for x in self.imagetypes):
				raise ImageFindError(
					f'That does not look like an image of a supported filetype. Make sure you provide a direct link.'
				)

		# else: #attached image
		# 	path = urllib.parse.urlparse(ctx.message.attachments[0].url).path
		# 	if not any(path.lower().endswith(x) for x in self.imagetypes):
		# 		raise ImageFindError(f'That does not look like an image of a supported filetype.')

		# 	if ctx.message.attachments[0].size > filesize_limit:
		# 		raise ImageFindError('That image is too large.')
		# 	temp_orig = BytesIO()
		# 	await ctx.message.attachments[0].save(temp_orig)
		# 	temp_orig.seek(0)
		# 	img = Image.open(temp_orig)
		#if max(img.size) > 3840:
			#raise ImageFindError('That image is too large.')
		
		#img = img.convert('RGB')
		return link
	
	@commands.command(aliases=['df'])
	@commands.bot_has_permissions(attach_files=True)
	async def deepfry(self, ctx, link: str=None):
		"""
		Deepfries images.
		
		The optional parameter "link" can be either a member or a **direct link** to an image.
		"""
		async with ctx.typing():
			try:
				imgLink = await self._get_image(ctx, link)
			except ImageFindError as e:	
				return await ctx.send(e)

			task = functools.partial(self._fry, imgLink)
			task = self.bot.loop.run_in_executor(None, task)
			try:
				image = await asyncio.wait_for(task, timeout=60)
			except asyncio.TimeoutError:
				return await ctx.send('The image took too long to process.')
			try:
				await ctx.send(file=discord.File(image))
			except discord.errors.HTTPException:
				return await ctx.send('That image is too large.')

	@commands.guild_only()
	@checks.guildowner()
	@commands.group(invoke_without_command=True)
	async def deepfryset(self, ctx):
		"""Config options for deepfry."""
		await ctx.send_help()
		cfg = await self.config.guild(ctx.guild).all()
		msg = (
			'Deepfry chance: {fryChance}\n'
		).format_map(cfg)
		await ctx.send(f'```py\n{msg}```')
	
	@deepfryset.command()	
	async def frychance(self, ctx, value: int=None):
		"""
		Change the rate images are automatically deepfried.
		
		Images will have a 1/<value> chance to be deepfried.
		Higher values cause less often fries.
		Set to 0 to disable.
		This value is server specific.
		"""
		if value is None:
			v = await self.config.guild(ctx.message.guild).fryChance()
			if v == 0:
				await ctx.send('Autofrying is currently disabled.')
			elif v == 1:
				await ctx.send('All images are being fried.')
			else:
				await ctx.send(f'1 out of every {str(v)} images are being fried.')
		else:
			if value < 0:
				return await ctx.send('Value cannot be less than 0.')
			await self.config.guild(ctx.guild).fryChance.set(value)
			if value == 0:
				await ctx.send('Autofrying is now disabled.')
			elif value == 1:
				await ctx.send('All images will be fried.')
			else:
				await ctx.send(f'1 out of every {str(value)} images will be fried.')

	async def red_delete_data_for_user(self, **kwargs):
		"""Nothing to delete."""
		return

	@commands.Cog.listener()
	async def on_message_without_command(self, msg):
		"""Passively deepfries random images."""
		#CHECKS
		if msg.author.bot:
			return
		if not msg.attachments:
			return
		if msg.guild is None:
			return
		if await self.bot.cog_disabled_in_guild(self, msg.guild):
			return
		if not msg.channel.permissions_for(msg.guild.me).attach_files:
			return
		if msg.attachments[0].size > msg.guild.filesize_limit:
			return
		path = urllib.parse.urlparse(msg.attachments[0].url).path
		if not any(path.lower().endswith(x) for x in self.imagetypes):
			return
		#GUILD SETTINGS
		vfry = await self.config.guild(msg.guild).fryChance()
		
		#FRY
		# if vfry != 0:
		# 	l = randint(1, vfry)
		# 	if l == 1:
		# 		temp = BytesIO()
		# 		await msg.attachments[0].save(temp)
		# 		temp.seek(0)
		# 		img = Image.open(temp)
		# 		duration = None
		# 		if isgif:
		# 			if 'duration' in img.info:
		# 				duration = img.info['duration']
		# 			task = functools.partial(self._videofry, img, duration)
		# 		else:
		# 			img = img.convert('RGB')
		# 			task = functools.partial(self._fry, img)
		# 		task = self.bot.loop.run_in_executor(None, task)
		# 		try:
		# 			image = await asyncio.wait_for(task, timeout=60)
		# 		except asyncio.TimeoutError:
		# 			return
		# 		await msg.channel.send(file=discord.File(image))
