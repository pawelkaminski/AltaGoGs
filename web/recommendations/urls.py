from django.urls import path
from recommendations.views import GameView, SeriesView, UserView

urlpatterns = [
    path('game/<int:user_id>/', GameView.as_view()),
    path('series/<int:user_id>/', SeriesView.as_view()),
    path('user/<int:user_id>/', UserView.as_view()),
]