from rest_framework import serializers
from django.contrib.auth.models import User

from .models import *


class ShipSerializer(serializers.ModelSerializer):
    class Meta:
        model = Ship
        fields = ["id", "ship_name", "length", "year", "ice_class", "length", "engine",
                  "image", "description", "is_active"]


class GetShipSerializer(serializers.Serializer):
    ship = ShipSerializer(many=True)
    icebreaker_id = serializers.IntegerField(
        required=False, allow_null=True)
    items_in_cart = serializers.IntegerField()


class OwnerSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "username"]


class IcebreakerSerializer(serializers.ModelSerializer):
    owner = serializers.SerializerMethodField()
    moderator = serializers.SerializerMethodField()

    def get_owner(self, obj):
        return obj.owner.username

    def get_moderator(self, obj):
        return obj.moderator.username if obj.moderator else None

    class Meta:
        model = Icebreaker
        fields = ["id", "date_created", "date_formation", "date_complete", "moderator", "date", "start_point", "finish_point",
                  "result", "status", "owner"]


class PutIcebreakerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Icebreaker
        fields = ["id", "date_created", "date_formation", "date_complete", "moderator", "date", "start_point", "finish_point",
                  "result", "status", "owner"]
        read_only_fields = ["id", "date_created", "date_complete", "moderator",
                            "result", "owner"]


class ResolveIcebreakerSerializer(serializers.ModelSerializer):
    def validate(self, data):
        status = data.get('status')
        print(f"Received status: {status}")
        if data.get('status', '') not in (
                Icebreaker.RequestStatus.COMPLETED, Icebreaker.RequestStatus.REJECTED,):
            raise serializers.ValidationError("invalid status")
        return data

    class Meta:
        model = Icebreaker
        fields = ["id", "date_created", "date_formation", "date_complete", "moderator", "date", "start_point", "finish_point",
                  "result", "status", "owner"]
        read_only_fields = ["id", "date_created", "moderator", "date", "start_point", "finish_point",
                            "owner"]


class UpdateShipIcebreakerSerializer(serializers.ModelSerializer):
    class Meta:
        model = ShipIcebreaker
        fields = ["order"]


class ShipIcebreakerSerializer(serializers.ModelSerializer):
    class Meta:
        model = ShipIcebreaker
        fields = ["icebreaker", "ship", "order"]


class ShipForIcebreakerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Ship
        fields = ["id", "ship_name", "ice_class", "length", "image"]


class RelatedSerializer(serializers.ModelSerializer):
    ship = ShipForIcebreakerSerializer()

    class Meta:
        model = ShipIcebreaker
        fields = ["ship", "order"]


class FullIcebreakerSerializer(serializers.ModelSerializer):
    ship_list = serializers.SerializerMethodField()

    class Meta:
        model = Icebreaker
        fields = ["id", "date_created", "date_formation", "date_complete", "moderator", "date", "start_point", "finish_point",
                  "result", "status", "owner", "ship_list"]

    def get_ship_list(self, obj):
        # Сортировка shipinicebreaker_set по полю `order`
        sorted_ships = obj.shipicebreaker_set.order_by("order")
        return RelatedSerializer(sorted_ships, many=True).data


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


class UserUpdateSerializer(serializers.ModelSerializer):
    email = serializers.EmailField(required=False, allow_blank=True)
    password = serializers.CharField(
        write_only=True, required=False, allow_blank=True)

    class Meta:
        model = User
        fields = ['email', 'password']
        extra_kwargs = {
            'password': {'write_only': True}
        }

    def update(self, instance, validated_data):
        if 'email' in validated_data:
            instance.email = validated_data['email']

        if 'password' in validated_data:
            instance.set_password(validated_data['password'])

        instance.save()
        return instance


class UserLoginSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['is_staff']
        read_only_fields = ['is_staff']
