from django.urls import path
from rest_framework.urlpatterns import format_suffix_patterns
from recommendations import views

urlpatterns = [
    path('game/<int:game_id>/', views.GameDetail.as_view()),
    path('series/<int:series_id/', views.SeriesDetail.as_view()),
    path('user/<int:user_id>/', views.UserDetail.as_view()),
]

urlpatterns = format_suffix_patterns(urlpatterns)