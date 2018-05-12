from django.views.generic import TemplateView


class GameView(TemplateView):
    template_name = 'recommendations/game.html'


class SeriesView(TemplateView):
    template_name = 'recommendations/series.html'


class UserView(TemplateView):
    template_name = 'recommendations/user.html'
