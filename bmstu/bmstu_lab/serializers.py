from rest_framework import serializers

from .models import *


class ShipSerializer(serializers.ModelSerializer):
    image = serializers.SerializerMethodField()

    def get_image(self, ship):
        return ship.image.url.replace("minio", "localhost", 1)

    class Meta:
        model = Ship
        fields = "__all__"


class IcebreakerSerializer(serializers.ModelSerializer):
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
        fields = '__all__'


class IcebreakersSerializer(serializers.ModelSerializer):
    ships = serializers.SerializerMethodField()
    owner = serializers.SerializerMethodField()
    moderator = serializers.SerializerMethodField()

    def get_owner(self, icebreaker):
        return icebreaker.owner.username

    def get_moderator(self, icebreaker):
        if icebreaker.moderator:
            return icebreaker.moderator.username

    def get_ships(self, lecture):
        items = ShipIcebreaker.objects.filter(lecture=lecture)
        return [{**ShipSerializer(item.ship).data, "value": item.value} for item in items]
    
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
        fields = ('id', 'email', 'password', 'is_staff', 'is_superuser', 'username')
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