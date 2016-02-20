__author__ = 'Sid'

from fb_main import *
import pandas as pd

class TypeList(list):
    """
    Custom List for FB Group Lists
    """
    def __init__(self, class_object):
        super(TypeList, self).__init__()
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

class FBPictureList(TypeList):
    def __init__(self):
        super(FBPictureList, self).__init__(FBPicture)

    def plot_likers(self, *args, **kwargs):
        """
        :return: Plot with x-axis of the person who liked, and y-axis of the amount of pictures he liked
        """
        pictures_df = self._to_dataframe(cache=False)
        pictures_df.likers.values()



