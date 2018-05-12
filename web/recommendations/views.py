from django.views.generic import TemplateView
import pymongo


class BaseView(TemplateView):
    mongo_path = 'mongodb://localhost:27017/'

    def get_client(self) -> pymongo.MongoClient:
        return pymongo.MongoClient(self.mongo_path)

    def game_info(self, game_id):
        with self.get_client() as client:
            db = client['gog']
            series_collection = db['series']
            games_collection = db['product']
            series = series_collection.find_one({'id': game_id})
            if series:
                series_games = games_collection.find({'id': {'$in': list(map(int, series['series']))}})
                series_games = {
                    game['id']: game
                    for game in series_games
                }
            else:
                series_games = {}
        game = series_games[game_id]
        del series_games[game_id]

        return {
            'game': game,
            'series': series_games
        }


class GameView(BaseView):
    template_name = 'recommendations/game.html'

    def get(self, request, *args, **kwargs):
        response = super().get(request, *args, **kwargs)

        with self.get_client() as client:
            db = client['gog']
            collection = db['product']
            item = collection.find_one({'id': int(request.GET['game_id'])})

        response.context_data['game'] = item
        return response

    def get(self, request, *args, **kwargs):
        response = super().get(request, *args, **kwargs)

        try:
            game_id = int(request.GET['game_id'])
            game_info = self.game_info(game_id)
        except KeyError:
            # TODO error for invalid key - no id given
            return response
        except ValueError:
            # TODO invalid key type
            return response

        response.context_data.update(game_info)

        print(response.context_data)

        return response


class UserView(BaseView):
    template_name = 'recommendations/user.html'
