__author__ = 'Sid'
from lxml import html
from parsers import fb_constants as constants
from fb_main import *
from fb_main import _default_vs_new, _stronger_value
from fb_df import *
import re
from time import sleep
from datetime import datetime
from mysql import connector

class FBGroupMeta(FBGroup):
    """
    Extension of FBGroup which adds metadata of the parsing itself
    """
    def __init__(self, fbid, username=None, title=None, privacy=None, description=None,
                 category=None, members_amount=None, members=None):
        super(FBGroupMeta, self).__init__(fbid, username, title, privacy, description,
                                            category, members_amount, members)
        self.meta = {'scrape_time': datetime.now()}

class FBGroupParseError(Exception):
    def __init__(self, message):
        super(FBGroupParseError, self).__init__(message)

class FBGroupParser(FBParser):
    """
    Class to parse FB Group metadata
    """

    def __init__(self, group_ids=None, extract_members=False, load_to_db=False):
        super(FBGroupParser, self).__init__(self.__class__.__name__, './logs')

        if group_ids is None:
            group_ids = []

        self.group_ids = group_ids  # list of strings
        self.extract_members = extract_members  # boolean
        self._load_to_db = load_to_db  # boolean, load info to DB as soon as its scraped
        if self._load_to_db:
            self._db_conn = connector.connect(user='root',
                                             password='hujiko',
                                             host='127.0.0.1',
                                             database='facebook')
            self._cursor = self._db_conn.cursor()

    @FBParser.browser_needed
    def parse_group(self, group_id, extract_members=False, load_to_db=False):
        """
        :param group_id: (string), group id
        :param load_to_db: (boolean), load info to DB as soon as its scraped
        :return: FBGroupMeta instance
        """

        BASE_URL = 'https://facebook.com/{fid}'
        self.driver.get(BASE_URL.format(fid=group_id))
        group = FBGroupMeta(group_id)

        # Group's username
        self._logger.info('Extracting username for group <{0}>'.format(group_id))
        match = constants.FBRegexes.url_group_username.search(self.driver.current_url)
        if match:
            user_name = match.group('result')
            if user_name.isdigit():
                # No username exists, it got FID
                user_name = None
                self._logger.warn('No username found for group <{0}>'.format(group_id))
            else:
                self._logger.info('Username found for group <{0}> is: {1}'.format(group_id, user_name))
            group.username = user_name

        tree = html.fromstring(self.driver.page_source)

        # Group's title
        self._logger.info('Extracting title for group <{0}>'.format(group_id))
        match = tree.xpath(constants.FBXpaths.group_title)
        retries = 0
        while len(match) == 0 and retries < 5:
            sleep(1)
            retries += 1
            match = tree.xpath(constants.FBXpaths.group_title)
        if len(match) > 0:
            group.title = unicode(match[0])
            self._logger.info(u"Title extracted for group <{0}>: {1}".format(group_id, group.title))
        else:
            raise FBGroupParseError("Couldn't parse title of group: {0}".format(group.fid))

        # Group's likers amount
        self._logger.info('Extracting likers amount for group <{0}>'.format(group_id))
        match = tree.xpath(constants.FBXpaths.group_members_amount)

        if len(match) > 0:
            members_amount_string = match[0]
            members_amount_digits = re.sub(r'\D', '',
                                           members_amount_string)  # example: '8,475 people liked this' -> '8475'
            group.members_amount = int(members_amount_digits)
            self._logger.info(u"Likers amount for group <{0}>: {1}".format(group_id, group.members_amount))
        else:
            self._logger.warn(u"No likers amount found for group <{0}>".format(group_id))

        # Group's description
        self._logger.info('Extracting description')
        match = tree.xpath(constants.FBXpaths.group_description)
        if len(match) > 0:
            group_description = match[0].text_content()
            group.description = unicode(group_description)
            self._logger.info(u"Description for group <{0}>: {1}".format(group_id, group.description))
        else:
            self._logger.warn(u"No description found for group {0}".format(group_id))

        # Group's category
        self._logger.info('Extracting category for group <{0}>'.format(group_id))
        match = tree.xpath(constants.FBXpaths.group_category)
        if len(match) > 0:
            group.category = unicode(match[0])
            self._logger.info(u"Category found for group <{0}>: {1}".format(group_id, group.category))
        else:
            self._logger.warn(u"No category found for group <{0}>".format(group_id))

        # Group's privacy
        self._logger.info('Extracting privacy for group <{0}>'.format(group_id))
        match = tree.xpath(constants.FBXpaths.group_privacy)
        if len(match) > 0:
            group.privacy = unicode(match[0])
            self._logger.info(u"Privacy found for group <{0}>: {1}".format(group_id, group.privacy))
        else:
            self._logger.info(u"No privacy found for group <{0}>".format(group_id))

        # Load group info to DB
        self._logger.info('Loading to DB')
        if load_to_db:
            try:
                group.import_to_db(group.meta['scrape_time'], self._cursor)
                self._db_conn.commit()
            except Exception, e:
                msg = "Failed to load {0} to DB. Error: {1}: {2}".format(group.fid, e.__class__, e.message)
                print msg
                self._logger.error(msg)

        # Extract group members
        if extract_members:
            self._logger.info('Extracting group members')
            group.members = self.parse_group_members(group_id)
            if load_to_db:
                self._logger.info('Loading group members to DB')
                self.import_group_members(group)
                self._db_conn.commit()
                self._logger.info('Done loading {0} members to group: {1}'.format(len(group.members), group_id))

        return group

    def parse_group_members(self, group_id):
        """
        :return: FBUserList of all group members
        """

        BASE_URL = 'https://www.facebook.com/ajax/browser/list/group_members/?gid={gid}' \
                   '&edge=groups:members&order=default&start={start}&__user={uid}&__a=1' \
                   '&__dyn=7AmajEzUGByEogDxyIGzGomyp9EbFbGAdy8VFLFwxBxCbzEeAq8zUK5U4e2O2K48jyR8' \
                   '8wPQiex2uVWxeUWq58O7EdV9VUcXxCFEW2PxOcxu5ocE88C9z9pqyUgx6'

        group_members = FBUserList()
        new_members = 1  # Used to count users found in each page
        while new_members > 0:
            new_members = 0

            current_url = BASE_URL.format(
                gid=group_id,
                start=len(group_members),
                uid=self._user_id
            )
            self.driver.get(current_url)
            sleep(4)

            html_payload = self._parse_payload_from_ajax_response(self.driver.page_source, 'group')
            if html_payload is None:
                return group_members

            html_payload = self._fix_payload(html_payload)
            tree = html.fromstring(html_payload)

            member_links = tree.xpath(constants.FBXpaths.group_member_urls)
            for member_link in member_links:
                member = self._parse_user_from_link(member_link)
                if member is not None and member not in group_members:
                    new_members += 1
                    group_members.append(member)

        return group_members

    def _import_group(self, group, cursor):
        """
        :param group: FBGroupMeta instance
        :param cursor: cursor to DB
        :return: boolean for success
        Saves groups into database
        """

        try:
            group.import_to_db(group.meta['scrape_time'], cursor)  # Import/Update row in DB
            self.import_group_members(group)
        except Exception, e:
            msg = "Failed to load {0} to DB. Error: {1}: {2}".format(group.fid, e.__class__, e.message)
            print msg
            self._logger.error(msg)

    def import_group_members(self, group, cursor=None):
        """
        :param group: FBGroup istance
        Loads all users and link to group into DB
        """

        GROUP_MEMBER_INSERT = r"INSERT INTO GROUP_MEMBERS (GROUP_ID, USER_ID, SCRAPING_TIME) " \
                                  r"VALUES (%(g_id)s, %(u_id)s, %(time)s)"
        cursor = _default_vs_new(self._cursor, cursor)

        for user in group.members:
                user.import_to_db(cursor)  # Import/Update row in DB of User
                cursor.execute(GROUP_MEMBER_INSERT, {
                    'g_id': group.fid, 'u_id': user.fid, 'time': group.meta['scrape_time']
                })

        self._db_conn.commit()  # Commit changes

    def import_groups(self, groups):
        """
        :param groups: FBGroupList
        Saves all the groups into a MySQL DB
        """

        for group in groups:
            self._import_group(group, self._cursor)
            self._db_conn.commit()

        self._db_conn.close()


    @FBParser.browser_needed
    def run(self, email, password, extract_members=None, load_to_db=None):
        """
        :param email: Email to connect with
        :param password: Password to connect with
        :param extract_members: (boolean), defaults to when the parser was created
        :param load_to_db: (boolean), load info to DB as soon as its scraped
        :return: List of pages metadata
        """

        self._user_id = self.init_connect(email, password)
        results = self._run_connected(extract_members, load_to_db)
        self.driver.quit()
        return results


    def _run_connected(self, extract_members=None, load_to_db=None, driver=None):
        """
        :param extract_members: (boolean), defaults to when the parser was created
        :param load_to_db: (boolean), load info to DB as soon as its scraped
        :return: List of pages metadata
        Method is called only after it's been connected
        """

        extract_members = _default_vs_new(self.extract_members, extract_members)
        load_to_db = _default_vs_new(self._load_to_db, load_to_db)
        self.driver = _stronger_value(self.driver, driver)

        all_groups = FBGroupList()

        for group_id in self.group_ids:
            try:
                group = self.parse_group(group_id, extract_members, load_to_db)
                all_groups.append(group)
            except FBGroupParseError, e:
                print e.message
                self._logger.error(e.message)

        return all_groups


if __name__ == '__main__':
    parser = FBGroupParser(['669009049776155'], extract_members=False, load_to_db=True)
    groups = parser.run('XXXXX', 'XXXX')
    #parser.import_groups(groups)
