from rest_framework.response import Response
from rest_framework.decorators import api_view

@api_view(["GET"])
def health(request):
    return Response({"status": "ok"})


@api_view(["GET"])
def test(self, request):
    return Response({
        "id": request.user.id,
        "username": request.user.username
    })
