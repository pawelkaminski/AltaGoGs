from collections import (
    Counter,
    defaultdict,
)

import pymongo

MONGO_HOST = 'localhost'
DB_NAME = 'gog'
SIMILARITY_COLLECTION_NAME = 'similarityMatrix'
USER_RECOMMENDATIONS_COLLECTION_NAME = 'userRecommendations'
USER_RECOMMENDATIONS_CUTOFF = 50
USERS_COLLECTION_NAME = 'users'
FRIENDS_COLLECTION_NAME = 'friends'


class UserRecommendations:
    def __init__(self):
        self.game_similarity = defaultdict(Counter)
        self.user_games = {}
        self.friend_games = {}
        self.personalized_recommendations = {}

    def compute(self):
        with pymongo.MongoClient(MONGO_HOST) as client:
            similarity_collection = client[DB_NAME][SIMILARITY_COLLECTION_NAME]
            user_collection = client[DB_NAME][USERS_COLLECTION_NAME]
            friends_collection = client[DB_NAME][FRIENDS_COLLECTION_NAME]
            recommendations_collection = client[DB_NAME][USER_RECOMMENDATIONS_COLLECTION_NAME]
            self._load_similarities(similarity_collection)
            self._load_users(user_collection)
            self._load_friends(friends_collection)
            self._process_users()
            self._process_friends()
            self._save_recommendations(recommendations_collection)

    def _load_similarities(self, similarity_collection):
        for game in similarity_collection.find(no_cursor_timeout=True):
            game_id = game['itemId']
            similar_games = [
                (similar['itemId'], similar['score'])
                for similar in game['similar']
            ]

            self.game_similarity[game_id] = Counter(dict(similar_games))

    def _load_users(self, collection):
        for user in collection.find():
            self.user_games[user['userId']] = set(user['owned'])

    def _load_friends(self, collection):
        for friend in collection.find():
            self.friend_games[friend['userId']] = set([int(owned) for owned in friend['owned']])

    def _process_users(self):
        self._process_owned_games(self.user_games)

    def _process_friends(self):
        self._process_owned_games(self.friend_games)

    def _process_owned_games(self, user_games):
        for user, games in user_games.items():
            n = len(games)
            user_counter = Counter()
            for game in games:
                user_counter += self.game_similarity[game]

            self.personalized_recommendations[user] = [
                (item_id, score / n)
                for item_id, score in user_counter.most_common()
                if item_id not in games
            ][:USER_RECOMMENDATIONS_CUTOFF]

    def _save_recommendations(self, collection):
        collection.drop()
        bulk = []

        for user, recommended_items in self.personalized_recommendations.items():
            bulk.append(pymongo.InsertOne({
                'userId': user,
                'recommendedItems': [
                    {'itemId': item_id, 'score': score}
                    for item_id, score in recommended_items
                ]
            }))

        collection.bulk_write(bulk)
        collection.create_index([('userId', pymongo.ASCENDING)], unique=True)

if __name__ == 'main':
    UserRecommendations().compute()
