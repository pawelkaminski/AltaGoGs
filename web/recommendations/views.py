from django.conf import settings
from django.views.generic import TemplateView
from django.conf import settings
import pymongo


class BaseView(TemplateView):
    mongo_path = 'mongodb://localhost:27017/'

    def get_client(self) -> pymongo.MongoClient:
        return pymongo.MongoClient(self.mongo_path)

    def game_info(self, game_id, limit_similarities=16):
        game_fields = {'id': True, 'images.icon': True, '_id': False, 'title': True}

        with self.get_client() as client:
            db = client[settings.DB_NAME]
            series_collection = db['series']
            games_collection = db['product']
            similarity_matrix_collection = db['similarityMatrix']
            series = series_collection.find_one({'id': game_id})
            if series:
                series_games = games_collection.find({'id': {'$in': list(map(int, series['series']))}}, game_fields)
                series_games = {
                    game['id']: game
                    for game in series_games
                }
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
                    similarities = {game[0]: game[1] for game in similarities}
                    similar_games = list(games_collection.find({'id': {'$in': similar_ids}}, game_fields))
                    similar_games = [
                        dict(game, score=similarities[game['id']])
                        for game in similar_games
                    ]
                    similar_games = sorted(similar_games, key=lambda item: item['score'], reverse=True)

                else:
                    similar_games = []
            else:
                series_games = {}
                similar_games = []

        game = series_games[game_id]
        del series_games[game_id]

        return {
            'game': game,
            'series': series_games,
            'similar_games': similar_games,
        }


class GameView(BaseView):
    template_name = 'recommendations/game.html'

    def get(self, request, *args, **kwargs):
        response = super().get(request, *args, **kwargs)

        with self.get_client() as client:
            db = client[settings.DB_NAME]
            collection = db['product']
            item = collection.find_one({'id': int(request.GET['game_id'])})

        response.context_data['game'] = item
        return response

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

        print(len(items))
        response.context_data['games'] = items
        return response
