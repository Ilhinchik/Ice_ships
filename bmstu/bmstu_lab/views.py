import requests
from django.contrib.auth import authenticate
from django.http import HttpResponse
from django.utils.dateparse import parse_datetime, parse_date
from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response

from .jwt_helper import *
from .permissions import *
from .serializers import *
from .utils import identity_user


def get_draft_icebreaker(request):
    user = identity_user(request)

    if user is None:
        return None

    icebreaker = Icebreaker.objects.filter(owner_id=user.id).filter(status=1).first()

    return icebreaker


@swagger_auto_schema(
    method='get',
    manual_parameters=[
        openapi.Parameter(
            'ship_name',
            openapi.IN_QUERY,
            type=openapi.TYPE_STRING
        )
    ]
)
@api_view(["GET"])
def search_ships(request):
    ship_name = request.GET.get("ship_name", "")

    ship = Ship.objects.filter(status=1).filter(ship_name__icontains=ship_name)

    serializer = ShipSerializer(ship, many=True)

    draft_icebreaker = get_draft_icebreaker(request)

    resp = {
        "ships": serializer.data,
        "ships_count": len(serializer.data),
        "draft_icebreaker_id": draft_icebreaker.pk if draft_icebreaker else None
    }

    return Response(resp)


@api_view(["GET"])
def get_ship_by_id(request, ship_id):
    if not Ship.objects.filter(pk=ship_id).exists():
        return Response(status=status.HTTP_404_NOT_FOUND)

    ship = Ship.objects.get(pk=ship_id)
    serializer = ShipSerializer(ship, many=False)

    return Response(serializer.data)


@api_view(["PUT"])
@permission_classes([IsModerator])
def update_ship(request, ship_id):
    if not Ship.objects.filter(pk=ship_id).exists():
        return Response(status=status.HTTP_404_NOT_FOUND)

    ship = Ship.objects.get(pk=ship_id)

    image = request.data.get("image")
    if image is not None:
        ship.image = image
        ship.save()

    serializer = ShipSerializer(ship, data=request.data, many=False, partial=True)

    if serializer.is_valid():
        serializer.save()

    return Response(serializer.data)


@api_view(["POST"])
@permission_classes([IsModerator])
def create_ship(request):
    ship = Ship.objects.create()

    serializer = ShipSerializer(ship)

    return Response(serializer.data)


@api_view(["DELETE"])
@permission_classes([IsModerator])
def delete_ship(request, ship_id):
    if not Ship.objects.filter(pk=ship_id).exists():
        return Response(status=status.HTTP_404_NOT_FOUND)

    ship = Ship.objects.get(pk=ship_id)
    ship.status = 2
    ship.save()

    ship = Ship.objects.filter(status=1)
    serializer = ShipSerializer(ship, many=True)

    return Response(serializer.data)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def add_ship_to_icebreaker(request, ship_id):
    if not Ship.objects.filter(pk=ship_id).exists():
        return Response(status=status.HTTP_404_NOT_FOUND)

    ship = Ship.objects.get(pk=ship_id)

    draft_icebreaker = get_draft_icebreaker(request)

    if draft_icebreaker is None:
        draft_icebreaker = Icebreaker.objects.create()
        draft_icebreaker.date_created = timezone.now()
        draft_icebreaker.owner = identity_user(request)
        draft_icebreaker.save()

    if ShipIcebreaker.objects.filter(icebreaker=draft_icebreaker, ship=ship).exists():
        return Response(status=status.HTTP_405_METHOD_NOT_ALLOWED)

    item = ShipIcebreaker.objects.create()
    item.icebreaker = draft_icebreaker
    item.ship = ship
    item.save()

    serializer = IcebreakerSerializer(draft_icebreaker, many=False)

    return Response(serializer.data["ships"])


@api_view(["POST"])
@permission_classes([IsModerator])
def update_ship_image(request, ship_id):
    if not Ship.objects.filter(pk=ship_id).exists():
        return Response(status=status.HTTP_404_NOT_FOUND)

    ship = Ship.objects.get(pk=ship_id)

    image = request.data.get("image")
    if image is not None:
        ship.image = image
        ship.save()

    serializer = ShipSerializer(ship)

    return Response(serializer.data)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def search_icebreakers(request):
    user = identity_user(request)

    status_id = int(request.GET.get("status", 0))
    date_formation_start = request.GET.get("date_formation_start")
    date_formation_end = request.GET.get("date_formation_end")

    icebreakers = Icebreaker.objects.exclude(status__in=[1, 5])

    if not user.is_staff:
        icebreakers = icebreakers.filter(owner=user)

    if status_id > 0:
        icebreakers = icebreakers.filter(status=status_id)

    if date_formation_start and parse_datetime(date_formation_start):
        icebreakers = icebreakers.filter(date_formation__gte=parse_datetime(date_formation_start))

    if date_formation_end and parse_datetime(date_formation_end):
        icebreakers = icebreakers.filter(date_formation__lt=parse_datetime(date_formation_end))

    serializer = IcebreakersSerializer(icebreakers, many=True)

    return Response(serializer.data)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def get_icebreaker_by_id(request, icebreaker_id):
    user = identity_user(request)

    if not Icebreaker.objects.filter(pk=icebreaker_id, owner=user).exists():
        return Response(status=status.HTTP_404_NOT_FOUND)

    icebreaker = Icebreaker.objects.get(pk=icebreaker_id)
    serializer = IcebreakerSerializer(icebreaker, many=False)

    return Response(serializer.data)


@swagger_auto_schema(method='put', request_body=IcebreakerSerializer)
@api_view(["PUT"])
@permission_classes([IsAuthenticated])
def update_icebreaker(request, icebreaker_id):
    if not Icebreaker.objects.filter(pk=icebreaker_id).exists():
        return Response(status=status.HTTP_404_NOT_FOUND)

    icebreaker = Icebreaker.objects.get(pk=icebreaker_id)
    serializer = IcebreakerSerializer(icebreaker, data=request.data, many=False, partial=True)

    if serializer.is_valid():
        serializer.save()

    return Response(serializer.data)


@api_view(["PUT"])
@permission_classes([IsAuthenticated])
def update_status_user(request, icebreaker_id):
    if not Icebreaker.objects.filter(pk=icebreaker_id).exists():
        return Response(status=status.HTTP_404_NOT_FOUND)

    icebreaker = Icebreaker.objects.get(pk=icebreaker_id)

    icebreaker.status = 2
    icebreaker.date_formation = timezone.now()
    icebreaker.save()

    serializer = IcebreakerSerializer(icebreaker, many=False)

    return Response(serializer.data)


@api_view(["PUT"])
@permission_classes([IsModerator])
def update_status_admin(request, icebreaker_id):
    if not Icebreaker.objects.filter(pk=icebreaker_id).exists():
        return Response(status=status.HTTP_404_NOT_FOUND)

    request_status = int(request.data["status"])

    if request_status not in [3, 4]:
        return Response(status=status.HTTP_405_METHOD_NOT_ALLOWED)

    icebreaker = Icebreaker.objects.get(pk=icebreaker_id)

    if icebreaker.status != 2:
        return Response(status=status.HTTP_405_METHOD_NOT_ALLOWED)

    icebreaker.status = request_status
    icebreaker.date_complete = timezone.now()
    icebreaker.moderator = identity_user(request)
    icebreaker.save()

    serializer = IcebreakerSerializer(icebreaker, many=False)

    return Response(serializer.data)


@api_view(["DELETE"])
@permission_classes([IsAuthenticated])
def delete_icebreaker(request, icebreaker_id):
    if not Icebreaker.objects.filter(pk=icebreaker_id).exists():
        return Response(status=status.HTTP_404_NOT_FOUND)

    icebreaker = Icebreaker.objects.get(pk=icebreaker_id)

    if icebreaker.status != 1:
        return Response(status=status.HTTP_405_METHOD_NOT_ALLOWED)

    icebreaker.status = 5
    icebreaker.save()

    return Response(status=status.HTTP_200_OK)


@api_view(["DELETE"])
@permission_classes([IsAuthenticated])
def delete_ship_from_icebreaker(request, icebreaker_id, ship_id):
    if not ShipIcebreaker.objects.filter(icebreaker_id=icebreaker_id, ship_id=ship_id).exists():
        return Response(status=status.HTTP_404_NOT_FOUND)

    item = ShipIcebreaker.objects.get(icebreaker_id=icebreaker_id, ship_id=ship_id)
    item.delete()

    icebreaker = Icebreaker.objects.get(pk=icebreaker_id)

    serializer = IcebreakerSerializer(icebreaker, many=False)
    ships = serializer.data["ships"]

    if len(ships) == 0:
        icebreaker.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    return Response(ships)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def get_ship_icebreaker(request, icebreaker_id, ship_id):
    if not ShipIcebreaker.objects.filter(ship_id=ship_id, icebreaker_id=icebreaker_id).exists():
        return Response(status=status.HTTP_404_NOT_FOUND)

    item = ShipIcebreaker.objects.get(ship_id=ship_id, icebreaker_id=icebreaker_id)

    serializer = ShipIcebreakerSerializer(item, many=False)

    return Response(serializer.data)


@swagger_auto_schema(method='PUT', request_body=ShipIcebreakerSerializer)
@api_view(["PUT"])
@permission_classes([IsAuthenticated])
def update_ship_in_icebreaker(request, icebreaker_id, ship_id):
    if not ShipIcebreaker.objects.filter(ship_id=ship_id, icebreaker_id=icebreaker_id).exists():
        return Response(status=status.HTTP_404_NOT_FOUND)

    item = ShipIcebreaker.objects.get(ship_id=ship_id, icebreaker_id=icebreaker_id)

    serializer = ShipIcebreakerSerializer(item, data=request.data, many=False, partial=True)

    if serializer.is_valid():
        serializer.save()

    return Response(serializer.data)


@swagger_auto_schema(method='post', request_body=UserLoginSerializer)
@api_view(["POST"])
def login(request):
    serializer = UserLoginSerializer(data=request.data)

    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_401_UNAUTHORIZED)

    user = authenticate(**serializer.data)
    if user is None:
        return Response(status=status.HTTP_401_UNAUTHORIZED)

    access_token = create_access_token(user.id)

    serializer = UserSerializer(user)

    response = Response(serializer.data, status=status.HTTP_201_CREATED)

    response.set_cookie('access_token', access_token, httponly=True)

    return response


@swagger_auto_schema(method='post', request_body=UserRegisterSerializer)
@api_view(["POST"])
def register(request):
    serializer = UserRegisterSerializer(data=request.data)

    if not serializer.is_valid():
        return Response(status=status.HTTP_409_CONFLICT)

    user = serializer.save()

    access_token = create_access_token(user.id)

    serializer = UserSerializer(user)

    response = Response(serializer.data, status=status.HTTP_201_CREATED)

    response.set_cookie('access_token', access_token, httponly=True)

    return response


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def check(request):
    user = identity_user(request)
    serializer = UserSerializer(user, many=False)
    return Response(serializer.data, status=status.HTTP_200_OK)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def logout(request):
    access_token = get_access_token(request)

    if access_token not in cache:
        cache.set(access_token, settings.JWT["ACCESS_TOKEN_LIFETIME"])

    return Response(status=status.HTTP_200_OK)


@swagger_auto_schema(method='PUT', request_body=UserSerializer)
@api_view(["PUT"])
@permission_classes([IsAuthenticated])
def update_user(request, user_id):
    if not User.objects.filter(pk=user_id).exists():
        return Response(status=status.HTTP_404_NOT_FOUND)

    user = User.objects.get(pk=user_id)
    serializer = UserSerializer(user, data=request.data, many=False, partial=True)

    if not serializer.is_valid():
        return Response(status=status.HTTP_409_CONFLICT)

    serializer.save()

    return Response(serializer.data)