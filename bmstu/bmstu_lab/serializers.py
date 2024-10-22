from rest_framework import serializers

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

        return ""
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
        fields = ('email', 'username')


class UserRegisterSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('email', 'password', 'username')
        write_only_fields = ('password',)
        read_only_fields = ('id',)

    def create(self, validated_data):
        user = User.objects.create(
            email=validated_data['email'],
            username=validated_data['username']
        )

        user.set_password(validated_data['password'])
        user.save()

        return user


class UserLoginSerializer(serializers.Serializer):
    username = serializers.CharField(required=True)
    password = serializers.CharField(required=True)