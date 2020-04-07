"""Search and gallery operations for art websites"""
import discord
from discord.ext import commands


class ImageBoard(commands.Cog):
    """Streaming websites definitions"""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.command(name='danbooru', aliases=['dan'])
    async def search_danbooru(self, ctx, *tags):
        """Search on danbooru!"""
        board_cog = self.bot.get_cog('Board')

        if board_cog is None:
            print('BOARD COG WAS MISSING!')
            return

        await board_cog.search_board(ctx, tags)

    @commands.command(name='e621', aliases=['e6'])
    async def search_e621(self, ctx, *tags):
        """Search on e621!"""
        board_cog = self.bot.get_cog('Board')

        if board_cog is None:
            print('BOARD COG WAS MISSING!')
            return

        await board_cog.search_board(ctx, tags, board='e621')

    async def show_gallery(self, msg: discord.Message, url: str, board: str):
        """Show a gallery"""
        gallery_cog = self.bot.get_cog('Gallery')

        if gallery_cog is None:
            print('GALLERY COG WAS MISSING!')

        if board == 'danbooru':
            await gallery_cog.display_static(msg.channel, msg, url, id_start='/posts/', id_end='?')
        elif board == 'e621':
            await gallery_cog.display_static(msg.channel, msg, url, board='e621', id_start=['/show/', '/posts/'], id_end=r'^[0-9]+', end_regex=True)
        elif board == 'twitter':
            await gallery_cog.get_twitter_gallery(msg, url)
        elif board == 'pixiv':
            await gallery_cog.get_pixiv_gallery(msg, url)
        elif board == 'sankaku':
            await gallery_cog.get_sankaku_post(msg, url)
        elif board == 'deviantart':
            await gallery_cog.get_deviantart_post(msg, url)
        elif board == 'imgur':
            await gallery_cog.get_imgur_gallery(msg, url)
        else:
            raise ValueError('Board has no gallery entry.')


def setup(bot: commands.Bot):
    """Initiate cog"""
    bot.add_cog(ImageBoard(bot))