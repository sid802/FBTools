__author__ = 'Sid'
import re

# Regexes
class FBRegexes(object):
    my_fid = re.compile(r'"USER_ID":"(?P<result>\d+)')
    json_from_html = re.compile(r'(?P<json>\{.*\})', re.MULTILINE)
    privacy = re.compile(r':\s*(?P<result>.*)')
    picture_timestamp = re.compile(r'(?P<result>\d+),"text')

    url_user = re.compile(r'\.com/(?P<result>[\w.-]+)')
    url_group_username = re.compile(r'\.com/groups/(?P<result>[\w.-]+)')

    # Likers
    liker_fid_from_url = re.compile(r'php\?id=(?P<result>\d+)')  # url comes from user_fid_url xpath
    liker_username_from_url = re.compile(r'facebook\.com\/(?P<result>[\w.]+)')  # url comes from user_username_url

# Xpaths
class FBXpaths(object):

    # User links
    #user_liker_links = '//li[@class="fbProfileBrowserListItem"]//a[@data-gt]'
    user_liker_links = '//a[@data-gt]'
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
    photo_caption_theater = '//span[@class="hasCaption"]//text()'
    photo_caption_normal = '//div[contains(@class,"userContentWrapper")]//div[contains(@class,"userContent")]//text()'

    # Friends
    friends_links = '//div/a[@data-gt and @data-hovercard]'

    # Pages
    page_title = '//h1/span[1]/text()'
    page_likers_amount = '//a[contains(@href,"likes")]/div[1]/text()'
    page_likers_amount_secondary = '//span[@id="PagesLikesCountDOMID"]//text()'
    page_short_desc = '//div[contains(text(), "Short Description")]/../../div[2]/div/text()'
    page_desc_is_split = '//span[@class="text_exposed_show"]'
    page_long_desc_split = '(//div[contains(text(), "Long Desc")]/../../div[2]//*[not(contains(@class,"hide"))]/text())[position() <=2]'
    page_long_desc_unified = '//div[contains(text(), "Long Desc")]/../../div[2]//text()'

    # Groups
    group_title = '//h1[@id="seo_h1_tag"]/a/text()'
    group_members_amount = '//span[@id="count_text"]/text()'
    group_description = '//div[@id="groupsDescriptionBox"]//div[contains(@class,"text_exposed_root")]'
    group_category = '//div[@id="groupsDescriptionBox"]//div[@class="groupsEditDescriptionArea"]//div[3]/span/text()'
    group_privacy = '//div[@id="fbProfileCover"]//a[@data-hover]/span/text()'
    group_member_urls = '//a[@data-hovercard and not(@class)]'

    # Group Posts

    # xpath to full post, containing comments (a post has an attribute named 'data-ft' with a tl_objid key
    group_posts = "//div[contains(@id,'mall_post')]"
    post_author = ".//a[@data-hovercard and not(@tabindex)]"
    post_commenter = './/a[contains(@class,"UFIComment")]'
    post_comment_timestamp = './/abr[@class="livetimestamp"]/@data-utime'
    post_text = './/span[contains(@class,"UFICommentBody")]'  # Relative to comment
