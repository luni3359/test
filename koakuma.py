"""Koakuma bot"""
import json
import os
import random
import re
import subprocess
import typing
import urllib
from datetime import datetime

import aiohttp
import commentjson
import discord
import pixivpy3
import tweepy
from discord.ext import commands

import gaka as art
import net
import urusai as channel_activity

SOURCE_DIR = os.path.dirname(os.path.realpath(__file__))
with open(os.path.join(SOURCE_DIR, 'config.jsonc')) as json_file:
    data = commentjson.load(json_file)

bot = commands.Bot(command_prefix='!', description='')
bot.launch_time = datetime.utcnow()
bot.__dict__.update(data)

twit_auth = tweepy.OAuthHandler(bot.auth_keys['twitter']['consumer'], bot.auth_keys['twitter']['consumer_secret'])
twit_auth.set_access_token(bot.auth_keys['twitter']['token'], bot.auth_keys['twitter']['token_secret'])
twitter_api = tweepy.API(twit_auth)

pixiv_api = pixivpy3.AppPixivAPI()

danbooru_auth = aiohttp.BasicAuth(login=bot.auth_keys['danbooru']['username'], password=bot.auth_keys['danbooru']['key'])


@bot.group(aliases=['art'])
async def artist(ctx):
    """Get info about an artist based on a previous immediate message containing a valid url
    from either twitter, danbooru or pixiv."""

    if ctx.invoked_subcommand is None:
        if art.last_artist is None:
            # Better change this to attempt to look back instead of giving up right away
            await ctx.send('I\'m not aware of anybody at the moment...')
            return


@artist.command(aliases=['twit'])
async def twitter(ctx):
    """Display artist's twitter"""

    embed = discord.Embed()
    embed.set_author(
        name='%s (@%s)' % (art.last_artist.twitter_name, art.last_artist.twitter_screen_name),
        url='https://twitter.com/%s' % art.last_artist.twitter_screen_name,
        icon_url=art.last_artist.twitter_profile_image_url_https
    )
    embed.set_thumbnail(url=art.last_artist.twitter_profile_image_url_https)
    embed.set_footer(
        text=bot.assets['twitter']['name'],
        icon_url=bot.assets['twitter']['favicon']
    )
    await ctx.send(embed=embed)


@artist.command(aliases=['dan'])
async def danbooru(ctx):
    """Display artist's art from danbooru"""

    await ctx.send('Box.')


@artist.command(aliases=['pix'])
async def pixiv(ctx):
    """Display something from pixiv"""

    await ctx.send('Navi?')


@bot.command(name='urbandictionary', aliases=['wu', 'udictionary'])
async def search_urban(ctx, *word):
    """Search a term in urbandictionary"""

    word = ' '.join(word).lower()
    word_encoded = urllib.parse.quote_plus(word)
    user_search = '%s%s' % (bot.assets['urban_dictionary']['search_url'], word_encoded)

    js = await net.http_request(user_search, json=True)

    if not js:
        await ctx.send('Error retrieving data from server.')
        return

    # Check if there are any results at all
    if not 'list' in js or not len(js['list']) > 0:
        await ctx.send(random.choice(bot.quotes['dictionary_no_results']))
        return

    embed = discord.Embed()
    embed.title = word
    embed.url = '%s%s' % (bot.assets['urban_dictionary']['dictionary_url'], word_encoded)
    embed.description = ''

    i = 0
    for entry in js['list'][:3]:
        i = i + 1
        definition = entry['definition']
        example = entry['example']

        embed.description += '**%i. %s**\n\n' % (i, formatDictionaryOddities(definition, 'urban'))
        embed.description += formatDictionaryOddities(example, 'urban') + '\n\n'

    if len(embed.description) > 2048:
        embed.description = embed.description[:2048]

    await ctx.send(embed=embed)


@bot.command(name='word', aliases=['w', 'dictionary'])
async def search_word(ctx, *word):
    """Search a term in merriam-webster's dictionary"""

    word = ' '.join(word).lower()
    word_encoded = urllib.parse.quote(word)
    user_search = '%s/%s?key=%s' % (bot.assets['merriam-webster']['search_url'], word_encoded, bot.auth_keys['merriam-webster']['key'])

    js = await net.http_request(user_search, json=True)

    if not js:
        await ctx.send("Oops. What?")
        return

    # Check if there are any results at all
    if not len(js) > 0:
        await ctx.send(random.choice(bot.quotes['dictionary_no_results']))
        return

    embed = discord.Embed()

    # Validate that the word exists and if it doesn't, show suggestions
    if not 'def' in js[0]:
        suggestions = js[:5]

        for i, suggestion in enumerate(suggestions):
            suggestions[i] = '• %s' % suggestion

        embed.description = '*%s*' % '\n\n'.join(suggestions)
        await ctx.send(random.choice(bot.quotes['dictionary_try_this']), embed=embed)
        return

    embed.title = word
    embed.url = '%s/%s' % (bot.assets['merriam-webster']['dictionary_url'], word_encoded)
    embed.description = ''

    for category in js[:2]:
        if not 'def' in category or not 'hwi' in category:
            continue

        pronunciation = category['hwi']['hw']
        definitions = category['def']

        embed.description = '%s►  *%s*' % (embed.description, pronunciation.replace('*', '・'))

        if 'fl' in category:
            embed.description = '%s\n\n__**%s**__' % (embed.description, category['fl'].upper())

        for subcategory in definitions:
            similar_meaning_string = ''
            for similar_meanings in subcategory['sseq']:
                for meaning in similar_meanings:
                    meaning_item = meaning[1]

                    if isinstance(meaning_item, typing.List):
                        meaning_item = meaning_item[0]

                    meaning_position = 'sn' in meaning_item and meaning_item['sn'] or '1'

                    if not meaning_position[0].isdigit():
                        meaning_position = '%s%s' % ('\u3000', meaning_position)

                    # Get definition
                    if isinstance(meaning_item, typing.List):
                        definition = meaning_item[1]['dt'][0][1]
                    elif 'dt' in meaning_item:
                        definition = meaning_item['dt'][0][1]
                    elif 'sense' in meaning_item:
                        definition = meaning_item['sense']['dt'][0][1]
                    else:
                        definition = ', '.join(meaning_item['sls'])

                    if isinstance(definition, typing.List):
                        definition = definition[0][0][1]

                    # Format bullet point
                    similar_meaning_string += '%s: %s\n' % (meaning_position, definition)

            embed.description = '%s\n**%s**\n%s' % (embed.description, 'vd' in subcategory and subcategory['vd']
                                                    or 'definition', formatDictionaryOddities(similar_meaning_string, 'merriam'))

        # Add etymology
        if 'et' in category:
            etymology = category['et']
            embed.description = '%s\n**%s**\n%s\n\n' % (embed.description, 'etymology', formatDictionaryOddities(etymology[0][1], 'merriam'))
        else:
            embed.description = '%s\n\n' % embed.description

    await ctx.send(embed=embed)


def formatDictionaryOddities(txt, which):
    """Trim weird markup from dictionary entries"""

    if which == 'merriam':
        # Properly format words encased in weird characters

        # Remove all filler
        txt = re.sub(r'\{bc\}|\*', '', txt)

        while True:
            matches = re.findall(r'({[a-z_]+[\|}]+([a-zÀ-Ž\ \-\,]+)(?:{\/[a-z_]*|[a-z0-9\ \-\|\:\(\)]*)})', txt, re.IGNORECASE)

            if not len(matches) > 0:
                txt = re.sub(r'\{\/?[a-z\ _\-]+\}', '', txt)
                print(txt)
                return txt

            for match in matches:
                txt = txt.replace(match[0], '*%s*' % match[1].upper())
    elif which == 'urban':
        txt = txt.replace('*', '\*')

        matches = re.findall(r'(\[([\w\ ’\']+)\])', txt, re.IGNORECASE)
        for match in matches:
            txt = txt.replace(match[0], '[%s](%s%s)' % (match[1], bot.assets['urban_dictionary']['dictionary_url'], urllib.parse.quote(match[1])))

        return txt


@bot.command(name='danbooru', aliases=['dan'])
async def search_danbooru(ctx, *args):
    """Search on danbooru!"""

    search = ' '.join(args)
    print('User searching for: %s' % search)

    posts = await board_search(tags=search, limit=3, random=True)

    if not posts:
        await ctx.send('Sorry, nothing found!')
        return

    for post in posts:
        print('Parsing post #%i...' % post['id'])
        post_tags = post['tag_string_general'].split()
        for tag_lacking_preview in bot.rules['no_preview_tags']:
            if tag_lacking_preview in post_tags:
                try:
                    fileurl = post['file_url']
                # Exception needs error type
                except Exception:
                    # this is wrong because post['source'] looks like this: 'https://i.pximg.net/img-original/img/2019/02/19/22/30/59/73277959_p3.png'
                    # fileurl = 'https://danbooru.donmai.us%s' % post['source']
                    fileurl = post['source']
                break
            else:
                fileurl = 'https://danbooru.donmai.us/posts/%i' % post['id']

        if '/data/' in fileurl or 'raikou' in fileurl:
            embed = discord.Embed()
            post_char = re.sub(r' \(.*?\)', '', combine_tags(post['tag_string_character']))
            post_copy = combine_tags(post['tag_string_copyright'])
            post_artist = combine_tags(post['tag_string_artist'])
            embed_post_title = ''

            if post_char:
                embed_post_title += post_char

            if post_copy:
                if not post_char:
                    embed_post_title += post_copy
                else:
                    embed_post_title += ' (%s)' % post_copy

            if post_artist:
                embed_post_title += ' drawn by %s' % post_artist

            if not post_char and not post_copy and not post_artist:
                embed_post_title += '#%s' % post['id']

            embed_post_title += ' - Danbooru'
            if len(embed_post_title) >= bot.assets['danbooru']['max_embed_title_length']:
                embed_post_title = embed_post_title[:bot.assets['danbooru']['max_embed_title_length'] - 3] + '...'

            embed.title = embed_post_title
            embed.url = 'https://danbooru.donmai.us/posts/%i' % post['id']
            embed.set_image(url=fileurl)
            await ctx.send('<%s>' % embed.url, embed=embed)
        else:
            await ctx.send(fileurl)

        print('Parse of #%i complete' % post['id'])


@bot.command(name='temperature', aliases=['temp'])
async def report_bot_temp(ctx):
    """Show the bot's current temperature"""

    try:
        current_temp = subprocess.run(['vcgencmd', 'measure_temp'], stdout=subprocess.PIPE, universal_newlines=True)
    except FileNotFoundError:
        current_temp = subprocess.run(['sensors'], stdout=subprocess.PIPE, universal_newlines=True)

    await ctx.send(current_temp.stdout)


@bot.command(name='last')
async def talk_status(ctx):
    """Mention a brief summary of the last used channel"""
    await ctx.send('Last channel: %s\nCurrent count there: %s' % (channel_activity.last_channel, channel_activity.count))


@bot.command(aliases=['ava'])
async def avatar(ctx):
    """Display the avatar of an user"""

    embed = discord.Embed()
    embed.set_image(url=ctx.message.author.avatar_url)
    embed.set_author(
        name='%s #%i' % (ctx.message.author.name, int(ctx.message.author.discriminator)),
        icon_url=ctx.message.author.avatar_url
    )
    await ctx.send(embed=embed)


@bot.command()
async def uptime(ctx):
    """Mention the current uptime"""

    delta_uptime = datetime.utcnow() - bot.launch_time
    hours, remainder = divmod(int(delta_uptime.total_seconds()), 3600)
    minutes, seconds = divmod(remainder, 60)
    days, hours = divmod(hours, 24)
    await ctx.send('I\'ve been running for %i days, %i hours, %i minutes and %i seconds.' % (days, hours, minutes, seconds))


async def board_search(**kwargs):
    """Board searches handler

    Keywords:
        board::str
            Specify what board to search on, default is danbooru.
        post_id::int
            Used for searching by post id on a board
        tags::str
            Used for searching with tags on a board
        limit::int
            How many images to retrieve, default is 5
        random::bool
            Pick at random from results, default is False

    Returns:
        json::dict
    """

    board = kwargs.get('board', 'danbooru')
    post_id = kwargs.get('post_id')
    tags = kwargs.get('tags')
    limit = kwargs.get('limit', 5)
    random = kwargs.get('random', False)

    data = {
        'tags': tags,
        'limit': limit,
        'random': random
    }

    if board == 'danbooru':
        if post_id:
            url = 'https://danbooru.donmai.us/posts/%s.json' % post_id
            return await net.http_request(url, auth=danbooru_auth, json=True, err_msg='error fetching post #%s' % post_id)
        elif tags:
            return await net.http_request('https://danbooru.donmai.us/posts.json', auth=danbooru_auth, data=json.dumps(data), headers={"Content-Type": "application/json"}, json=True, err_msg='error fetching search: %s' % tags)


async def get_danbooru_gallery(msg, url):
    """Automatically fetch and post any image galleries from danbooru"""

    channel = msg.channel

    post_id = get_post_id(url, '/posts/', '?')

    if not post_id:
        return

    post = await board_search(post_id=post_id)

    if not post:
        return

    if post['has_children']:
        search = 'parent:%s order:id -id:%s' % (post['id'], post['id'])
    elif post['parent_id']:
        search = 'parent:%s order:id -id:%s' % (post['parent_id'], post['id'])
    else:
        return

    posts = await board_search(tags=search)

    total_posts = len(posts)
    posts_processed = 0

    for post in posts[:4]:
        print('Parsing post #%i...' % post['id'])
        posts_processed += 1

        if post['file_url']:
            fileurl = post['file_url']
        else:
            fileurl = post['source']

        embed = discord.Embed()
        post_char = re.sub(r' \(.*?\)', '', combine_tags(post['tag_string_character']))
        post_copy = combine_tags(post['tag_string_copyright'])
        post_artist = combine_tags(post['tag_string_artist'])
        embed_post_title = ''

        if post_char:
            embed_post_title += post_char

        if post_copy:
            if not post_char:
                embed_post_title += post_copy
            else:
                embed_post_title += ' (%s)' % post_copy

        if post_artist:
            embed_post_title += ' drawn by %s' % post_artist

        if not post_char and not post_copy and not post_artist:
            embed_post_title += '#%s' % post['id']

        embed_post_title += ' - Danbooru'
        if len(embed_post_title) >= bot.assets['danbooru']['max_embed_title_length']:
            embed_post_title = embed_post_title[:bot.assets['danbooru']['max_embed_title_length'] - 3] + '...'

        embed.title = embed_post_title
        embed.url = 'https://danbooru.donmai.us/posts/%i' % post['id']
        embed.set_image(url=fileurl)

        if posts_processed >= min(4, total_posts):
            if total_posts > 4:
                embed.set_footer(
                    text='%i+ remaining' % (total_posts - 4)
                    # icon_url=bot.assets['danbooru']['favicon']
                )
            else:
                embed.set_footer(
                    text=bot.assets['danbooru']['name']
                    # icon_url=bot.assets['danbooru']['favicon']
                )

        print('Parse of #%i complete' % post['id'])
        await channel.send(embed=embed)


async def get_twitter_gallery(msg, url):
    """Automatically fetch and post any image galleries from twitter"""

    channel = msg.channel

    post_id = get_post_id(url, '/status/', '?')
    if not post_id:
        return

    tweet = twitter_api.get_status(post_id, tweet_mode='extended')

    art.last_artist = art.Gaka()
    art.last_artist.twitter_id = tweet.author.id
    art.last_artist.twitter_name = tweet.author.name
    art.last_artist.twitter_screen_name = tweet.author.screen_name
    art.last_artist.twitter_profile_image_url_https = tweet.author.profile_image_url_https

    if not hasattr(tweet, 'extended_entities') or len(tweet.extended_entities['media']) <= 1:
        print('Preview gallery not applicable.')
        return

    print(msg.embeds)
    for e in msg.embeds:
        print(str(datetime.now()))
        print(dir(e))
        print(e.url)

    if not msg.embeds:
        print('I wouldn\'t have worked. Embeds report as 0 on the first try after inactivity on message #%i at %s.' % (msg.id, str(datetime.now())))
        # await channel.send('I wouldn't have worked')

    gallery_pics = []
    for picture in tweet.extended_entities['media'][1:]:
        if picture['type'] != 'photo':
            return

        # Appending :orig to get a better image quality
        gallery_pics.append(picture['media_url_https'] + ':orig')

    total_gallery_pics = len(gallery_pics)
    for picture in gallery_pics:
        total_gallery_pics -= 1

        embed = discord.Embed()
        embed.set_author(
            name='%s (@%s)' % (tweet.author.name, tweet.author.screen_name),
            url='https://twitter.com/%s' % tweet.author.screen_name,
            icon_url=tweet.author.profile_image_url_https
        )
        embed.set_image(url=picture)

        # If it's the last picture to show, add a brand footer
        if total_gallery_pics <= 0:
            embed.set_footer(
                text=bot.assets['twitter']['name'],
                icon_url=bot.assets['twitter']['favicon']
            )

        await channel.send(embed=embed)


async def get_pixiv_gallery(msg, url):
    """Automatically fetch and post any image galleries from pixiv"""

    channel = msg.channel

    post_id = get_post_id(url, 'illust_id=', '&')
    if not post_id:
        return

    print('Now starting to process pixiv link #%s' % post_id)
    if pixiv_api.access_token is None:
        pixiv_api.login(bot.auth_keys['pixiv']['username'], bot.auth_keys['pixiv']['password'])

    illust_json = pixiv_api.illust_detail(post_id, req_auth=True)
    print(illust_json)
    if 'error' in illust_json:
        # Attempt to login
        pixiv_api.login(bot.auth_keys['pixiv']['username'], bot.auth_keys['pixiv']['password'])
        illust_json = pixiv_api.illust_detail(post_id, req_auth=True)
        print(illust_json)

        if 'error' in illust_json:
            # too bad
            print('Invalid Pixiv id #%s' % post_id)
            return

    print('Pixiv auth passed! (for #%s)' % post_id)

    illust = illust_json.illust
    meta_dir = None

    if illust['meta_single_page']:
        meta_dir = 'meta_single_page'
    elif illust['meta_pages']:
        meta_dir = 'meta_pages'
    else:
        await channel.send('Sorry, sorry, sorry! Link missing data!')
        return

    total_illust_pictures = len(illust[meta_dir])
    if total_illust_pictures <= 1:
        illust[meta_dir] = [illust[meta_dir]]

    temp_wait = await channel.send('***%s***' % random.choice(bot.quotes['processing_long_task']))
    async with channel.typing():
        pictures_processed = 0
        for picture in illust[meta_dir][:4]:
            pictures_processed += 1
            print('Retrieving picture from #%s...' % post_id)

            try:
                img_url = picture.image_urls['medium']
            except AttributeError:
                img_url = illust.image_urls['medium']

            image = await net.fetch_image(img_url, headers={'Referer': 'https://app-api.pixiv.net/'})

            print('Retrieved more from #%s (maybe)' % post_id)
            image_filename = get_file_name(img_url)
            embed = discord.Embed()
            embed.set_author(
                name=illust['user']['name'],
                url='https://www.pixiv.net/member.php?id=%i' % illust['user']['id']
            )
            embed.set_image(url='attachment://%s' % image_filename)

            if pictures_processed >= min(4, total_illust_pictures):
                if total_illust_pictures > 4:
                    embed.set_footer(
                        text='%i+ remaining' % (total_illust_pictures - 4),
                        icon_url=bot.assets['pixiv']['favicon']
                    )
                else:
                    embed.set_footer(
                        text=bot.assets['pixiv']['name'],
                        icon_url=bot.assets['pixiv']['favicon']
                    )

            await channel.send(file=discord.File(fp=image, filename=image_filename), embed=embed)

    await temp_wait.delete()
    print('DONE PIXIV!')


def get_post_id(url, word_to_match, trim_to):
    """Get post id from url"""

    if not word_to_match in url:
        return False

    return url.split(word_to_match)[1].split(trim_to)[0]


def combine_tags(tags):
    """Combine tags and give them a readable format"""

    tags_split = tags.split()[:5]

    if len(tags_split) > 1:
        joint_tags = ', '.join(tags_split[:-1])
        joint_tags += ' and %s' % tags_split[-1]
        return joint_tags.strip().replace('_', ' ')

    return ''.join(tags_split).strip().replace('_', ' ')


def get_urls(string):
    """findall() has been used with valid conditions for urls in string"""

    regex_exp = r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\(\), ]|(?:%[0-9a-fA-F][0-9a-fA-F]))+'
    matching_urls = re.findall(regex_exp, string)
    return matching_urls


def get_domains(array):
    """Get domains from a link
    thanks dude https://stackoverflow.com/questions/9626535/get-protocol-host-name-from-url#answer-36609868"""

    domains = []

    for url in array:
        domain = url.split('//')[-1].split('/')[0].split('?')[0]
        domains.append(domain)
    return domains


def get_file_name(url):
    """Get file name from url"""

    return url.split('/')[-1]


'''
async def lookup_pending_posts():
    await bot.wait_until_ready()

    pending_posts = []

    safe_channels = []
    for channel in bot.tasks['danbooru']['safe_channels']:
        new_channel = bot.get_channel(int(channel))
        safe_channels.append(new_channel)

    nsfw_channels = []
    for channel in bot.tasks['danbooru']['nsfw_channels']:
        new_channel = bot.get_channel(int(channel))
        nsfw_channels.append(new_channel)

    while not bot.is_closed():
        posts = danbooru_api.post_list(tags=bot.tasks['danbooru']['tag_list'], page=1, limit=5, random=True)

        safe_posts = []
        nsfw_posts = []
        for post in posts:
            if not post['id'] in pending_posts:
                pending_posts.append(post['id'])
                if post['rating'] is 's':
                    safe_posts.append('https://danbooru.donmai.us/posts/%i' % post['id'])
                else:
                    nsfw_posts.append('https://danbooru.donmai.us/posts/%i' % post['id'])

        safe_posts = '\n'.join(safe_posts)
        nsfw_posts = '\n'.join(nsfw_posts)

        if safe_posts:
            for channel in safe_channels:
                await channel.send('Here are some posts to take into consideration:\n%s' % safe_posts)

        if nsfw_posts:
            for channel in nsfw_channels:
                await channel.send('Here are some posts to take into consideration:\n%s' % nsfw_posts)

        await asyncio.sleep(60 * 5)
'''


async def convert_to_si(msg):
    """Convert imperial units to SI"""

    regex_exp = r'(([0-9]+(?:\.?[0-9]+)?\ *(?:\'|foot|feet|ft))(?:\ *(?:and)?\ *)?([0-9]+(?:\.?[0-9]+)?\ *(?:"|inches|inch|in))|([0-9]+(?:\.?[0-9]+)?\ *(?:\'|foot|feet|ft))|([0-9]+(?:\.?[0-9]+)?\ *(?:"|inches|inch|in)))'
    results = re.findall(regex_exp, msg.content)

    if not results:
        return

    channel = msg.channel
    conversion_str = random.choice(bot.quotes['converting_units']) + '```'

    for match in results:
        units = {
            'feet': match[1] or match[3],
            'inches': match[2] or match[4],
        }
        converted_units = {
            'meters': 0,
            'feet': 0,
            'inches': 0,
        }

        for key in units:
            if not units[key]:
                continue

            units[key] = float(re.match(r'\d+\.?\d*', units[key]).group(0))

        if units['feet']:
            converted_units['meters'] += units['feet'] * 0.3048

        if units['inches']:
            converted_units['meters'] += units['inches'] * 0.0254

        conversion_str += '\n%s → %0.4fm' % (match[0], converted_units['meters'])

    # Random chance for final quote, 50% chance
    if not random.getrandbits(1):
        conversion_str += '```\n' + random.choice(bot.quotes['converting_units_modest'])
    else:
        conversion_str += '```'

    await channel.send(conversion_str)


@bot.event
async def on_message(msg):
    """Searches messages for urls and certain keywords"""

    # Prevent bot from spamming itself
    if msg.author.bot:
        return

    # Test for units
    await convert_to_si(msg)

    # Test for image urls
    urls = get_urls(msg.content)
    if urls:
        domains = get_domains(urls)
        for i, domain in enumerate(domains):
            if bot.assets['twitter']['domain'] in domain:
                await get_twitter_gallery(msg, urls[i])

            if bot.assets['pixiv']['domain'] in domain:
                await get_pixiv_gallery(msg, urls[i])

            if bot.assets['danbooru']['domain'] in domain:
                await get_danbooru_gallery(msg, urls[i])

    if channel_activity.last_channel != msg.channel.id or urls:
        channel_activity.last_channel = msg.channel.id
        channel_activity.count = 0

    channel_activity.count += 1

    if str(msg.channel.id) in bot.rules['quiet_channels']:
        if not channel_activity.warned and channel_activity.count >= bot.rules['quiet_channels'][str(msg.channel.id)]['max_messages_without_embeds']:
            channel_activity.warned = True
            await msg.channel.send(random.choice(bot.quotes['quiet_channel_past_threshold']))

    await bot.process_commands(msg)


@bot.event
async def on_ready():
    """On bot start"""

    print('ready!')
    # Change play status to something fitting
    await bot.change_presence(activity=discord.Game(name='with books'))

# bot.loop.create_task(lookup_pending_posts())
bot.run(bot.auth_keys['discord']['token'])
