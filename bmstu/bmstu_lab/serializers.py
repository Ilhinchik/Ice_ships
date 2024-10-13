from rest_framework import serializers

from .models import *


class ShipSerializer(serializers.ModelSerializer):
    def get_image(self, ship):
        return ship.image.url.replace("minio", "localhost", 1)

    class Meta:
        model = Ship
        fields = "__all__"


class IcebreakerSerializer(serializers.ModelSerializer):
    ships = serializers.SerializerMethodField()
    owner = serializers.SerializerMethodField()
    moderator = serializers.SerializerMethodField()

    def get_owner(self, icebreaker):
        return icebreaker.owner.username

    def get_moderator(self, icebreaker):
        if icebreaker.moderator:
            return icebreaker.moderator.username
            
    def get_ships(self, icebreaker):
        items = ShipIcebreaker.objects.filter(icebreaker=icebreaker)
        serializer = ShipSerializer([item.ship for item in items], many=True)
        return serializer.data

    class Meta:
        model = Icebreaker
        fields = '__all__'


class IcebreakersSerializer(serializers.ModelSerializer):
    owner = serializers.SerializerMethodField()
    moderator = serializers.SerializerMethodField()

    def get_owner(self, icebreaker):
        return icebreaker.owner.username

    def get_moderator(self, icebreaker):
        if icebreaker.moderator:
            return icebreaker.moderator.username

    class Meta:
        model = Icebreaker
        fields = "__all__"


class ShipIcebreakerSerializer(serializers.ModelSerializer):
    class Meta:
        model = ShipIcebreaker
        fields = "__all__"


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('id', 'email', 'password', 'first_name', 'last_name', 'date_joined', 'password', 'username')


class UserRegisterSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('id', 'email', 'password', 'first_name', 'last_name', 'username')
        write_only_fields = ('password',)
        read_only_fields = ('id',)

    def create(self, validated_data):
        user = User.objects.create(
            email=validated_data['email'],
            first_name=validated_data['first_name'],
            last_name=validated_data['last_name'],
            username=validated_data['username']
        )

        user.set_password(validated_data['password'])
        user.save()

        return user


class UserLoginSerializer(serializers.Serializer):
    username = serializers.CharField(required=True)
    password = serializers.CharField(required=True)