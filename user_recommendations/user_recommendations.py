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
OWNED_WEIGHT = 1
PLAYED_WEIGHT = 3
MAX_SCORE = 50
SCORE_BIAS = 25


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
            owned = set(user['owned'])
            wishlist = set(user['wishlist'])
            ranked = user['ranked']
            self.user_games[user['userId']] = {
                'owned': owned,
                'wishlist': wishlist,
                'ranked': ranked,
            }

    def _load_friends(self, collection):
        for friend in collection.find():
            owned = set([int(owned) for owned in friend['owned']])
            played = set([int(played) for played in friend['played']])
            self.friend_games[friend['userId']] = {
                'owned': owned,
                'played': played,
            }

    def _process_users(self):
        for user, games in self.user_games.items():
            owned = games['owned']
            wishlist = games['wishlist']
            ranked = games['ranked']
            ranked_ids = set([item['itemId'] for item in ranked])
            n = 0
            user_counter = Counter()
            for game in (owned | wishlist) - ranked_ids:
                if game in self.game_similarity:
                    n += 1
                    user_counter += self.game_similarity[game]

            for game in ranked:
                game_id = game['itemId']
                score = game['score']
                weight = self._calculate_score_weight(score)
                if game_id in self.game_similarity:
                    n += weight
                    user_counter += Counter({
                        item_id: score * weight
                        for item_id, score in self.game_similarity[game_id].items()
                    })

            self._cache_top_recommendations(user, owned, n, user_counter)

    def _process_friends(self):
        for user, friend_games in self.friend_games.items():
            n = 0
            owned = friend_games['owned']
            played = friend_games['played']
            user_counter = Counter()
            for game in owned:
                if game in self.game_similarity:
                    n += OWNED_WEIGHT
                    user_counter += self.game_similarity[game]

            for game in played:
                weight = PLAYED_WEIGHT - OWNED_WEIGHT
                if game in self.game_similarity:
                    n += weight
                    user_counter += Counter({
                        item_id: score * weight
                        for item_id, score in self.game_similarity[game].items()
                    })

            self._cache_top_recommendations(user, owned, n, user_counter)

    def _cache_top_recommendations(self, user, owned, n, user_counter):
        self.personalized_recommendations[user] = [
            (item_id, score / n)
            for item_id, score in user_counter.most_common()
            if item_id not in owned
        ][:USER_RECOMMENDATIONS_CUTOFF]

    @classmethod
    def _calculate_score_weight(cls, score):
        return (score - SCORE_BIAS) / MAX_SCORE

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
