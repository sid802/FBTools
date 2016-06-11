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


class FBGroupParser(FBParser):
    """
    Class to parse FB Group metadata
    """

    def __init__(self, group_ids, extract_members=False):
        super(FBGroupParser, self).__init__()
        self.group_ids = group_ids  # list of strings
        self.extract_members = extract_members  # boolean

    @FBParser.browser_needed
    def parse_group(self, group_id, extract_members=False):
        """
        :param group_id: (string), group id
        :return: FBGroup instance
        """

        BASE_URL = 'https://facebook.com/{fid}'
        self.driver.get(BASE_URL.format(fid=group_id))
        group = FBGroup(group_id)

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

        # Extract group members
        if extract_members:
            group.members = self.parse_group_members(group_id)

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
        :param group: FBGroup instance
        :param cursor: cursor to DB
        :return: boolean for success
        Saves groups into database
        """

        try:
            GROUP_MEMBER_INSERT = r"INSERT INTO GROUP_MEMBERS (GROUP_ID, USER_ID, INSERTION_TIME) " \
                                  r"VALUES (%(g_id)s, %(u_id)s), %(time)s"
            group.import_to_db(cursor)  # Import/Update row in DB
            load_time = datetime.now()

            for user in group.members:
                user.import_to_db(cursor)  # Import/Update row in DB of User
                cursor.execute(GROUP_MEMBER_INSERT, {
                    'g_id': group.fid, 'u_id': user.fid, 'time': load_time
                })
        except connector.IntegrityError, e:
            print "Failed to load {0} to DB".format(group.fid)

    def import_groups(self, groups):
        """
        :param groups: FBGroupList
        Saves all the groups into a MySQL DB
        """
        db_conn = connector.connect(user='root',
                                    password='hujiko',
                                    host='127.0.0.1',
                                    database='facebook')
        cursor = db_conn.cursor()

        for group in groups:
            self._import_group(group, cursor)
            db_conn.commit()

        db_conn.close()


    @FBParser.browser_needed
    def run(self, email, password, extract_members=None):
        """
        :param email: Email to connect with
        :param password: Password to connect with
        :param extract_memebrs: (boolean), defaults to when the parser was created
        :return: List of pages metadata
        """

        self._user_id = self.init_connect(email, password)

        extract_members = _default_vs_new(self.extract_members, extract_members)

        all_groups = FBGroupList()

        for group_id in self.group_ids:
            group = self.parse_group(group_id, extract_members)
            all_groups.append(group)

        return all_groups


if __name__ == '__main__':
    parser = FBGroupParser(['1546783482199949', '361098497413890', '1591911684375443', '141134932694237'], True)
    groups = parser.run('sidfeiner@gmail.com', 'Qraaynem23')
    parser.import_groups(groups)
    print groups[0]
