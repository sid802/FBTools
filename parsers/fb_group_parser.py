__author__ = 'Sid'
from lxml import html
from parsers import fb_constants as constants
from fb_main import *
from fb_main import _default_vs_new
from fb_df import *
import re
from time import sleep
from datetime import datetime
from mysql import connector

class FBGroupMeta(FBGroup):
    """
    Extension of FBGroup which adds metadata of the parsing itself
    """
    def __init__(self, fbid, group_user=None, group_title=None, privacy=None, description=None,
                 category=None, members_amount=None, members=None):
        super(FBGroupMeta, self).__init__(fbid, group_user, group_title, privacy, description,
                                            category, members_amount, members)
        self.group_user = group_user  # username (string)
        self.group_title = group_title  # full name (string)
        self.privacy = privacy  # string
        self.description = description  # string
        self.members_amount = members_amount  # int
        self.members = members  # list of FBUsers
        self.category = category  # Category (string)

        self.meta = {'scrape_time': datetime.now()}


class FBGroupParser(FBParser):
    """
    Class to parse FB Group metadata
    """

    def __init__(self, group_ids, extract_members=False, load_to_db=False):
        super(FBGroupParser, self).__init__()
        self.group_ids = group_ids  # list of strings
        self.extract_members = extract_members  # boolean
        self._load_to_db = load_to_db  # boolean, load info to DB as soon as its scraped
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
        match = constants.FBRegexes.url_group_username.search(self.driver.current_url)
        if match:
            user_name = match.group('result')
            if user_name.isdigit():
                # No username exists, it got FID
                user_name = None
            group.group_user = user_name

        tree = html.fromstring(self.driver.page_source)

        # Group's title
        match = tree.xpath(constants.FBXpaths.group_title)
        retries = 0
        while len(match) == 0 and retries < 5:
            sleep(1)
            retries += 1
            match = tree.xpath(constants.FBXpaths.group_title)
        if len(match) > 0:
            group.group_title = unicode(match[0])

        # Group's likers amount
        match = tree.xpath(constants.FBXpaths.group_members_amount)

        if len(match) > 0:
            members_amount_string = match[0]
            members_amount_digits = re.sub(r'\D', '',
                                           members_amount_string)  # example: '8,475 people liked this' -> '8475'
            group.members_amount = int(members_amount_digits)

        # Group's description
        match = tree.xpath(constants.FBXpaths.group_description)
        if len(match) > 0:
            group_description = match[0].text_content()
            group.description = unicode(group_description)

        # Group's category
        match = tree.xpath(constants.FBXpaths.group_category)
        if len(match) > 0:
            group.category = unicode(match[0])

        # Group's privacy
        match = tree.xpath(constants.FBXpaths.group_privacy)
        if len(match) > 0:
            group.privacy = unicode(match[0])

        # Load group info to DB
        if load_to_db:
            try:
                group.import_to_db(group.meta['scrape_time'], self._cursor)
                self._db_conn.commit()
            except Exception, e:
                print str(e)

                print "Failed to load {0} to DB".format(group.fid)

        # Extract group members
        if extract_members:
            group.members = self.parse_group_members(group_id)
            if load_to_db:
                self.import_group_members(group)
                self._db_conn.commit()

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
            print str(e)
            print "Failed to load {0} to DB".format(group.fid)

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
        extract_members = _default_vs_new(self.extract_members, extract_members)
        load_to_db = _default_vs_new(self._load_to_db, load_to_db)

        all_groups = FBGroupList()

        for group_id in self.group_ids:
            group = self.parse_group(group_id, extract_members, load_to_db)
            all_groups.append(group)

        self.driver.quit()
        return all_groups


if __name__ == '__main__':
    parser = FBGroupParser(['108459592629916','13625164631','141134932694237','1492833544374932','1546783482199949','1591911684375443','1610254709201836','162685489659','17275074758','188430365379','2215439152','243878712401976','251023115009662','258447084303291','263023093838552','289193677785389','314227591934262','327483250942','361098497413890','371486982898464','387770837993755','392031520857479','396641690362272','421798144631098','43456268660','445887735495943','45245752193','528365857234634','5583181379','558444230904923','599061010175112','610241649060550','667953409893624','669009049776155','674316449257956','829096557118704'], extract_members=False, load_to_db=True)
        #['371486982898464', '667953409893624', '258447084303291', '43456268660', '5583181379', '610241649060550',
         #'1492833544374932', '1610254709201836', '2215439152'], True)
    groups = parser.run('sidfeiner@gmail.com', 'Qraaynem23')
    #parser.import_groups(groups)
