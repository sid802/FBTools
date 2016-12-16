__author__ = 'Sid'

from fb_main import _default_vs_new
from fb_main import *
from base64 import b64encode
from lxml import html

class FriendsParser(FBParser):
    """
    Class to parse a user's friends
    """
    def __init__(self, user_targets, extract_friends_infos=False):
        """
        :param fb_user: list, FBUsers instances
        :param extract_user_infos: boolean, to extract the friend's basic infos
        :return:
        """
        super(FriendsParser, self).__init__(self.__class__.__name__, './logs')
        self.user_targets = user_targets  # List
        self.extract_friends_infos = extract_friends_infos  # Boolean

    @FBParser.browser_needed
    def parse_friends(self, fb_user, extract_friends_infos=None):
        """
        :param fb_user: FBUser instance of user we want to extract its friends
        :param extract_friends_infos: boolean, to extract the friend's basic infos
        :return: List of all friends that could be parsed from user
        """

        friends_normal = self._parse_friends_normal(fb_user, extract_friends_infos)  # People in friends list
        covers_likers = self._parse_cover_likers(fb_user, extract_friends_infos)  # People who liked the cover pictures

        basic_friends = friends_normal.union(covers_likers)
        all_mutuals = set()

        for friend in basic_friends:
            mutual_friends = self._parse_friends_mutual(fb_user, friend)  # Find mutual friends with each friend
            all_mutuals.update(mutual_friends)

        all_friends = basic_friends.union(all_mutuals)  # Union friend list, cover likers and mutual friends

        return all_friends

    @FBParser.browser_needed
    def _parse_cover_likers(self, fb_user, extract_friends_infos=None):
        """
        :param fb_user: FBUser instance of user we want to extract its friends
        :param extract_friends_infos: boolean, to extract the friend's basic infos
        :return: Set of all people who liked the fb_user's cover pictures
        """
        #TODO: write
        return set()
        pass

    @FBParser.browser_needed
    def _parse_friends_normal(self, fb_user, extract_friends_infos=None):
        """
        :param fb_user: FBUser, instance of user we want to extract its friends
        :param extract_friends_infos: boolean, to extract the friend's basic infos
        :return: List of friends of fb_user
        """

        BASE_URL = 'https://www.facebook.com/ajax/pagelet/generic.php/FriendsAppCollectionPagelet?data=' \
                '{{"collection_token":"{target}:2356318349:3","cursor":"{cursor}",' \
                '"profile_id":{target}}}&__user={user}&__a=1'

        cursor = '0:not_structured:{0}'
        last_friend_fid = ''

        all_friends = set()  # List of FBUser's
        currently_added = 1

        while currently_added != 0:
            # Break when friends page is empty
            currently_added = 0
            current_url = BASE_URL.format(
                target=fb_user.fid,
                cursor=b64encode(cursor.format(last_friend_fid)),
                user=self._user_id
            )
            self.driver.get(current_url)

            html_payload = self._parse_payload_from_ajax_response(self.driver.page_source, 'friends')
            if html_payload is None:
                return all_friends

            html_payload = self._fix_payload(html_payload)
            tree = html.fromstring(html_payload)
            friends_elements = tree.xpath(constants.FBXpaths.friends_links)

            for friend_element in friends_elements:
                friend = self._parse_user_from_link(friend_element)
                last_friend_fid = friend.fid
                all_friends.add(friend)
                currently_added += 1

        return all_friends

    @FBParser.browser_needed
    def _parse_friends_mutual(self, user_target, user_friend):
        """
        :param user_target: FBUser, our target user
        :param user_friends: FBUser,
        :return: list, mutual friends of a target and his friends
        """

        offset = 0

        BASE_URL = 'https://www.facebook.com/ajax/browser/list/mutualfriends/?uid={id1}&node={id2}&start={offset}&__user={user}&__a=1'

        self.driver.get(BASE_URL)

        currently_added = 1
        all_mutuals = set()

        while currently_added != 0:
            currently_added = 0
            current_url = BASE_URL.format(id1=user_target.fid,
                                          id2=user_friend.fid,
                                          offset=offset,
                                          user=self._user_id)

            self.driver.get(current_url)
            html_payload = self._parse_payload_from_ajax_response(self.driver.page_source, 'mutual_friends')
            if html_payload is None or len(html_payload) == 0:
                # None or blank string
                return all_mutuals
            html_payload = self._fix_payload(html_payload)
            tree = html.fromstring(html_payload)

            friends_elements = tree.xpath(constants.FBXpaths.friends_links)
            for friend_element in friends_elements:
                friend = self._parse_user_from_link(friend_element)
                all_mutuals.add(friend)
                currently_added += 1

            offset += currently_added  # Increment offset

        return all_mutuals

    @FBParser.browser_needed
    def run(self, email, password, extract_friends_infos=None):
        """
        :param email: Email to connect with
        :param password: Password to connect with
        :param extract_friends_infos: boolean, to extract the friend's basic infos
        :return: List of target users but with filled friends attribute
        """

        self._user_id = self.init_connect(email, password)

        extract_friends_infos = _default_vs_new(self.extract_friends_infos, extract_friends_infos)

        for user_target in self.user_targets:
            user_friends = self.parse_friends(user_target, extract_friends_infos)
            user_target.friends = user_friends

        return self.user_targets

if __name__ == '__main__':
    parser = FriendsParser([FBUser('XXXXX')])
    targets = parser.run('XXXXX', 'XXXX')
    for target in targets:
        for friend in target.friends:
            print friend