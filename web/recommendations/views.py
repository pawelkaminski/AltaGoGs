from django.views.generic import TemplateView
import pymongo


class BaseView(TemplateView):
    mongo_path = 'mongodb://localhost:27017/'

    def get_db(self):
        return pymongo.MongoClient(self.mongo_path)


class GameView(BaseView):
    template_name = 'recommendations/game.html'

    example_data = {
        'title': 'Jazda',
        'img': {
            'href': 'https://demotywatory.pl/uploads/1255436121_by_preceleK_600.jpg',
            'formatters': {
                '0': '800',
                '1': '1600',
            }
        }
    }

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['data'] = self.example_data
        return context


class SeriesView(BaseView):
    template_name = 'recommendations/series.html'


class UserView(BaseView):
    template_name = 'recommendations/user.html'
