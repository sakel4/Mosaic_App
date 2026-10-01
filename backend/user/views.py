from rest_framework import generics, permissions
from rest_framework_simplejwt.authentication import JWTAuthentication

from .serializers import UserSerializer


class MeView(generics.RetrieveUpdateAPIView):
    serializer_class = UserSerializer
    authentication_classes = (JWTAuthentication,)
    permission_classes = (permissions.IsAuthenticated,)
    http_method_names = ["get", "patch", "head", "options"]

    def get_object(self):
        return self.request.user
