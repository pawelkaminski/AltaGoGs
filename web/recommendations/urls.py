from django.urls import path
from recommendations.views import (
    GameView,
    SearchView,
    UserView,
)

urlpatterns = [
    path('game/', GameView.as_view(), name='game'),
    path('search/', SearchView.as_view(), name='search'),
    path('user/', UserView.as_view(), name='user'),
]