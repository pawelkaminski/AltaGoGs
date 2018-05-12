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
            users_collection = db['userRecommendations']
            games_collection = db['product']

            query = {'userId': user_id}
            recommendations = users_collection.find_one(query)

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
            
        return {'games': games}


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
