from django.urls import path
from recommendations.views import GameView, SeriesView, UserView

urlpatterns = [
    path('game', GameView.as_view(), name='game'),
    path('series', SeriesView.as_view(), name='series'),
    path('user', UserView.as_view(), name='user'),
]