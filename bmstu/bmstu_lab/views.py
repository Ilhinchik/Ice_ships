from django.contrib.auth import authenticate
from django.http import HttpResponse
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema

from .jwt_helper import *
from .permissions import *
from .serializers import *
from .utils import identity_user


def get_draft_icebreaker():
    user = identity_user(request)

    if user is None:
        return None

    icebreaker = Icebreaker.objects.filter(owner_id=user.id).filter(status=1).first()

    return icebreaker


def get_user():
    return User.objects.filter(is_superuser=False).first()


def get_moderator():
    return User.objects.filter(is_superuser=True).first()

@swagger_auto_schema(
    method='get',
    manual_parameters=[
        openapi.Parameter(
            'query',
            openapi.IN_QUERY,
            type=openapi.TYPE_STRING
        )
    ]
)
@api_view(["GET"]) # 1
def search_ships(request):
    ship_name = request.GET.get("ship_name", "")

    ships = Ship.objects.filter(status=1).filter(ship_name__icontains=ship_name)

    serializer = ShipSerializer(ships, many=True)

    draft_icebreaker = get_draft_icebreaker()

    resp = {
        "ships": serializer.data,
        "ships_count": len(serializer.data),
        "draft_icebreaker": draft_icebreaker.pk if draft_icebreaker else None
    }

    return Response(resp)


@api_view(["GET"]) # 1
def get_ship_by_id(request, ship_id):
    if not Ship.objects.filter(pk=ship_id).exists():
        return Response(status=status.HTTP_404_NOT_FOUND)

    ship = Ship.objects.get(pk=ship_id)
    serializer = ShipSerializer(ship, many=False)

    return Response(serializer.data)


@api_view(["PUT"]) # 1
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


@api_view(["POST"]) # 1
def create_ship(request):
    data = request.data

    required_fields = ['ship_name', 'year', 'ice_class', 'length', 'engine', 'description']
    for field in required_fields:
        if field not in data:
            return Response({'error': f'Missing required field: {field}'}, status=400)
        

    ship = Ship.objects.create(**data)
    serializer = ShipSerializer(ship)


    return Response(serializer.data)


@api_view(["DELETE"]) # 1
def delete_ship(request, ship_id):
    if not Ship.objects.filter(pk=ship_id).exists():
        return Response(status=status.HTTP_404_NOT_FOUND)

    ship = Ship.objects.get(pk=ship_id)
    ship.status = 2
    ship.save()

    ships = Ship.objects.filter(status=1)
    serializer = ShipSerializer(ships, many=True)

    return Response(serializer.data)


@api_view(["POST"]) # 1
def add_ship_to_icebreaker(request, ship_id):
    if not Ship.objects.filter(pk=ship_id).exists():
        return Response({'error': 'Ship not found'}, status=status.HTTP_404_NOT_FOUND)

    ship = Ship.objects.get(pk=ship_id)

    draft_icebreaker = get_draft_icebreaker()

    if draft_icebreaker is None:
        draft_icebreaker = Icebreaker.objects.create()
        draft_icebreaker.owner = get_user()
        draft_icebreaker.date_created = timezone.now()
        draft_icebreaker.save()

    if ShipIcebreaker.objects.filter(icebreaker=draft_icebreaker, ship=ship).exists():
        return Response({'error': 'Ship already added to this icebreaker'}, status=status.HTTP_405_METHOD_NOT_ALLOWED)
    
    item = ShipIcebreaker.objects.create(icebreaker=draft_icebreaker, ship=ship)
    item.save()

    serializer = IcebreakerSerializer(draft_icebreaker, many=False)

    return Response(serializer.data)



@api_view(["POST"]) # 1
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



@api_view(["GET"]) # 1
def search_icebreakers(request):
    status = int(request.GET.get("status", 0))
    date_formation_start = request.GET.get("date_formation_start")
    date_formation_end = request.GET.get("date_formation_end")

    icebreakers = Icebreaker.objects.exclude(status__in=[1, 5])

    if status > 0:
        icebreakers = icebreakers.filter(status=status)

    if date_formation_start and parse_datetime(date_formation_start):
        icebreakers = icebreakers.filter(date_formation__gte=parse_datetime(date_formation_start))

    if date_formation_end and parse_datetime(date_formation_end):
        icebreakers = icebreakers.filter(date_formation__lt=parse_datetime(date_formation_end))

    serializer = IcebreakersSerializer(icebreakers, many=True)

    return Response(serializer.data)


@api_view(["GET"]) # 1
def get_icebreaker_by_id(request, icebreaker_id):
    if not Icebreaker.objects.filter(pk=icebreaker_id).exists():
        return Response(status=status.HTTP_404_NOT_FOUND)

    icebreaker = Icebreaker.objects.get(pk=icebreaker_id)
    serializer = IcebreakerSerializer(icebreaker, many=False)

    return Response(serializer.data)


@api_view(["PUT"]) # 1
def update_icebreaker(request, icebreaker_id):
    if not Icebreaker.objects.filter(pk=icebreaker_id).exists():
        return Response(status=status.HTTP_404_NOT_FOUND)

    icebreaker = Icebreaker.objects.get(pk=icebreaker_id)
    serializer = IcebreakerSerializer(icebreaker, data=request.data, many=False, partial=True)

    if serializer.is_valid():
        serializer.save()

    return Response(serializer.data)


@api_view(["PUT"])  # 1
def update_status_user(request, icebreaker_id):
    if not Icebreaker.objects.filter(pk=icebreaker_id).exists():
        return Response(status=status.HTTP_404_NOT_FOUND)

    icebreaker = Icebreaker.objects.get(pk=icebreaker_id)

    if icebreaker.status != 1:
        return Response(status=status.HTTP_405_METHOD_NOT_ALLOWED)

    icebreaker.status = 2
    icebreaker.date_formation = timezone.now()
    icebreaker.save()

    serializer = IcebreakerSerializer(icebreaker, many=False)

    return Response(serializer.data)


@api_view(["PUT"]) # 1
def update_status_admin(request, icebreaker_id):
    if not Icebreaker.objects.filter(pk=icebreaker_id).exists():
        return Response(status=status.HTTP_404_NOT_FOUND)

    request_status = int(request.data["status"])

    if request_status not in [3, 4]:
        return Response(status=status.HTTP_405_METHOD_NOT_ALLOWED)

    icebreaker = Icebreaker.objects.get(pk=icebreaker_id)

    if icebreaker.status != 2:
        return Response(status=status.HTTP_405_METHOD_NOT_ALLOWED)

    icebreaker.date_complete = timezone.now()
    icebreaker.status = request_status
    icebreaker.moderator = get_moderator()
    icebreaker.save()

    serializer = IcebreakerSerializer(icebreaker, many=False)

    return Response(serializer.data)


@api_view(["DELETE"]) # 1
def delete_icebreaker(request, icebreaker_id):
    if not Icebreaker.objects.filter(pk=icebreaker_id).exists():
        return Response(status=status.HTTP_404_NOT_FOUND)

    icebreaker = Icebreaker.objects.get(pk=icebreaker_id)

    if icebreaker.status != 1:
        return Response(status=status.HTTP_405_METHOD_NOT_ALLOWED)

    icebreaker.status = 5
    icebreaker.save()

    serializer = IcebreakerSerializer(icebreaker, many=False)

    return Response(serializer.data)


@api_view(["DELETE"]) # 1
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


@api_view(["PUT"]) # 1
def update_ship_in_icebreaker(request, icebreaker_id, ship_id):
    if not ShipIcebreaker.objects.filter(ship_id=ship_id, icebreaker_id=icebreaker_id).exists():
        return Response(status=status.HTTP_404_NOT_FOUND)

    item = ShipIcebreaker.objects.get(ship_id=ship_id, icebreaker_id=icebreaker_id)

    serializer = ShipIcebreakerSerializer(item, data=request.data, many=False, partial=True)

    if serializer.is_valid():
        serializer.save()

    return Response(serializer.data)


@api_view(["POST"]) # 1
def register(request):
    serializer = UserRegisterSerializer(data=request.data)

    if not serializer.is_valid():
        return Response(status=status.HTTP_409_CONFLICT)

    user = serializer.save()

    serializer = UserSerializer(user)

    return Response(serializer.data, status=status.HTTP_201_CREATED)


@api_view(["POST"]) # 1
def login(request):
    serializer = UserLoginSerializer(data=request.data)

    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_401_UNAUTHORIZED)

    user = authenticate(**serializer.data)
    if user is None:
        return Response(status=status.HTTP_401_UNAUTHORIZED)

    return Response(status=status.HTTP_200_OK)


@api_view(["POST"]) # 1
def logout(request):
    return Response(status=status.HTTP_200_OK)


@api_view(["PUT"]) # 1
def update_user(request, user_id):
    if not User.objects.filter(pk=user_id).exists():
        return Response(status=status.HTTP_404_NOT_FOUND)

    user = User.objects.get(pk=user_id)
    serializer = UserSerializer(user, data=request.data, many=False, partial=True)

    if not serializer.is_valid():
        return Response(status=status.HTTP_409_CONFLICT)

    serializer.save()

    return Response(serializer.data)