__author__ = 'Sid'

##############################################
#
# Extract open facebook groups
#
# Extract anybody who posted/commented
# with the phone numbers/emails he posted
#
##############################################

import re, time, sys, json, os
from base64 import b64encode
from HTMLParser import HTMLParser
from datetime import datetime

sys.path.append(r'C:\Users\Sid\Documents\GitHub\PhoneExtractor')
import canonization
from selenium import webdriver
from lxml import html
from mysql import connector
import fb_constants as constants

import export_to_file
from fb_main import *
from fb_main import _stronger_value, _default_vs_new, blankify
import fb_group_parser
from fb_group_posters_importer import import_dir


# Constants
_USERNAME = 'username_from_url'
_FID = 'fid_from_url'
_POST_ID = 'post_id'

# Exceptions
class ClosedGroupException(Exception):
    def __init__(self, message):
        super(ClosedGroupException, self).__init__(message)


class FBGroupInfosParser(FBParser):
    def __init__(self, group_ids, reload_amount):
        super(FBGroupInfosParser, self).__init__(self.__class__.__name__, './logs')
        self.reload_amount = reload_amount
        self.group_ids = group_ids
        self.driver = None
        self._regexes = self._init_regexes()
        self._xpaths = self._init_xpaths()
        self._canonizers = canonization.create_all_canonizers()
        self._html_parser = HTMLParser()

    def _init_regexes(self):
        """
        :return: dictionary of compiled regexes
        """

        regexes = {}

        # Extracts user id from facebook homepage
        regexes['my_id'] = re.compile(r'"USER_ID":"(?P<result>\d+)')

        # Doesn't extract fid if no username found. ON PURPOSE
        regexes['username_from_url'] = re.compile(r'facebook\.com/(?P<result>[\w.]+)')

        # Extracts fid from data-hover attribute (/ajax/hovercard/user.php?id=785737849&extragetparams=)
        regexes['fid_from_url'] = re.compile(r'\?id=(?P<result>\d+)')

        # Finds emails
        regexes['emails'] = re.compile(r'([\w.-]+(@|&#064;)[\w-]{2,}(\.[\w-]{2,}){1,4})')

        # Extract post_id from id attribute
        regexes['post_id'] = re.compile(r'mall_post_(?P<result>\d+)')

        # Extract json from page source
        regexes['json_from_html'] = re.compile(r'[^{]*(?P<json>.*\})[^}]*$')

        return regexes

    def _init_xpaths(self):
        """
        :return: dictionary of xpaths
        """

        xpaths = {}

        # xpaths to the content itself and the comment section
        xpaths['post_content'] = ".//p/parent::*"

        # Author Xpath's. Relative to post
        xpaths['post_author'] = './/a[@data-hovercard][2]'  # First is link from picture, without name
        xpaths['author_username'] = './@href'  # URL's need further parsing
        xpaths['author_fid'] = './@data-hovercard'
        xpaths['author_fullname'] = './text()'

        # Comment Xpath's
        xpaths['post_comments'] = ".//div[contains(@class, 'UFIContainer')]//div[@class='UFICommentContent']"
        xpaths['comment_author_fid'] = './@data-hovercard'  # URL's need further parsing, relative to meta
        xpaths['comment_author_username'] = './@href'  # URL's need further parsing, relative to meta
        xpaths['comment_author_fullname'] = './span/text()'  # relative to meta

        xpaths['post_timestamp'] = './/abbr/@data-utime[1]'  # Relative to post
        xpaths['post_id'] = './@id'  # Relative to post, needed further parsing

        return xpaths

    def _parse_from_xpath(self, xpath_result, target_parse):
        """
        :param xpath_result: List containing Url with username (should have only 1 string)
        :param target_parse: string of what you want to parse ('fid'/'username'/'post_id' or _USERNAME/_FID/_POST_ID)
        :return: Parsed username if exists
        """

        if not xpath_result:
            return ''

        regex = self._regexes[target_parse]

        match = regex.search(xpath_result[0])  # Choose only first result from list
        if not match:
            return ''

        result = match.group('result')

        if target_parse == _USERNAME and result == 'profile.php':
            return ''

        return result

    def _parse_author(self, post_node):
        """
        :param post_node: Node representing the current post (Xpath)
        :return: UserInfo instance for author
        """
        post_author_nodes = post_node.xpath(constants.FBXpaths.post_author)
        if not post_author_nodes:
            return None

        post_author = post_author_nodes[0]
        return self._parse_user_from_link(post_author)


    def _parse_commenter(self, post_node):
        """
        :param post_node: Html node representing the current post
        :return: UserInfo instance - only USER
        """

        post_author_nodes = post_node.xpath(constants.FBXpaths.post_commenter)
        if not post_author_nodes:
            return None

        post_author = post_author_nodes[0]
        poster = self._parse_user_from_link(post_author)

        return UserInfo(fb_user=poster)

    def _parse_phones(self, text):
        """
        :param text: source to extract phone numbers from
        :return: set of tuples containig canonized phone number and country
        """
        info_tuples = set()

        for country, canonizer in self._canonizers.iteritems():
            # Find all phone numbers and canonize
            country_phone = canonizer._country_phone
            finding_regex = country_phone.to_find_regex(is_strict=False, is_canonized=False,
                                                        optional_country=True, stuck_zero=True)

            phone_matches = finding_regex.finditer(text)
            for phone_match in phone_matches:
                phone = phone_match.group('phone')
                canonized_phone_lst = canonizer.canonize(phone)
                for canonized_phone in canonized_phone_lst:
                    info_tuples.add((phone, canonized_phone, '{0}_phone'.format(country)))

        return info_tuples

    def _parse_emails(self, text):
        """
        :param text: source to extract emails from
        :return: set of emails
        """

        info_tuples = set()

        emails = self._regexes['emails'].findall(text)
        for email in emails:
            canonized_email = email[0].replace('#&064;', '@').lower()  # email is a tuple. email[0] is full email
            canonized_email = canonized_email.strip('.')
            info_tuples.add((canonized_email, canonized_email.lower(), 'email'))

        return info_tuples

    def _parse_info_from_text(self, text):
        """
        :param text: Text to extract info from
        :return: list of tuple info
        """

        info_tuples = self._parse_phones(text)
        emails = self._parse_emails(text)

        # Union all infos
        info_tuples.update(emails)

        return info_tuples

    def _parse_info_from_node(self, post_node):
        """
        :param post_node: Html node representing the current post
        :return: list of tuple info
        """

        post_content_lst = post_node.xpath(self._xpaths['post_content'])
        post_content = '\n'.join(map(lambda x: x.text_content(), post_content_lst))

        return self._parse_info_from_text(post_content)

    def _parse_author_user_info(self, post_node):
        """
        :param post_node: Html node representing the current post
        :return: UserInfo instance (names, info)
        """

        user = self._parse_author(post_node)
        user_infos = UserInfo(fb_user=user)
        user_infos.infos = self._parse_info_from_node(post_node)
        return user_infos

    def _parse_user_infos_from_comments(self, comments_xpath):
        """
        :param comments_xpath: xpath containing all comments
        :return: distinct user_infos who commented
        """

        all_commenters = set()  # Set of user_info's

        for comment in comments_xpath:
            user_info = self._parse_commenter(comment)
            comment_content_lst = comment.xpath(constants.FBXpaths.post_text)
            if comment_content_lst:
                comment_content = comment_content_lst[0].text_content()
                infos = self._parse_info_from_text(comment_content)
                user_info.infos = infos

            all_commenters.add(user_info)

        return all_commenters

    def _parse_max_timestamp_from_comments(self, comments):
        """
        :param comment: Xpath list of all comment
        :return: int - Maximum timestamp of the comments. 0 if no comment exists
        """

        timestamps = map(lambda comment: comment.xpath(constants.FBXpaths.post_comment_timestamp), comments)
        if len(timestamps) == 0:
            return 0
        return max(filter(lambda x: len(x) > 0, timestamps))


    def _parse_post(self, group, author, post_xpath):
        """
        :param post_xpath: xpath node for current post
        :param group: FBGroup where post was posted
        :param author: FBUser who is the post's author
        :return: Post instance
        """

        timestamp_unix_str = post_xpath.xpath(self._xpaths['post_timestamp'])

        if not timestamp_unix_str:
            timestamp = None
        else:
            timestamp = int(timestamp_unix_str[0])

        post_id_path = post_xpath.xpath(self._xpaths['post_id'])
        post_id = self._parse_from_xpath(post_id_path, _POST_ID)
        return FBPost(id=post_id, group=group, author=author, date_time=timestamp), timestamp

    def _parse_page(self, group, parse_src, output_file):
        """
        :param group: current Group instance
        :param parse_src: src (string) to parse from
        :param output_file: handle to file where to write the results
        :return: Tuple of last parsed post's id, its maximum associated timestamp (post and its comments) and amount of parsed posts
        """

        html_tree = html.fromstring(parse_src)

        all_posts = html_tree.xpath(constants.FBXpaths.group_posts)
        if not all_posts:
            raise ClosedGroupException("Probably got to a Closed group")

        last_timestamp = None

        for post in all_posts:
            author_info = self._parse_author_user_info(post)

            previous_timestamp = last_timestamp  # Save previous in case current is None
            current_post, last_timestamp = self._parse_post(group, author_info, post)

            if not last_timestamp:
                last_timestamp = previous_timestamp  # last_timestamp is previous again (which isn't None)

            comments = post.xpath(self._xpaths['post_comments'])
            commenters_infos = self._parse_user_infos_from_comments(comments)
            max_comment_timestamp = self._parse_max_timestamp_from_comments(comments)
            last_timestamp = max(max_comment_timestamp, last_timestamp)

            current_post.commenters = commenters_infos
            current_post.author = author_info  # Switch default author parsing with FBUser, to UserInfo

            export_to_file.write_user_post(current_post, output_file)

        return current_post.fid, last_timestamp, len(all_posts)

    def _get_next_url(self, posts_extracted, last_post_id, last_timestamp, group_id, user_id, reload_id):
        """
        :param posts_extracted: int - amount of posts
        :param last_post_id: id of the last post extracted
        :param last_timestamp: unix timestamp of the latest comment on the last post extracted (post timestamp if no comment)
        :param group_id: group_id of group we are currently extracting
        :param user_id: user id of current connected user
        :param reload_id: index of current reload (starts with 1)
        :return: formatted string
        """

        # Deprecated in 27/06/2016
        """
        base_url = (
            'https://www.facebook.com/ajax/pagelet/generic.php/GroupEntstreamPagelet?__pc=EXP1:react_composer_pkg'
            '&ajaxpipe=1&ajaxpipe_token=AXhY1JWsfBFKhhsj&no_script_path=1'
            '&data={{"last_view_time":0,"is_file_history":null,"is_first_story_seen":true,"end_cursor":"{cursor}",'
            '"group_id":{g_id},"has_cards":true,"multi_permalinks":[],"post_story_type":null}}&__user={user_id}&__a=1'
            '&__dyn=7AmajEzUGBym5Q9UoHaEWC5ECiq2WbF3oyupFLFwxBxCbzES2N6y8-bxu3fzoaqwFUgx-y28b9J1efKiVWxe6okzEswLDz8Sm2uVUKmFAdAw'
            '&__req=jsonp_{reload}&__rev=2071590&__adt={reload}')
        """

        # Deprecated 12/10/2016
        """
        base_url = (
            'https://www.facebook.com/ajax/pagelet/generic.php/GroupEntstreamPagelet?'
            'data={{"end_cursor":"{cursor}","group_id":{g_id},"multi_permalinks":[]}}'
            '&__user={user_id}&__a=1&__adt={reload}'
        )
        """

        base_url = (
            'https://www.facebook.com/ajax/pagelet/generic.php/GroupEntstreamPagelet?'
            'data={{"last_view_time":0,"is_file_history":null,"is_first_story_seen":true,"permalink_story_index":{n_index},'
            '"end_cursor":"{cursor}","group_id":{g_id},'
            '"has_cards":true,"multi_permalinks":[],"posts_visible":{p_extracted}}}&__user={u_id}&__a=1'
            '&__dyn=7AmajEzUGByA5Q9UoHaEWC5EWq2WiWF3oyeqrWo8popyUWdwIhE98nwgUaqwHx24UJi28rxuF8W49XDG4XzErz8iGta3iaVVojxCVEiHWCDxh1rDAzUO5u5od8a8Cium8yUgx66EK3O69L-6Z1im7WxWKiaggzETxqayoHypFu6Gx2'
            '&__req=jsonp_{reload}&__rev=2732669&__adt={reload}'
        )


        cursor = "{timestamp}:{post_id}::".format(timestamp=last_timestamp,
                                                  post_id=last_post_id)  # Remove 3 hours from current timestamp (Thats what it does from research)
        if last_post_id is None and last_timestamp is None:
            encoded_cursor = ""
        else:
            encoded_cursor = b64encode(cursor)

        return base_url.format(
            n_index=posts_extracted + 1,
            cursor=encoded_cursor,
            p_extracted=posts_extracted,
            g_id=group_id,
            u_id=user_id,
            reload=reload_id
        )

    def _parse_group(self, group, last_timestamp_unix, user_id, output, reload_amount=400):
        """
        parse single group
        returns true if it got to a page there wasn't anything to extract (It got to the bottom)
        return false if it didn't get to the end
        """

        group_url = 'https://facebook.com/{id}'.format(id=group.fid)
        if not group.fid in self.driver.current_url:
            self.driver.get(group_url)
            time.sleep(5)

        reload_id = 2
        last_post_id = 0  # Init
        last_timestamp = int(time.time())  # Current timestamp
        parsed_posts = 0

        #TODO: Test with first load, test get_next_url and script itself!

        for i in xrange(1, reload_amount + 1):
            # Parse reload_amount of pages

            next_url = self._get_next_url(parsed_posts, last_post_id, last_timestamp, group.fid, user_id, reload_id)
            self._logger.getLogger().debug("Next url is: {0}".format(next_url))

            reload_id += 1
            self.driver.get(next_url)

            page_source = self._get_page_source(self.driver)
            payload = self._parse_payload_from_ajax_response(page_source,
                                                             source='group_posts')
            if payload is None:
                if isinstance(output, file):
                    output.flush()
                raise Exception("Next json payload couldn't be loaded")
            payload_html = self._fix_payload(payload)  # Get unicode strings

            try:
                result_tuple = self._parse_page(group, payload_html, output)
            except html.etree.XMLSyntaxError:
                # Probably got to the end
                if isinstance(output, file):
                    output.flush()
                return True, i

            if last_post_id == result_tuple[0]:
                # Stop script from looping for ever
                #TODO: Make sure it doesn't quit before it should
                if isinstance(output, file):
                    output.flush()
                return False, i

            last_post_id, last_timestamp, parsed_posts = result_tuple

            if last_timestamp is not None and last_timestamp < last_timestamp_unix:
                # From here on, posts have already been written in DB
                if isinstance(output, file):
                    output.flush()
                return True, i

            if i % 10 == 0:
                # Flush each 10 pages
                if isinstance(output, file):
                    output.flush()

        if isinstance(output, file):
            output.flush()
        return False, i

    @staticmethod
    def _get_page_source(driver):
        """
        :param driver: Selenium Driver
        :return: page source.
        Retries 5 times if page_source is empty
        """
        retries = 0
        page_source = driver.page_source
        while len(page_source) == 0 and retries < 5:
            page_source = driver.page_source
            time.sleep(1.5)
            retries += 1
        return page_source



    def _parse_all_groups(self, user_id, reload_amount=400):
        """
        start parsing the groups
        """
        reload_amount = _stronger_value(self.reload_amount, reload_amount)
        output_path = 'logs/output_{0}.NEW.txt'.format(datetime.now().strftime('%Y%m%d-%H%M%S'))
        for group_id, last_post_unix in self.group_ids:
            parser = fb_group_parser.FBGroupParser()
            parser.set_driver(self.driver)

            try:
                current_group = parser.parse_group(group_id)
            except fb_group_parser.FBGroupParseError:
                self._logger.getLogger().error("Couldn't parse title of group: {0}".format(group_id))
                continue

            posts_in_page = html.fromstring(self.driver.page_source).xpath(constants.FBXpaths.group_posts)
            if len(posts_in_page) == 0 and 'closed' in current_group.privacy.lower():
                self._logger.getLogger().warn(u"The group is closed. This script only parses open groups!")
                continue

            try:
                export_to_file.write_group_start(current_group, self._logger.getLogger())
                self._logger.getLogger().info(u'Starting to parse group: {0}'.format(current_group.title))
                absolute_crawl = self._parse_group(current_group, last_post_unix, user_id, self._logger.getLogger(), reload_amount=reload_amount)
                if absolute_crawl[0]:
                    export_to_file.write_absolute_parse(current_group, self._logger.getLogger())
                export_to_file.write_group_end(current_group, self._logger.getLogger())
                self._logger.getLogger().info(u'Done parsing group: {0}, Parsed everything: {1}'
                                              .format(current_group.title, absolute_crawl))

            except ClosedGroupException:
                # Shouldn't get here unless the FB page isn't in english
                self._logger.getLogger().warn(u"The group is closed. This script only parses open groups!")
                export_to_file.write_group_end(current_group, self._logger.getLogger())
                continue
        self._logger.getLogger().info(u'Log path is: {0}'.format(os.path.abspath(output_path)))



    @FBParser.browser_needed
    def run(self, email, password, reload_amount=None):
        """
        start running the parser
        :return: Full path to log with results
        """
        reload_amount = _stronger_value(self.reload_amount, reload_amount)
        my_id = self.init_connect(email, password)  # Connect to facebook

        if my_id is None:
            raise Exception("User id not found in homepage")
        logger.init_logger()
        self._parse_all_groups(user_id=my_id, reload_amount=reload_amount)
        logger.close_handlers()
        self.driver.quit()


class UserInfo(object):
    """
    class to contain user info
    """
    
    def __init__(self, fb_user):
        self.user = fb_user
        self.infos = set()  # will contain tuples containing (origina_info, canonized_info, info_kind). EX: (0475-864-285, 32475864285, 'belgian_phone')


class UserPost(object):
    """
    Class to contain POST info
    """

    def __init__(self, author, group, post, commenters):
        self.author = author  # FBUser
        self.commenters = commenters
        self.post = post  # Post instance
        self.group = group  # Group instance


def get_group_ids():
    """
    get group ids. allow only number, allow many group ids in one time
    """
    pattern = re.compile(r'\d{6,}')
    group_ids = set()
    group_id = raw_input("Enter group id(s):\n")
    while group_id not in ['', 'done', 'exit']:
        current_ids = pattern.findall(group_id)  # Find all group ids entered
        map(lambda x: group_ids.add((x, 0)), current_ids)  # add them to set. 0 is to indicate to parse everything
        group_id = raw_input("Enter group id(s): ")
    
    return group_ids


def get_user_info():
    """
    Get user's email/password
    :return tuple of (email, password)
    :rtype TUPLE
    """
    email_pattern = re.compile(r'[\w.-]+@[\w-]{2,}(\.[\w-]{2,}){1,4}')
    email = raw_input("Enter you email: ")
    while not email_pattern.match(email.strip()):
        email = raw_input("Enter you email: ")
    
    password = raw_input("Enter your password: ")
    
    return email, password


def get_reload_amount():
    """
    get the maximal amount of time you want to load next page in group
    """
    
    amount = raw_input("Enter the amount of pages you want to load in each group: ")
    while not amount.isdigit():
        amount = raw_input("Enter the amount of pages you want to load in each group: ")
    return int(amount)

def main(params_dict=None):
    """
    Gets input for script
    :param params_dict: dicts with group_ids, email, password and reload_amount
    """
    if params_dict is None:
        group_ids = get_group_ids()  # gets a set
        email, password = get_user_info()
        amount = get_reload_amount()
    else:
        group_ids = params_dict['group_ids']
        email = params_dict['email']
        password = params_dict['password']
        amount = params_dict['reload_amount']

    group_parser = FBGroupInfosParser(group_ids=group_ids, reload_amount=amount)
    group_parser.run(email, password)
    import_dir(logger.log_directory)


    raw_input('Enter anything to finish')


def get_wanted_group_ids():
    """
    :return: Queries MySql DB for latest group id's and timestamp of every last post extracted
    """

    conn = connector.connect(user='root',
                             password='hujiko',
                             host='127.0.0.1',
                             database='facebook')

    cursor = conn.cursor()

    QUERY = """
            SELECT
                id,
                UNIX_TIMESTAMP(last_info_extraction),
                last_info_extraction
            FROM
                facebook.group_summary
            ORDER BY last_info_extraction IS NULL DESC , LAST_INFO_EXTRACTION ASC
            LIMIT 10
            """

    cursor.execute(QUERY)
    results = cursor.fetchall()

    results_set = set()

    for result in results:
        group_id, timestamp_unix, _ = result

        # Set oldest timestamp we want to parse (older posts won't be parsed)
        if timestamp_unix is None:
            last_timestamp = None
        else:
            last_timestamp = timestamp_unix - 60 * 60 * 2  # Remove 2 hours from timestamp to be sure not to miss any posts
        results_set.add((group_id, last_timestamp))

    conn.close()

    return results_set

if __name__ == '__main__':
    if 2 <= len(sys.argv) <= 5:
        args = sys.argv[1:]

        if len(args) == 4:
            group_ids = [(args[3], None)]
        elif len(args) == 3:
            group_ids = get_wanted_group_ids()

        params_dict = dict(
            email=args[0],
            password=args[1],
            reload_amount=int(args[2]),
            group_ids=group_ids
        )

        main(params_dict)
    else:
        main()