from rest_framework import serializers

class RefreshTokenRequestSerializer(serializers.Serializer):
    refresh_token = serializers.CharField()

class RefreshTokenResponseSerializer(serializers.Serializer):
    access = serializers.CharField()
    refresh = serializers.CharField()


class LegacyRefreshTokenResponseSerializer(serializers.Serializer):
    access_token = serializers.CharField()
    refresh_token = serializers.CharField()
