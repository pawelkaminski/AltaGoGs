from bs4 import BeautifulSoup
from pymongo import MongoClient
import requests
import time


class UserDownloader:
    REQUEST_WAIT = 0.01
    DATABASE_NAME = 'gog'

    USERS_COLLECTION_NAME = 'users'
    FRIENDS_COLLECTION_NAME = 'friends'

    # it is faster to copy datafrom browser for 5 people
    def download(self):
        self.get_user()
        self.get_friends()

    def get_user(self):
        nick = 'Super_Cezar'
        # https://www.gog.com/user/data/games
        owned = []
        # https://www.gog.com/user/games_rating.json
        ranked = {}
        # https://embed.gog.com/user/wishlist.json
        wishlist = []

        user = {
            'userId': nick,
            'owned': owned,
            'ranked': {{'itemId': key, 'score': val} for key, val in ranked.items()},
            'wishlist': wishlist,
        }
        self._store_result_at_mongo(self.USERS_COLLECTION_NAME, user)

    def get_friends(self):
        htmls = []
        for html in htmls:
            self._get_friend(html)

    def _get_friend(self, html):
        pass

    def _store_result_at_mongo(self, collection_name, item):
        with MongoClient() as client:
            collection = client[self.DATABASE_NAME][collection_name]
            collection.insert_one(item)


if __name__ == '__main__':
    user_downloader = UserDownloader()
    user_downloader.download()
