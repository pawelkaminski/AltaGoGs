from django.views.generic import TemplateView
from django.conf import settings
import pymongo


class BaseView(TemplateView):
    mongo_path = 'mongodb://localhost:27017/'

    def get_client(self) -> pymongo.MongoClient:
        return pymongo.MongoClient(self.mongo_path)

    @staticmethod
    def get_games(games_collection, ids_list):
        game_fields = {'id': True, 'images.icon': True, '_id': False, 'title': True}
        return games_collection.find({'id': {'$in': ids_list}}, game_fields)

    def game_no_series(self, game_id, limit=16):
        with self.get_client() as client:
            blacklist = {game_id}

            db = client[settings.DB_NAME]
            similarity_matrix_collection = db['similarityMatrix']
            series_collection = db['series']
            games_collection = db['product']

            similarities = similarity_matrix_collection.find_one({'itemId': game_id})
            if not similarities:
                return []

            similarities = similarities['similar']
            games_ids = [
                game['itemId']
                for game in similarities
            ]

            series = series_collection.find({'id': {'$in': games_ids}})
            series = {
                s['id']: s['series']
                for s in series
            }

            similarities = sorted(similarities, key=lambda item: item['score'], reverse=True)

            sub_result = {}
            for game in similarities:
                if game['itemId'] in blacklist:
                    continue

                sub_result[game['itemId']] = game['score']

                if len(sub_result) >= limit:
                    break

                if game['itemId'] in series:
                    blacklist.union(series[game['itemId']])

            games_ids = list(sub_result.keys())
            games = self.get_games(games_collection, games_ids)
            result = [
                dict(game, score=sub_result[game['id']])
                for game in games
            ]
            result = sorted(result, key=lambda item: item['score'], reverse=True)

        return result

    def game_info(self, game_id, limit_similarities=16):
        with self.get_client() as client:
            db = client[settings.DB_NAME]
            games_collection = db['product']

            game = games_collection.find_one({'id': game_id})
            if not game:
                return {}

            series_collection = db['series']
            similarity_matrix_collection = db['similarityMatrix']
            series = series_collection.find_one({'id': game_id})
            if series:
                series_games = self.get_games(games_collection, list(map(int, series['series'])))
                series_games = {
                    game['id']: game
                    for game in series_games
                }
                del series_games[game_id]
            else:
                series_games = {}

            similarities = list(similarity_matrix_collection.find({'itemId': game_id}))
            if similarities:
                similarities = similarities[0]['similar']
                similarities = sorted(similarities, key=lambda item: item['score'], reverse=True)
                similarities = [
                    (similar['itemId'], similar['score'])
                    for similar in similarities
                    if (similar['itemId'] != game_id) and (similar['itemId'] not in series_games)
                ]
                similarities = similarities[:limit_similarities]
                similar_ids = [
                    similar[0]
                    for similar in similarities
                ]
                similarities = {g[0]: g[1] for g in similarities}
                similar_games = list(self.get_games(games_collection, similar_ids))
                similar_games = [
                    dict(game, score=similarities[game['id']])
                    for game in similar_games
                ]
                similar_games = sorted(similar_games, key=lambda item: item['score'], reverse=True)

            else:
                similar_games = []

        return {
            'game': game,
            'series': series_games,
            'similar_games': similar_games,
        }

    def user_info(self, user_id):
        with self.get_client() as client:
            db = client[settings.DB_NAME]
            rec_collection = db['userRecommendations']
            games_collection = db['product']
            user_collection = db['users']
            friend_collection = db['friends']

            query = {'userId': user_id}
            recommendations = rec_collection.find_one(query)

            if not recommendations:
                return {}

            users_recommendations = {
                game['itemId']: game['score']
                for game in recommendations['recommendedItems']
            }

            plain_games = self.get_games(games_collection, list(users_recommendations.keys()))
            games = [
                dict(game, score=users_recommendations[game['id']])
                for game in plain_games
            ]

            games = sorted(games, key=lambda game: game['score'], reverse=True)

            user = user_collection.find_one(query)
            if not user:
                user = friend_collection.find_one(query)

            return_dict = {
                'owned': self._process_game_list(user.get('owned', []), games_collection),
                'played': self._process_game_list(user.get('played', []), games_collection),
                'wishlist': self._process_game_list(user.get('wishlist', []), games_collection),
                'ranked': self._process_game_list([key['itemId'] for key in user.get('ranked', [])], games_collection),
                'games': games,
            }

        return return_dict

    def _process_game_list(self, game_list, games_collection):
        return list(self.get_games(games_collection, [int(el) for el in game_list]))


class GameView(BaseView):
    template_name = 'recommendations/game.html'

    def get(self, request, *args, **kwargs):
        response = super().get(request, *args, **kwargs)

        try:
            game_id = int(request.GET['game_id'])
            game_info = self.game_info(game_id)
        except KeyError as ex:
            # TODO error for invalid key - no id given
            return response
        except ValueError as ex:
            # TODO invalid key type
            return response

        response.context_data.update(game_info)

        return response


class UserView(BaseView):
    template_name = 'recommendations/user.html'

    def get(self, request, *args, **kwargs):
        response = super().get(request, *args, **kwargs)

        try:
            user_id = request.GET['user_id']
            user_info = self.user_info(user_id)
        except KeyError as ex:
            # TODO error for invalid key - no id given
            return response
        except ValueError as ex:
            # TODO invalid key type
            return response

        response.context_data.update(user_info)

        return response
    

class SearchView(BaseView):
    template_name = 'recommendations/search.html'

    def get(self, request, *args, **kwargs):
        response = super().get(request, *args, **kwargs)

        with self.get_client() as client:
            db = client[settings.DB_NAME]
            collection = db['product']
            # BEWARE: requires text index
            # db.product.createIndex({'title': 'text'})
            request_text = request.GET['game_name']
            items = list(collection.find({'$text': {'$search': f'"{request_text}"'}}))

        response.context_data['games'] = items
        return response
