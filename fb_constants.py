__author__ = 'Sid'
import re

# Regexes
class FBRegexes(object):
    my_fid = re.compile(r'"USER_ID":"(?P<result>\d+)')
    json_from_html = re.compile(r'\{.*\}', re.MULTILINE)
    liker_fid_from_url = re.compile(r'php\?id=(?P<result>\d+)')  # url comes from user_fid_url xpath
    liker_username_from_url = re.compile(r'facebook\.com\/(?P<result>[\w.]+)')  # url comes from user_username_url

# Xpaths
class FBXpaths(object):
    likers = '//li[@class="fbProfileBrowserListItem"]//a[@data-gt]'
    user_full_name = './text()'  # Relative to liker_info_element
    user_fid_url = './@data-hovercard'  # Relative to liker_info_element
    user_username_url = './@href'