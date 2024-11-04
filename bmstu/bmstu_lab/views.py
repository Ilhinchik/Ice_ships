import requests
import os
import uuid
from dateutil.parser import parse
from django.core.files.storage import default_storage
from django.contrib.auth import authenticate
from django.utils.dateparse import parse_datetime
from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes, authentication_classes, parser_classes
from rest_framework.response import Response
from django.db import transaction
from rest_framework.permissions import AllowAny
from .auth import AuthBySessionID, AuthBySessionIDIfExists, IsAuth, IsManagerAuth
from .redis import session_storage
from rest_framework.parsers import FormParser, MultiPartParser, JSONParser
from drf_yasg import openapi

from .serializers import *



def get_draft_icebreaker(request):
    user = request.user

    # Проверка на аутентификацию пользователя
    if user is None or not user.is_authenticated:
        return None

    # Поиск черновика ледокола для данного пользователя со статусом 1 (например, черновик)
    icebreaker = Icebreaker.objects.filter(owner=user, status=1).first()

    # Логирование для отладки (опционально)
    if icebreaker:
        print(f"Draft icebreaker found: {icebreaker.id}")
    else:
        print("No draft icebreaker found for user")

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
@permission_classes([AllowAny])
def search_ships(request):
    ship_name = request.GET.get("ship_name", "")

    ships = Ship.objects.filter(status=1)

    if ship_name:
        ships = ships.filter(ship_name__icontains=ship_name)

    serializer = ShipSerializer(ships, many=True)

    draft_icebreaker = get_draft_icebreaker(request)

    resp = {
        "ships": serializer.data,
        "ships_count": ShipIcebreaker.objects.filter(icebreaker=draft_icebreaker).count() if draft_icebreaker else None,
        "draft_icebreaker_id": draft_icebreaker.pk if draft_icebreaker else None
    }

    return Response(resp)


@swagger_auto_schema(method='get',
                     responses={
                         status.HTTP_200_OK: ShipSerializer(),
                         status.HTTP_404_NOT_FOUND: "Not Found",
                     })
@api_view(["GET"])
@permission_classes([AllowAny])
def get_ship_by_id(request, ship_id):
    if not Ship.objects.filter(pk=ship_id).exists():
        return Response(status=status.HTTP_404_NOT_FOUND)

    ship = Ship.objects.get(pk=ship_id)
    serializer = ShipSerializer(ship)

    return Response(serializer.data)

@swagger_auto_schema(method='put',
                     request_body=ShipSerializer,
                     responses={
                         status.HTTP_200_OK: ShipSerializer(),
                         status.HTTP_400_BAD_REQUEST: "Bad Request",
                         status.HTTP_403_FORBIDDEN: "Forbidden",
                         status.HTTP_404_NOT_FOUND: "Not Found",
                     })
@api_view(["PUT"])
@permission_classes([IsManagerAuth])
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


@swagger_auto_schema(method='post',
                     request_body=ShipSerializer,
                     responses={
                         status.HTTP_200_OK: ShipSerializer(),
                         status.HTTP_400_BAD_REQUEST: "Bad Request",
                         status.HTTP_403_FORBIDDEN: "Forbidden",
                     })
@api_view(["POST"])
@permission_classes([IsManagerAuth])
def create_ship(request):

    serializer = ShipSerializer(data=request.data)

    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@swagger_auto_schema(method='delete',
                     responses={
                         status.HTTP_200_OK: "OK",
                         status.HTTP_403_FORBIDDEN: "Forbidden",
                         status.HTTP_404_NOT_FOUND: "Not Found",
                     })
@api_view(["DELETE"])
@permission_classes([IsManagerAuth])
def delete_ship(request, ship_id):
    if not Ship.objects.filter(pk=ship_id).exists():
        return Response(status=status.HTTP_404_NOT_FOUND)

    ship = Ship.objects.get(pk=ship_id)
    ship.status = 2
    ship.save()

    ship = Ship.objects.filter(status=1)
    serializer = ShipSerializer(ship, many=True)

    return Response(serializer.data)


@swagger_auto_schema(method='post',
                     responses={
                         status.HTTP_200_OK: "OK",
                         status.HTTP_403_FORBIDDEN: "Forbidden",
                         status.HTTP_404_NOT_FOUND: "Not Found",
                     }) 
@api_view(["POST"])
@permission_classes([IsAuth])
@authentication_classes([AuthBySessionID])
def add_ship_to_icebreaker(request, ship_id):
    user = request.user

    if not Ship.objects.filter(pk=ship_id).exists():
        return Response(status=status.HTTP_404_NOT_FOUND)

    ship = Ship.objects.get(pk=ship_id)

    draft_icebreaker = get_draft_icebreaker(request)

    if draft_icebreaker is None:
        draft_icebreaker = Icebreaker.objects.create(
            date_created = timezone.now(),
            owner = user
        )


    if ShipIcebreaker.objects.filter(icebreaker=draft_icebreaker, ship=ship).exists():
        return Response({"error": "Ship already added to this icebreaker"}, status=status.HTTP_405_METHOD_NOT_ALLOWED)

    item = ShipIcebreaker.objects.create(icebreaker = draft_icebreaker, ship = ship)

    serializer = IcebreakerSerializer(draft_icebreaker)
    return Response(serializer.data)

@swagger_auto_schema(method="post",
                     manual_parameters=[
                         openapi.Parameter(name="image",
                                           in_=openapi.IN_QUERY,
                                           type=openapi.TYPE_FILE,
                                           required=True, description="Image")],
                     responses={
                         status.HTTP_200_OK: "OK",
                         status.HTTP_400_BAD_REQUEST: "Bad Request",
                         status.HTTP_403_FORBIDDEN: "Forbidden",
                     })
@api_view(["POST"])
@permission_classes([IsManagerAuth])
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


@swagger_auto_schema(method='get',
                     manual_parameters=[
                         openapi.Parameter('status',
                                           type=openapi.TYPE_STRING,
                                           description='status',
                                           in_=openapi.IN_QUERY)
                     ],
                     responses={
                         status.HTTP_200_OK: ShipSerializer(many=True),
                         status.HTTP_403_FORBIDDEN: "Forbidden",
                     })
@api_view(["GET"])
@permission_classes([IsAuth])
@authentication_classes([AuthBySessionID])
def search_icebreakers(request):
    status_id = int(request.GET.get("status", 0))
    date_formation_start = request.GET.get("date_formation_start")
    date_formation_end = request.GET.get("date_formation_end")

    icebreakers = Icebreaker.objects.exclude(status__in=[1, 5])

    if not request.user.is_staff:
        icebreakers = icebreakers.filter(owner=request.user)

    if status_id > 0:
        icebreakers = icebreakers.filter(status=status_id)

    # Add date filters with error handling
    if date_formation_start:
        try:
            parsed_start_date = parse_datetime(date_formation_start)
            if parsed_start_date:
                icebreakers = icebreakers.filter(date_formation__gte=parsed_start_date)
            else:
                raise ValueError("Invalid date format for date_formation_start")
        except ValueError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

    if date_formation_end:
        try:
            parsed_end_date = parse_datetime(date_formation_end)
            if parsed_end_date:
                icebreakers = icebreakers.filter(date_formation__lt=parsed_end_date)
            else:
                raise ValueError("Invalid date format for date_formation_end")
        except ValueError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

    serializer = IcebreakersSerializer(icebreakers, many=True)
    return Response(serializer.data)


@swagger_auto_schema(method='get',
                     responses={
                         status.HTTP_200_OK: IcebreakerSerializer(),
                         status.HTTP_403_FORBIDDEN: "Forbidden",
                         status.HTTP_404_NOT_FOUND: "Not Found",
                     })
@api_view(["GET"])
@permission_classes([IsAuth])
@authentication_classes([AuthBySessionID])
def get_icebreaker_by_id(request, icebreaker_id):
    user = request.user

    if not Icebreaker.objects.filter(pk=icebreaker_id, owner=user).exists():
        return Response(status=status.HTTP_404_NOT_FOUND)

    icebreaker = Icebreaker.objects.get(pk=icebreaker_id)
    serializer = IcebreakerSerializer(icebreaker)

    return Response(serializer.data)


@swagger_auto_schema(method='put',
                     request_body=IcebreakerSerializer,
                     responses={
                         status.HTTP_200_OK: IcebreakerSerializer(),
                         status.HTTP_400_BAD_REQUEST: "Bad Request",
                         status.HTTP_403_FORBIDDEN: "Forbidden",
                         status.HTTP_404_NOT_FOUND: "Not Found",
                     })
@api_view(["PUT"])
@permission_classes([IsAuth])
@authentication_classes([AuthBySessionID])
def update_icebreaker(request, icebreaker_id):
    user = request.user

    if not Icebreaker.objects.filter(pk=icebreaker_id, owner=user).exists():
        return Response(status=status.HTTP_404_NOT_FOUND)

    icebreaker = Icebreaker.objects.get(pk=icebreaker_id)
    serializer = IcebreakerSerializer(icebreaker, data=request.data, partial=True)

    if serializer.is_valid():
        serializer.save()

    return Response(serializer.data)

@swagger_auto_schema(method='put',
                     responses={
                         status.HTTP_200_OK: IcebreakerSerializer(),
                         status.HTTP_400_BAD_REQUEST: "Bad Request",
                         status.HTTP_403_FORBIDDEN: "Forbidden",
                         status.HTTP_404_NOT_FOUND: "Not Found",
                     })
@api_view(["PUT"])
@permission_classes([IsAuth])
@authentication_classes([AuthBySessionID])
def update_status_user(request, icebreaker_id):
    user = request.user

    if not Icebreaker.objects.filter(pk=icebreaker_id, owner=user).exists():
        return Response(status=status.HTTP_404_NOT_FOUND)

    icebreaker = Icebreaker.objects.get(pk=icebreaker_id)

    if icebreaker.status != 1:
        return Response(status=status.HTTP_405_METHOD_NOT_ALLOWED)

    icebreaker.status = 2
    icebreaker.date_formation = timezone.now()
    icebreaker.save()

    serializer = IcebreakerSerializer(icebreaker)

    return Response(serializer.data)


@swagger_auto_schema(method='put',
                     responses={
                         status.HTTP_200_OK: IcebreakerSerializer(),
                         status.HTTP_403_FORBIDDEN: "Forbidden",
                         status.HTTP_404_NOT_FOUND: "Not Found",
                     })
@api_view(["PUT"])
@permission_classes([IsManagerAuth])
@authentication_classes([AuthBySessionID])
def update_status_admin(request, icebreaker_id):
    if not Icebreaker.objects.filter(pk=icebreaker_id).exists():
        return Response(status=status.HTTP_404_NOT_FOUND)
    
    user = request.user

    request_status = int(request.data["status"])

    if request_status not in [3, 4]:
        return Response(status=status.HTTP_405_METHOD_NOT_ALLOWED)

    icebreaker = Icebreaker.objects.get(pk=icebreaker_id)

    if icebreaker.status != 2:
        return Response(status=status.HTTP_405_METHOD_NOT_ALLOWED)

    icebreaker.status = request_status
    icebreaker.date_complete = timezone.now()
    icebreaker.status = request_status
    icebreaker.moderator = user
    icebreaker.update_result()
    icebreaker.save()

    serializer = IcebreakerSerializer(icebreaker)

    return Response(serializer.data)

@swagger_auto_schema(method='delete',
                     responses={
                         status.HTTP_200_OK: "OK",
                         status.HTTP_403_FORBIDDEN: "Forbidden",
                         status.HTTP_404_NOT_FOUND: "Not Found",
                     })
@api_view(["DELETE"])
@permission_classes([IsAuth])
@authentication_classes([AuthBySessionID])
def delete_icebreaker(request, icebreaker_id):
    user = request.user

    if not Icebreaker.objects.filter(pk=icebreaker_id, owner=user).exists():
        return Response(status=status.HTTP_404_NOT_FOUND)

    icebreaker = Icebreaker.objects.get(pk=icebreaker_id)

    if icebreaker.status != 1:
        return Response(status=status.HTTP_405_METHOD_NOT_ALLOWED)

    icebreaker.status = 5
    icebreaker.save()

    return Response(status=status.HTTP_200_OK)


@swagger_auto_schema(method='delete',
                     responses={
                         status.HTTP_200_OK: "OK",
                         status.HTTP_403_FORBIDDEN: "Forbidden",
                         status.HTTP_404_NOT_FOUND: "Not Found",
                     })
@api_view(["DELETE"])
@permission_classes([IsAuth])
@authentication_classes([AuthBySessionID])
def delete_ship_from_icebreaker(request, icebreaker_id, ship_id):
    user = request.user

    if not Icebreaker.objects.filter(pk=icebreaker_id, owner=user).exists():
        return Response(status=status.HTTP_404_NOT_FOUND)

    if not ShipIcebreaker.objects.filter(icebreaker_id=icebreaker_id, ship_id=ship_id).exists():
        return Response(status=status.HTTP_404_NOT_FOUND)

    item = ShipIcebreaker.objects.get(icebreaker_id=icebreaker_id, ship_id=ship_id)
    item.delete()

    icebreaker = Icebreaker.objects.get(pk=icebreaker_id)

    serializer = IcebreakerSerializer(icebreaker)
    ships = serializer.data["ships"]

    if len(ships) == 0:
        icebreaker.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    return Response(ships)


@swagger_auto_schema(method='get',
                     responses={
                         status.HTTP_200_OK: ShipIcebreakerSerializer(),
                         status.HTTP_403_FORBIDDEN: "Forbidden",
                         status.HTTP_404_NOT_FOUND: "Not Found",
                     })
@api_view(["GET"])
@permission_classes([IsAuth])
@authentication_classes([AuthBySessionID])
def get_ship_icebreaker(request, icebreaker_id, ship_id):
    user = request.user

    if not Icebreaker.objects.filter(pk=icebreaker_id, owner=user).exists():
        return Response(status=status.HTTP_404_NOT_FOUND)

    if not ShipIcebreaker.objects.filter(ship_id=ship_id, icebreaker_id=icebreaker_id).exists():
        return Response(status=status.HTTP_404_NOT_FOUND)

    item = ShipIcebreaker.objects.get(ship_id=ship_id, icebreaker_id=icebreaker_id)

    serializer = ShipIcebreakerSerializer(item)

    return Response(serializer.data)


@swagger_auto_schema(method='put',
                     request_body=ShipIcebreakerSerializer,
                     responses={
                         status.HTTP_200_OK: ShipIcebreakerSerializer(),
                         status.HTTP_400_BAD_REQUEST: "Bad Request",
                         status.HTTP_403_FORBIDDEN: "Forbidden",
                         status.HTTP_404_NOT_FOUND: "Not Found",
                     })
@api_view(["PUT"])
@permission_classes([IsAuth])
@authentication_classes([AuthBySessionID])
def update_ship_in_icebreaker(request, icebreaker_id, ship_id):
    user = request.user
    if not ShipIcebreaker.objects.filter(ship_id=ship_id, icebreaker_id=icebreaker_id).exists():
        return Response(status=status.HTTP_404_NOT_FOUND)

    # Получаем текущую связь
    current_item = ShipIcebreaker.objects.get(ship_id=ship_id, icebreaker_id=icebreaker_id)
    current_order = current_item.order

    # Проверяем направление обмена из данных запроса
    direction = request.data.get("direction")
    if direction not in ["up", "down"]:
        return Response({"error": "Invalid direction"}, status=status.HTTP_400_BAD_REQUEST)

    # Определяем новое значение порядка для обмена
    if direction == "up":
        # Получаем соседний объект с порядком выше текущего
        neighbor = ShipIcebreaker.objects.filter(
            icebreaker_id=icebreaker_id, order__lt=current_order
        ).order_by("-order").first()
    elif direction == "down":
        # Получаем соседний объект с порядком ниже текущего
        neighbor = ShipIcebreaker.objects.filter(
            icebreaker_id=icebreaker_id, order__gt=current_order
        ).order_by("order").first()

    if not neighbor:
        # Если соседнего объекта нет, значит текущий объект уже в крайнем положении
        return Response({"error": "Cannot move further in this direction"}, status=status.HTTP_400_BAD_REQUEST)

    # Обмен значениями порядка
    with transaction.atomic():
        current_item.order, neighbor.order = neighbor.order, current_item.order
        current_item.save()
        neighbor.save()

    # Возвращаем обновленные данные
    serializer = ShipIcebreakerSerializer(current_item)
    return Response(serializer.data)


@swagger_auto_schema(
    method='post',
    request_body=LoginSerializer,
    responses={
        status.HTTP_200_OK: "OK",
        status.HTTP_400_BAD_REQUEST: "Bad Request",
    }
)
@parser_classes([JSONParser])
@api_view(["POST"])
@permission_classes([AllowAny])
def login(request):
    """
    Вход
    """
    serializer = LoginSerializer(data=request.data)
    if serializer.is_valid():
        username = serializer.validated_data['username']
        password = serializer.validated_data['password']
        
        user = authenticate(request, username=username, password=password)
        if user is not None:
            session_id = str(uuid.uuid4())
            session_storage.set(session_id, username)
            response = Response(status=status.HTTP_201_CREATED)
            key="session_id"
            response.set_cookie(key, value=session_id, samesite="Lax", secure=False, httponly=True)
            print(f"Session ID set: {session_id}\nKey: {key}")
            return response
        else:
            return Response({'error': 'Invalid Credentials'}, status=status.HTTP_400_BAD_REQUEST)
    else:
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@swagger_auto_schema(method='post',
                     request_body=UserSerializer,
                     responses={
                         status.HTTP_201_CREATED: "Created",
                         status.HTTP_400_BAD_REQUEST: "Bad Request",
                     })
@api_view(["POST"])
def register(request):
    serializer = UserSerializer(data=request.data)

    if not serializer.is_valid():
        return Response(status=status.HTTP_409_CONFLICT)

    user = serializer.save()

    response = Response(serializer.data, status=status.HTTP_201_CREATED)

    return response


@swagger_auto_schema(method='post',
                     responses={
                         status.HTTP_204_NO_CONTENT: "No content",
                         status.HTTP_403_FORBIDDEN: "Forbidden",
                     })
@api_view(["POST"])
@permission_classes([IsAuth])
def logout(request):
    """
    Выход
    """
    session_id = request.COOKIES["session_id"]
    if session_storage.exists(session_id):
        session_storage.delete(session_id)
        return Response(status=status.HTTP_204_NO_CONTENT)

    return Response(status=status.HTTP_403_FORBIDDEN)


@swagger_auto_schema(method='put',
                     request_body=UserSerializer,
                     responses={
                         status.HTTP_200_OK: UserSerializer(),
                         status.HTTP_400_BAD_REQUEST: "Bad Request",
                         status.HTTP_403_FORBIDDEN: "Forbidden",
                     })
@api_view(["PUT"])
@permission_classes([IsAuth])
@authentication_classes([AuthBySessionID])
def update_user(request, user_id):
    if not User.objects.filter(pk=user_id).exists():
        return Response(status=status.HTTP_404_NOT_FOUND)

    user = request.user

    if user.pk != user_id:
        return Response(status=status.HTTP_404_NOT_FOUND)

    serializer = UserSerializer(user, data=request.data, partial=True)
    if not serializer.is_valid():
        return Response(status=status.HTTP_409_CONFLICT)

    serializer.save()

    return Response(serializer.data, status=status.HTTP_200_OK)
