"""Provide users a way to view timezones"""
from datetime import datetime

import pytz
from discord.ext import commands


class TimeZone(commands.Cog):
    """TimeZone class"""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.command(aliases=['t'])
    async def time(self, ctx, *region_or_country):
        """Provide time zones"""

        if not region_or_country:
            tzs = [
                ['USA', 'America/Chicago'],
                ['Canada', 'America/Toronto'],
                ['Mexico', 'America/Mexico_City'],
            ]

        tz_result = '>>> '
        for label, timezone in tzs:
            tz = pytz.timezone(timezone)
            tz_time = datetime.now(tz)
            # https://strftime.org
            tz_result += (label + ': ').ljust(10, ' ') + tz_time.strftime('%a, %b %d %H:%M:%S\n')

        await ctx.send(tz_result)


def setup(bot: commands.Bot):
    """Initiate cog"""
    bot.add_cog(TimeZone(bot))
