from django.urls import path
from recommendations.views import GameView, UserView

urlpatterns = [
    path('game/', GameView.as_view(), name='game'),
    path('user/', UserView.as_view(), name='user'),
]