from collections import (
    defaultdict,
    Counter,
)
import re

from gensim.corpora.wikicorpus import tokenize
from gensim.models.doc2vec import Doc2Vec
import pymongo
from sklearn.metrics.pairwise import cosine_similarity

TEXT_MODEL = '../text_model/wiki_200_14'
MONGO_HOST = 'localhost'
DB_NAME = 'gog'
GAMES_COLLECTION_NAME = 'product'
SIMILARITY_COLLECTION_NAME = 'similarityMatrix'
RATING_COLLECTION_NAME = 'rank'
SIMILARITY_CUTOFF = 200
MAX_GAME_RATING = 5
TEXT_SIMILARITY_FACTOR = 0.7
RATING_FACTOR = 1 - TEXT_SIMILARITY_FACTOR


class SimilarityMatrix:
    def __init__(self):
        self.game_ratings = {}
        self.game_order = {}
        self.game_vector = {}
        self.game_similar = defaultdict(Counter)
        self.text_model = None

    def compute(self):
        self._load_model()
        with pymongo.MongoClient(MONGO_HOST) as client:
            self._get_game_ratings(client)
            self._calculate_game_vectors(client)
            self._calculate_similars()
            self._push_similarity(client)

    def _load_model(self):
        self.text_model = Doc2Vec.load(TEXT_MODEL)

    def _get_game_ratings(self, client):
        rank_collection = client[DB_NAME][RATING_COLLECTION_NAME]
        for game in rank_collection.find(no_cursor_timeout=True):
            if 'ratingValue' in game:
                self.game_ratings[game['id']] = float(game['ratingValue'])

    def _calculate_game_vectors(self, client):
        games_collection = client[DB_NAME][GAMES_COLLECTION_NAME]
        for game in games_collection.find(no_cursor_timeout=True):
            game_id = game['id']
            self.game_order[len(self.game_order)] = game_id
            game_description = self._prepare_description(game)
            self.game_vector[game_id] = self.text_model.infer_vector(game_description)

    def _calculate_similars(self):
        vector_matrix = []
        for _, game_id in sorted(self.game_order.items(), key=lambda x: x[0]):
            vector_matrix.append(self.game_vector[game_id])

        similarity_matrix = cosine_similarity(vector_matrix)
        for game_ord, sim_vec in enumerate(similarity_matrix):
            game_id = self.game_order[game_ord]
            for other_game_ord, score in enumerate(sim_vec):
                other_game_id = self.game_order[other_game_ord]
                self.game_similar[game_id][other_game_id] = score

    def _push_similarity(self, client):
        similarity_collection = client[DB_NAME][SIMILARITY_COLLECTION_NAME]
        similarity_collection.drop()

        bulk = []
        for game_id, similarities in self.game_similar.items():
            top_similar = similarities.most_common(SIMILARITY_CUTOFF)
            similar = []
            for item_id, score in top_similar:
                if item_id in self.game_ratings:
                    game_rating = self.game_ratings[item_id]
                    score = score * TEXT_SIMILARITY_FACTOR + (game_rating / MAX_GAME_RATING) * RATING_FACTOR
                similar.append({'itemId': item_id, 'score': float(score)})

            bulk.append(
                pymongo.InsertOne({
                    'itemId': game_id,
                    'similar': sorted(similar, key=lambda x: x['score'], reverse=True)
                })
            )

        similarity_collection.bulk_write(bulk)
        similarity_collection.create_index([('itemId', pymongo.ASCENDING)], unique=True)

    @classmethod
    def _cleanhtml(cls, raw_html):
        regexp = re.compile('<.*?>')
        cleaned_text = re.sub(regexp, '', raw_html)
        return cleaned_text

    @classmethod
    def _prepare_description(cls, game):
        title = game['title']
        description = game['description']['full']
        whats_cool = game['description']['whats_cool_about_it']
        text = f'{title} {description} {whats_cool}'
        return tokenize(cls._cleanhtml(text))


if __name__ == 'main':
    SimilarityMatrix().compute()
