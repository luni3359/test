"""Handle network requests"""
import io

import aiohttp


async def http_request(url, **kwargs):
    """Make an http request"""

    auth = kwargs.get('auth')
    data = kwargs.get('data')
    headers = kwargs.get('headers')
    json = kwargs.get('json')
    err_msg = kwargs.get('err_msg')

    async with aiohttp.ClientSession(auth=auth) as session:
        async with session.get(url, data=data, headers=headers) as response:
            if response.status != 200:
                print('[%i] %s' % (response.status, err_msg))
                return False

            if json:
                return await response.json()

            return await response.read()


async def fetch_image(url, **kwargs):
    """Download an image"""

    img_bytes = io.BytesIO(await http_request(url, **kwargs))
    return img_bytes
