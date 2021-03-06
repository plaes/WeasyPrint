# coding: utf8

#  WeasyPrint converts web documents (HTML, CSS, ...) to PDF.
#  Copyright (C) 2011  Simon Sapin
#
#  This program is free software: you can redistribute it and/or modify
#  it under the terms of the GNU Affero General Public License as
#  published by the Free Software Foundation, either version 3 of the
#  License, or (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU Affero General Public License for more details.
#
#  You should have received a copy of the GNU Affero General Public License
#  along with this program.  If not, see <http://www.gnu.org/licenses/>.


"""
Various utils.

"""

from __future__ import division, unicode_literals

import io
import base64

from cssutils.helper import path2url

from . import VERSION
from .logger import LOGGER
from .compat import (
    urljoin, urlparse, unquote_to_bytes, urlopen_contenttype, Request,
    parse_email)


HTTP_USER_AGENT = 'WeasyPrint/%s http://weasyprint.org/' % VERSION


def get_url_attribute(element, key):
    """Get the URL corresponding to the ``key`` attribute of ``element``.

    The retrieved URL is absolute, even if the URL in the element is relative.

    """
    attr_value = element.get(key)
    if attr_value:
        attr_value = attr_value.strip()
        if attr_value:
            return urljoin(element.base_url, attr_value)


def ensure_url(string):
    """Get a ``scheme://path`` URL from ``string``.

    If ``string`` looks like an URL, return it unchanged. Otherwise assume a
    filename and convert it to a ``file://`` URL.

    """
    if urlparse(string).scheme:
        return string
    else:
        return path2url(string.encode('utf8'))


def parse_data_url(url):
    """Decode URLs with the 'data' stream. urllib can handle them
    in Python 2, but that is broken in Python 3.

    Inspired from the Python 2.7.2’s urllib.py.

    """
    # syntax of data URLs:
    # dataurl   := "data:" [ mediatype ] [ ";base64" ] "," data
    # mediatype := [ type "/" subtype ] *( ";" parameter )
    # data      := *urlchar
    # parameter := attribute "=" value
    try:
        header, data = url.split(',', 1)
    except ValueError:
        raise IOError('bad data URL')
    header = header[5:]  # len('data:') == 5
    if header:
        semi = header.rfind(';')
        if semi >= 0 and '=' not in header[semi:]:
            content_type = header[:semi]
            encoding = header[semi+1:]
        else:
            content_type = header
            encoding = ''
        message = parse_email('Content-type: ' + content_type)
        mime_type = message.get_content_type()
        charset = message.get_content_charset()
    else:
        mime_type = 'text/plain'
        charset = 'US-ASCII'
        encoding = ''

    if encoding == 'base64':
        data = data.encode('ascii')
        data = base64.decodestring(data)
    else:
        data = unquote_to_bytes(data)

    return io.BytesIO(data), mime_type, charset


def urlopen(url):
    """Fetch an URL and return ``(file_like, mime_type, charset)``.

    It is the caller’s responsability to call ``file_like.close()``.
    """
    if url.startswith('data:'):
        return parse_data_url(url)
    else:
        return urlopen_contenttype(Request(url,
            headers={'User-Agent': HTTP_USER_AGENT}))


def urllib_fetcher(url):
    """URL fetcher for cssutils.

    This fetcher is based on urllib instead of urllib2, since urllib has
    support for the "data" URL scheme.

    """
    file_like, mime_type, charset = urlopen(url)
    if mime_type != 'text/css':
        LOGGER.warn('Expected `text/css` for stylsheet at %s, got `%s`',
                    url, mime_type)
        return None
    content = file_like.read()
    file_like.close()
    return charset, content


class cached_property(object):
    """A decorator that converts a function into a lazy property. The
    function wrapped is called the first time to retrieve the result
    and then that calculated result is used the next time you access
    the value.

    Stolen from Werkzeug:
    https://github.com/mitsuhiko/werkzeug/blob/7b8d887d33/werkzeug/utils.py#L28

    """

    def __init__(self, func):
        self.__name__ = func.__name__
        self.__module__ = func.__module__
        self.__doc__ = func.__doc__
        self.func = func

    def __get__(self, obj, type=None):
        if obj is None:
            return self
        missing = object()
        value = obj.__dict__.get(self.__name__, missing)
        if value is missing:
            value = self.func(obj)
            obj.__dict__[self.__name__] = value
        return value
