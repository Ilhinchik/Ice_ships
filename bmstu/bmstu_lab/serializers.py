from rest_framework import serializers
from django.contrib.auth.models import User

from .models import *


class ShipSerializer(serializers.ModelSerializer):
    image = serializers.SerializerMethodField()

    def get_image(self, ship):
        if ship.image:
            return ship.image.url.replace("minio", "localhost", 1)

        return "http://localhost:9000/images/default.png"

    class Meta:
        model = Ship
        fields = "__all__"



class IcebreakersSerializer(serializers.ModelSerializer):
    owner = serializers.SerializerMethodField()
    moderator = serializers.SerializerMethodField()

    def get_owner(self, icebreaker):
        return icebreaker.owner.username

    def get_moderator(self, icebreaker):
        if icebreaker.moderator:
            return icebreaker.moderator.username
            
    def get_ships(self, icebreaker):
        # Получаем связи ShipIcebreaker для текущей проводки
        items = ShipIcebreaker.objects.filter(icebreaker=icebreaker)
        
        # Сериализуем каждый объект Ship и добавляем его порядок (order)
        ships_with_order = []
        for item in items:
            ship_data = ShipSerializer(item.ship).data
            ship_data['order'] = item.order  # Добавляем поле order
            ships_with_order.append(ship_data)
        
        return ships_with_order
    
    def update(self, instance, validated_data):
        instance = super().update(instance, validated_data)
        instance.update_result()
        return instance

    class Meta:
        model = Icebreaker
        fields = "__all__"



class IcebreakerSerializer(serializers.ModelSerializer):
    ships = serializers.SerializerMethodField()
    owner = serializers.SerializerMethodField()
    moderator = serializers.SerializerMethodField()

    def get_owner(self, icebreaker):
        return icebreaker.owner.username

    def get_moderator(self, icebreaker):
        return icebreaker.moderator.username if icebreaker.moderator else ""
    

    def get_ships(self, icebreaker):
        items = ShipIcebreaker.objects.filter(icebreaker=icebreaker)
        return [{**ShipSerializer(item.ship).data, "order": item.order} for item in items]

    class Meta:
        model = Icebreaker
        fields = '__all__'


class ShipIcebreakerSerializer(serializers.ModelSerializer):
    class Meta:
        model = ShipIcebreaker
        fields = "__all__"


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'password']
        extra_kwargs = {'password': {'write_only': True}}

    def create(self, validated_data):
        user = User.objects.create_user(
            username=validated_data['username'],
            password=validated_data['password'],
            email=validated_data.get('email', '')
        )
        return user

    def update(self, instance, validated_data):
        instance.email = validated_data.get('email', instance.email)
        if 'password' in validated_data:
            instance.set_password(validated_data['password'])
        instance.save()
        return instance
    
class LoginSerializer(serializers.Serializer):
    username = serializers.CharField(required=True)
    password = serializers.CharField(required=True)