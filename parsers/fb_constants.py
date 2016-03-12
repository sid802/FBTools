__author__ = 'Sid'
import re

# Regexes
class FBRegexes(object):
    my_fid = re.compile(r'"USER_ID":"(?P<result>\d+)')
    json_from_html = re.compile(r'(?P<json>\{.*\})', re.MULTILINE)
    privacy = re.compile(r':\s*(?P<result>.*)')
    picture_timestamp = re.compile(r'(?P<result>\d+),"text')

    url_user = re.compile(r'\.com/(?P<result>[\w.-]+)')

    # Likers
    liker_fid_from_url = re.compile(r'php\?id=(?P<result>\d+)')  # url comes from user_fid_url xpath
    liker_username_from_url = re.compile(r'facebook\.com\/(?P<result>[\w.]+)')  # url comes from user_username_url

# Xpaths
class FBXpaths(object):

    # User links
    user_liker_links = '//li[@class="fbProfileBrowserListItem"]//a[@data-gt]'
    user_taggee_links = '//a[@class="taggee"]'

    # User link parts
    user_full_name = './text()'  # Relative to liker_info_element
    user_fid_url = './@data-hovercard'  # Relative to liker_info_element
    user_username_url = './@href'

    # privacy
    privacy_logged_in = '//div[contains(@aria-label,"Shared with")]/@aria-label'
    privacy_not_logged_in = '//a[contains(@data-tooltip-content,"Shared")]/@data-tooltip-content'

    # Photo author
    photo_author = '//a[@class="profileLink"]'

    # Pages
    page_title = '//h1/span[1]/text()'
    page_likers_amount = '//a[contains(@href,"likes")]/div[1]/text()'
    page_likers_amount_secondary = '//span[@id="PagesLikesCountDOMID"]//text()'
    page_short_desc = '//div[contains(text(), "Short Description")]/../../div[2]/div/text()'
    page_desc_is_split = '//span[@class="text_exposed_show"]'
    page_long_desc_split = '(//div[contains(text(), "Long Desc")]/../../div[2]//*[not(contains(@class,"hide"))]/text())[position() <=2]'
    page_long_desc_unified = '//div[contains(text(), "Long Desc")]/../../div[2]//text()'