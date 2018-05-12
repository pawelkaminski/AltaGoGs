from rest_framework.views import APIView
from rest_framework.response import Response


class GameDetail(APIView):
    def get(self, request, game_id, format=None):
        return Response({'hello': 'world'})


class SeriesDetail(APIView):
    def get(self, request, series_id, fromat=None):
        return Response({'hello': 'world'})


class UserDetail(APIView):
    def get(self, request, user_id, format=None):
        return Response({'hello': 'world'})


