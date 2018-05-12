import glob
import os

from bs4 import BeautifulSoup
from pymongo import MongoClient


class UserDownloader:
    REQUEST_WAIT = 0.01
    DATABASE_NAME = 'gog2'

    USERS_COLLECTION_NAME = 'users'
    FRIENDS_COLLECTION_NAME = 'friends'

    # it is faster to copy datafrom from browser for 3 people than write code
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
        wishlist = {}

        user = {
            'userId': nick,
            'owned': owned,
            'ranked': [{'itemId': key, 'score': val} for key, val in ranked.items()],
            'wishlist': [key for key, _ in wishlist.items()],
        }
        self._store_result_at_mongo(self.USERS_COLLECTION_NAME, user)

    def get_friends(self):
        os.chdir('htmls')
        for file in glob.glob('*.html'):
            with open(file, encoding='utf8') as f:
                contents = f.read()
                self._get_friend(contents, file.split('.')[0])

    def _get_friend(self, html, user_name):
        friend = {
            'userId': user_name,
            'owned': [],
            'played': [],
        }
        soup = BeautifulSoup(html, 'html.parser')
        for item in soup.findAll('div', class_='games-matcher__row'):
            id_finder = item.find('div', class_='games-matcher__column--game')
            item_id = id_finder.attrs['prof-game']
            friend['owned'].append(item_id)
            time_spent = item.find_all('div', class_='games-matcher__column--statistics')
            if self._is_any_time_spent(time_spent):
                friend['played'].append(item_id)

        self._store_result_at_mongo(self.FRIENDS_COLLECTION_NAME, friend)

    def _is_any_time_spent(self, statistics):
        for stat in statistics:
            for binding in stat.find_all('span', class_='ng-binding'):
                if binding.contents[0] not in ('0%', '0m'):
                    return True
        return False

    def _store_result_at_mongo(self, collection_name, item):
        with MongoClient() as client:
            collection = client[self.DATABASE_NAME][collection_name]
            collection.insert_one(item)


if __name__ == '__main__':
    user_downloader = UserDownloader()
    user_downloader.download()
