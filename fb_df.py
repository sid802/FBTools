__author__ = 'Sid'

from fb_main import *
import pandas as pd
from matplotlib import pyplot as plt

class TypeList(list):
    """
    List that accepts only specific types
    """
    def __init__(self, class_object, data=list()):
        super(TypeList, self).__init__(data)
        self.class_object = class_object
        self._df = None  # Cached DataFrame

    def append(self, p_object):
        if not isinstance(p_object, self.class_object):
            raise Exception("List can only contain {0} instances".format(self.class_object))
        super(TypeList, self).append(p_object)


    def _to_dataframe(self, cache=True):
        """
        :param cache: cache the DataFrame in instance
        :return: Current list represented as a DataFrame
        """
        attributes = self.class_object().__dict__.keys()
        all_objects = []

        for item in self:
            flat_obj = []
            for attribute in attributes:
                # attributes are picked in the same order
                flat_obj.append(getattr(item, attribute))
            all_objects.append(flat_obj)

        df = pd.DataFrame(columns=attributes, data=all_objects).set_index('fid')

        if cache:
            self._df = df

        return df

class FBUserList(TypeList):
    def __init__(self, data=list()):
        super(FBUserList, self).__init__(FBUser, data)

class FBPageList(TypeList):
    def __init__(self, data=list()):
        super(FBPageList, self).__init__(FBPage, data)

class FBPictureList(TypeList):
    def __init__(self, data=list()):
        super(FBPictureList, self).__init__(FBPicture, data)

    def _plot_users(self, user_kind, *args, **kwargs):
        """
        :param user_kind: What kind of users to plot (likers/taggees/authors etc)
        :return: Plot with x-axis of persons and y-axes as counter
        """
        pictures_df = self._to_dataframe(cache=False)

        users_lst = []
        for picture_index, picture_row in pictures_df.iterrows():
            users = picture_row[user_kind]
            for user in users:
                users_lst.append((picture_index, user.fid, user.full_name))


        likers_df = pd.DataFrame(columns=['fid', 'user_fid', 'user_fullname'], data=users_lst)
        count = likers_df.groupby(by=['user_fid', 'user_fullname']).count()
        plot = count[:10].plot.bar()
        plt.show()
        return plot


    def plot_likers(self, *args, **kwargs):
        """
        :return: Plot with x-axis of the person who liked, and y-axis of the amount of pictures he liked
        """
        return self._plot_users('likers')

    def plot_taggees(self, *args, **kwargs):
        """
        :return: Plot with x-axis of the taggees, and y-axis of the amount of pictures he liked
        """
        return self._plot_users('taggees')




