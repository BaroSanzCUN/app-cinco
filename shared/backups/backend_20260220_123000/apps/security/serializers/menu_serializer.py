from rest_framework import serializers

class MenuItemSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    url = serializers.CharField()
    nombre = serializers.CharField()
    area = serializers.CharField()
    carpeta = serializers.CharField()
    permisos = serializers.ListField(
        child=serializers.DictField(child=serializers.BooleanField())
    )

class MenuResponseSerializer(serializers.Serializer):
    menu = serializers.ListField(
        child=MenuItemSerializer()
    )
