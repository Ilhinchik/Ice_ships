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
from .minio import MinioStorage
from bmstu import settings
import time
from bmstu_lab.serializers import *
from .services import get_or_create_user_cart, \
    result_icebreaker, add_item_to_request
from django.db.models import Q
from datetime import datetime
from django.db import IntegrityError
from django.db.models.functions import TruncDate


@swagger_auto_schema(method='get',
                     manual_parameters=[
                         openapi.Parameter('ship_title',
                                           type=openapi.TYPE_STRING,
                                           description='ship_title',
                                           in_=openapi.IN_QUERY),
                     ],
                     responses={
                         status.HTTP_200_OK: GetShipSerializer,
                         status.HTTP_403_FORBIDDEN: "Forbidden",
                     })
@api_view(["GET"])
@permission_classes([AllowAny])
@authentication_classes([AuthBySessionIDIfExists])
def search_ships(request):

    user = request.user

    ship_name = request.query_params.get("ship_name", "")
    ship_list = Ship.objects.filter(
        ship_name__icontains=ship_name, is_active=True).order_by('-id')

    req = None
    items_in_cart = 0

    if user is not None:
        req = Icebreaker.objects.filter(owner_id=user.id,
                                        status=Icebreaker.RequestStatus.DRAFT).first()
        if req is not None:
            items_in_cart = ShipIcebreaker.objects.filter(
                icebreaker=req).count()

    serializer = GetShipSerializer(
        {
            "ship": ShipSerializer(ship_list, many=True).data,
            "icebreaker_id": req.id if req else None,
            "items_in_cart": items_in_cart,
        },
    )
    time.sleep(0.25)  # ДЛЯ ДЕМОНСТРАЦИИ АНИМАЦИИ ЗАГРУЗКИ НА ФРОНТЕ
    return Response(serializer.data, status=status.HTTP_200_OK)


@swagger_auto_schema(method='get',
                     responses={
                         status.HTTP_200_OK: ShipSerializer(),
                         status.HTTP_404_NOT_FOUND: "Not Found",
                     })
@api_view(["GET"])
@permission_classes([AllowAny])
def get_ship_by_id(request, ship_id):
    """
    Получение корабля
    """
    ship = Ship.objects.filter(id=ship_id, is_active=True).first()
    if ship is None:
        return Response("Ship not found", status=status.HTTP_404_NOT_FOUND)
    serialized_ship = ShipSerializer(ship)
    return Response(serialized_ship.data, status=status.HTTP_200_OK)


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
    """
    Изменение корабля
    """
    ship = Ship.objects.filter(id=ship_id, is_active=True).first()
    if ship is None:
        return Response("Ship not found", status=status.HTTP_404_NOT_FOUND)

    serializer = ShipSerializer(ship, data=request.data, partial=True)
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data)
    else:
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@swagger_auto_schema(method='post',
                     request_body=ShipSerializer,
                     responses={
                         status.HTTP_200_OK: ShipSerializer(),
                         status.HTTP_400_BAD_REQUEST: "Bad Request",
                         status.HTTP_403_FORBIDDEN: "Forbidden",
                     })
@api_view(["POST"])
@permission_classes([IsManagerAuth])
@parser_classes([MultiPartParser, JSONParser])
def create_ship(request):
    """
    Создание ПО
    """
    serializer = ShipSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    new_ship = serializer.save()
    serializer = ShipSerializer(new_ship)
    return Response(serializer.data, status=status.HTTP_200_OK)


@swagger_auto_schema(method='delete',
                     responses={
                         status.HTTP_200_OK: "OK",
                         status.HTTP_403_FORBIDDEN: "Forbidden",
                         status.HTTP_404_NOT_FOUND: "Not Found",
                     })
@api_view(["DELETE"])
@permission_classes([IsManagerAuth])
def delete_ship(request, ship_id):
    """
    Удаление ПО
    """
    ship = Ship.objects.filter(id=ship_id, is_active=True).first()
    if ship is None:
        return Response("Ship not found", status=status.HTTP_404_NOT_FOUND)

    if ship.image != "":
        minio_storage = MinioStorage(endpoint=settings.MINIO_ENDPOINT_URL,
                                     access_key=settings.MINIO_ACCESS_KEY,
                                     secret_key=settings.MINIO_SECRET_KEY,
                                     secure=settings.MINIO_SECURE)
        file_extension = os.path.splitext(ship.image)[1]
        file_name = f"{ship_id}{file_extension}"
        try:
            minio_storage.delete_file(settings.MINIO_BUCKET_NAME, file_name)
        except Exception as e:
            return Response(f"Failed to delete image: {e}",
                            status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        ship.image = ""

    ship.is_active = False
    ship.save()
    return Response(status=status.HTTP_200_OK)


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
    """
    Добавление кораблә в заәвку на проводку
    """
    ship = Ship.objects.filter(id=ship_id, is_active=True).first()
    if ship is None:
        return Response("Ship not found", status=status.HTTP_404_NOT_FOUND)
    icebreaker_id = get_or_create_user_cart(request.user.id)

    try:
        add_item_to_request(icebreaker_id, ship_id)
    except IntegrityError:
        return Response(status=status.HTTP_400_BAD_REQUEST)
    return Response(status=status.HTTP_200_OK)


@swagger_auto_schema(method="post",
                     manual_parameters=[
                         openapi.Parameter(name="image",
                                           in_=openapi.IN_FORM,
                                           type=openapi.TYPE_FILE,
                                           required=True, description="Image")],
                     responses={
                         status.HTTP_200_OK: "OK",
                         status.HTTP_400_BAD_REQUEST: "Bad Request",
                         status.HTTP_403_FORBIDDEN: "Forbidden",
                     })
@api_view(["POST"])
@permission_classes([IsManagerAuth])
@parser_classes([MultiPartParser])
def update_ship_image(request, ship_id):
    ship = Ship.objects.filter(id=ship_id, is_active=True).first()
    if ship is None:
        return Response("Ship not found", status=status.HTTP_404_NOT_FOUND)

    minio_storage = MinioStorage(endpoint=settings.MINIO_ENDPOINT_URL,
                                 access_key=settings.MINIO_ACCESS_KEY,
                                 secret_key=settings.MINIO_SECRET_KEY,
                                 secure=settings.MINIO_SECURE)

    file = request.FILES.get("image")
    if not file:
        return Response(f"No image in request. Request contains: {request.FILES}", status=status.HTTP_400_BAD_REQUEST)

    file_extension = os.path.splitext(file.name)[1]
    file_name = f"{ship_id}{file_extension}"

    try:
        minio_storage.load_file(settings.MINIO_BUCKET_NAME, file_name, file)
    except Exception as e:
        return Response(f"Failed to load image: {e}", status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    ship.image = f"http://{settings.MINIO_ENDPOINT_URL}/{settings.MINIO_BUCKET_NAME}/{file_name}"
    ship.save()
    return Response(status=status.HTTP_200_OK)


@swagger_auto_schema(method='get',
                     manual_parameters=[
                         openapi.Parameter('status',
                                           type=openapi.TYPE_STRING,
                                           description='status',
                                           in_=openapi.IN_QUERY),
                         openapi.Parameter('formation_start',
                                           type=openapi.TYPE_STRING,
                                           description='status',
                                           in_=openapi.IN_QUERY,
                                           format=openapi.FORMAT_DATETIME),
                         openapi.Parameter('formation_end',
                                           type=openapi.TYPE_STRING,
                                           description='status',
                                           in_=openapi.IN_QUERY,
                                           format=openapi.FORMAT_DATETIME),
                     ],
                     responses={
                         status.HTTP_200_OK: IcebreakerSerializer(many=True),
                         status.HTTP_403_FORBIDDEN: "Forbidden",
                     })
@api_view(["GET"])
@permission_classes([IsAuth])
@authentication_classes([AuthBySessionID])
def search_icebreakers(request):
    """
    Получение списка заявок на проводку кораблей
    """
    status_filter = request.query_params.get("status")
    formation_datetime_start_filter = request.query_params.get(
        "formation_start")
    formation_datetime_end_filter = request.query_params.get("formation_end")

    filters = ~Q(status=Icebreaker.RequestStatus.DELETED)  # & ~Q(
    #     status=Icebreaker.RequestStatus.DRAFT)
    if status_filter is not None:
        filters &= Q(status=status_filter.upper())
    if formation_datetime_start_filter is not None:
        start_date = parse(formation_datetime_start_filter).date()
        filters &= Q(date_formation__date__gte=start_date)
        # filters &= Q(date_formation__gte=parse(
        #     formation_datetime_start_filter))
    if formation_datetime_end_filter is not None:
        end_date = parse(formation_datetime_end_filter).date()
        filters &= Q(date_formation__date__lte=end_date)
        # filters &= Q(date_formation__lte=parse(
        #     formation_datetime_end_filter))

    if not request.user.is_staff:
        filters &= Q(owner=request.user)

    icebreakers = Icebreaker.objects.filter(
        filters).select_related("owner").order_by('-id')
    serializer = IcebreakerSerializer(
        icebreakers, many=True)

    return Response(serializer.data, status=status.HTTP_200_OK)


@swagger_auto_schema(method='get',
                     responses={
                         status.HTTP_200_OK: FullIcebreakerSerializer(),
                         status.HTTP_403_FORBIDDEN: "Forbidden",
                         status.HTTP_404_NOT_FOUND: "Not Found",
                     })
@api_view(["GET"])
@permission_classes([IsAuth])
@authentication_classes([AuthBySessionID])
def get_icebreaker_by_id(request, icebreaker_id):
    """
    Получение заявки на проводку кораблей
    """
    filters = Q(id=icebreaker_id) & ~Q(status=Icebreaker.RequestStatus.DELETED)

    icebreaker = Icebreaker.objects.filter(filters).first()
    if icebreaker is None:
        return Response("Icebreaker not found", status=status.HTTP_404_NOT_FOUND)

    if not request.user.is_staff and icebreaker.owner != request.user:
        return Response(status=status.HTTP_403_FORBIDDEN)

    serializer = FullIcebreakerSerializer(icebreaker)
    return Response(serializer.data, status=status.HTTP_200_OK)


@swagger_auto_schema(method='put',
                     request_body=PutIcebreakerSerializer,
                     responses={
                         status.HTTP_200_OK: PutIcebreakerSerializer(),
                         status.HTTP_400_BAD_REQUEST: "Bad Request",
                         status.HTTP_403_FORBIDDEN: "Forbidden",
                         status.HTTP_404_NOT_FOUND: "Not Found",
                     })
@api_view(["PUT"])
@permission_classes([IsAuth])
@authentication_classes([AuthBySessionID])
def update_icebreaker(request, icebreaker_id):
    """
    Изменение заявки на проводку кораблей
    """
    icebreaker = Icebreaker.objects.filter(id=icebreaker_id,
                                           status=Icebreaker.RequestStatus.DRAFT).first()
    if icebreaker is None:
        return Response("Icebreaker not found", status=status.HTTP_404_NOT_FOUND)

    if not request.user.is_staff and icebreaker.owner != request.user:
        return Response(status=status.HTTP_403_FORBIDDEN)

    serializer = PutIcebreakerSerializer(icebreaker,
                                         data=request.data,
                                         partial=True)
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data)
    else:
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


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
    """
    Формирование заявки на установку ПО
    """
    icebreaker = Icebreaker.objects.filter(id=icebreaker_id,
                                           status=Icebreaker.RequestStatus.DRAFT).first()
    if icebreaker is None:
        return Response("Icebreaker not found", status=status.HTTP_404_NOT_FOUND)

    if not request.user.is_staff and icebreaker.owner != request.user:
        return Response(status=status.HTTP_403_FORBIDDEN)

    if icebreaker.start_point is None or icebreaker.start_point == "":
        return Response("Icebreaker.start_point is empty", status=status.HTTP_400_BAD_REQUEST)

    # if not is_valid_versions(pk):
    #     return Response("One or more software versions is empty", status=status.HTTP_400_BAD_REQUEST)

    icebreaker.status = Icebreaker.RequestStatus.FORMED
    icebreaker.date_formation = datetime.now()
    # Отправка запроса на асинхронный сервис
    url = 'http://127.0.0.1:8100/api/async_calc/'
    data = {
        'icebreaker_id': icebreaker_id,
    }
    try:
        response = requests.post(url, json=data)

        # if response.status_code == 200:
        #     # Получаем результат от асинхронного сервиса
        #     result_data = response.json().get('data', {})
        #     icebreaker.result = result_data.get('result', False)
        # else:
        #     icebreaker.result = False  # В случае ошибки устанавливаем результат в False

        icebreaker.save()
    except Exception as error:
        print(f"Error during async request: {error}")
        # icebreaker.result = False
        icebreaker.save()

    serializer = IcebreakerSerializer(icebreaker)
    return Response(serializer.data, status=status.HTTP_200_OK)


@swagger_auto_schema(method='put',
                     request_body=ResolveIcebreakerSerializer,
                     responses={
                         status.HTTP_200_OK: ResolveIcebreakerSerializer(),
                         status.HTTP_403_FORBIDDEN: "Forbidden",
                         status.HTTP_404_NOT_FOUND: "Not Found",
                     })
@api_view(["PUT"])
@permission_classes([IsManagerAuth])
@authentication_classes([AuthBySessionID])
def update_status_admin(request, icebreaker_id):
    """
    Закрытие заявки на проводку кораблей модератором
    """
    print(f"Request data: {request.data}")
    icebreaker = Icebreaker.objects.filter(id=icebreaker_id,
                                           status=Icebreaker.RequestStatus.FORMED).first()
    if icebreaker is None:
        return Response("Icebreaker not found", status=status.HTTP_404_NOT_FOUND)

    serializer = ResolveIcebreakerSerializer(icebreaker,
                                             data=request.data,
                                             partial=True)
    if not serializer.is_valid():
        print(serializer.errors)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    serializer.save()

    icebreaker = Icebreaker.objects.get(id=icebreaker_id)
    icebreaker.date_complete = datetime.now()
    # if icebreaker.status == Icebreaker.RequestStatus.REJECTED:
    #     icebreaker.result = False
    # elif icebreaker.status == Icebreaker.RequestStatus.COMPLETED:
    #     icebreaker.result = random.choice([True, False])
    icebreaker.moderator = request.user

    # # Отправка запроса на асинхронный сервис
    # url = 'http://127.0.0.1:8100/api/async_calc/'
    # data = {
    #     'icebreaker_id': icebreaker_id,
    # }
    # try:
    #     response = requests.post(url, json=data)

    #     # if response.status_code == 200:
    #     #     # Получаем результат от асинхронного сервиса
    #     #     result_data = response.json().get('data', {})
    #     #     icebreaker.result = result_data.get('result', False)
    #     # else:
    #     #     icebreaker.result = False  # В случае ошибки устанавливаем результат в False

    #     icebreaker.save()
    # except Exception as error:
    #     print(f"Error during async request: {error}")
    #     # icebreaker.result = False
    #     icebreaker.save()

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
    """
    Удаление заявки на проводку кораблей
    """
    icebreaker = Icebreaker.objects.filter(id=icebreaker_id,
                                           status=Icebreaker.RequestStatus.DRAFT).first()
    if icebreaker is None:
        return Response("Icebreaker not found", status=status.HTTP_404_NOT_FOUND)

    if not request.user.is_staff and icebreaker.owner != request.user:
        return Response(status=status.HTTP_403_FORBIDDEN)

    icebreaker.status = Icebreaker.RequestStatus.DELETED
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
    """
    Удаление корабәл из заявки на проводку
    """
    icebreaker = Icebreaker.objects.filter(
        id=icebreaker_id).first()
    if icebreaker is None:
        return Response("Icebreaker not found", status=status.HTTP_404_NOT_FOUND)
    if not request.user.is_staff and icebreaker.owner != request.user:
        return Response(status=status.HTTP_403_FORBIDDEN)

    ship_in_icebreaker = ShipIcebreaker.objects.filter(
        icebreaker_id=icebreaker_id, ship_id=ship_id).first()
    if ship_in_icebreaker is None:
        return Response("ShipIcebreaker not found", status=status.HTTP_404_NOT_FOUND)

    deleted_ship_order = ship_in_icebreaker.order
    ship_in_icebreaker.delete()

    # Обновляем порядок у оставшихся кораблей
    ShipIcebreaker.objects.filter(
        icebreaker_id=icebreaker_id,
        order__gt=deleted_ship_order  # Только корабли ниже по порядку
    ).update(order=models.F('order') - 1)

    return Response(status=status.HTTP_200_OK)


# @swagger_auto_schema(method='get',
#                      responses={
#                          status.HTTP_200_OK: ShipIcebreakerSerializer(),
#                          status.HTTP_403_FORBIDDEN: "Forbidden",
#                          status.HTTP_404_NOT_FOUND: "Not Found",
#                      })
# @api_view(["GET"])
# @permission_classes([IsAuth])
# @authentication_classes([AuthBySessionID])
# def get_ship_icebreaker(request, icebreaker_id, ship_id):
#     user = request.user

#     if not Icebreaker.objects.filter(pk=icebreaker_id, owner=user).exists():
#         return Response(status=status.HTTP_404_NOT_FOUND)

#     if not ShipIcebreaker.objects.filter(ship_id=ship_id, icebreaker_id=icebreaker_id).exists():
#         return Response(status=status.HTTP_404_NOT_FOUND)

#     item = ShipIcebreaker.objects.get(
#         ship_id=ship_id, icebreaker_id=icebreaker_id)

#     serializer = ShipIcebreakerSerializer(item)

#     return Response(serializer.data)


@swagger_auto_schema(method='put',
                     request_body=UpdateShipIcebreakerSerializer,
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
    """
    Изменение порядка кораблей в заявке
    """
    # Получение заявки
    icebreaker = Icebreaker.objects.filter(id=icebreaker_id).first()
    if icebreaker is None:
        return Response("Icebreaker not found", status=status.HTTP_404_NOT_FOUND)
    if not request.user.is_staff and icebreaker.owner != request.user:
        return Response(status=status.HTTP_403_FORBIDDEN)

    # Получение записи ShipIcebreaker
    ship_in_icebreaker = ShipIcebreaker.objects.filter(
        icebreaker_id=icebreaker_id, ship_id=ship_id).first()
    if ship_in_icebreaker is None:
        return Response("ShipIcebreaker not found", status=status.HTTP_404_NOT_FOUND)

    # Извлечение направления
    direction = request.data.get("direction")
    if direction not in ["up", "down"]:
        return Response("Invalid direction. Use 'up' or 'down'.", status=status.HTTP_400_BAD_REQUEST)

    # Текущий порядок
    current_order = ship_in_icebreaker.order

    # Определение нового порядка
    if direction == "up":
        adjacent_ship = ShipIcebreaker.objects.filter(
            icebreaker_id=icebreaker_id, order=current_order - 1).first()
    elif direction == "down":
        adjacent_ship = ShipIcebreaker.objects.filter(
            icebreaker_id=icebreaker_id, order=current_order + 1).first()

    if adjacent_ship is None:
        return Response("Cannot move in the specified direction.", status=status.HTTP_400_BAD_REQUEST)

    # Обмен порядков
    ship_in_icebreaker.order, adjacent_ship.order = adjacent_ship.order, ship_in_icebreaker.order

    # Сохранение изменений
    ship_in_icebreaker.save()
    adjacent_ship.save()

    return Response("Order updated successfully", status=status.HTTP_200_OK)


@swagger_auto_schema(method='post',
                     responses={
                         status.HTTP_200_OK: UserLoginSerializer(),
                         status.HTTP_400_BAD_REQUEST: "Bad Request",
                     },
                     manual_parameters=[
                         openapi.Parameter('username',
                                           type=openapi.TYPE_STRING,
                                           description='username',
                                           in_=openapi.IN_FORM,
                                           required=True),
                         openapi.Parameter('password',
                                           type=openapi.TYPE_STRING,
                                           description='password',
                                           in_=openapi.IN_FORM,
                                           required=True)
                     ])
@api_view(['POST'])
@parser_classes((FormParser,))
@permission_classes([AllowAny])
def login(request):
    """
    Вход
    """
    username = request.POST.get('username')
    password = request.POST.get('password')
    user = authenticate(username=username, password=password)
    if user is not None:
        session_id = str(uuid.uuid4())
        session_storage.set(session_id, username)
        serializer = UserLoginSerializer(user)
        response = Response(serializer.data, status=status.HTTP_200_OK)
        response.set_cookie("session_id", session_id, samesite="lax")
        return response
    return Response({'error': 'Invalid Credentials'}, status=status.HTTP_400_BAD_REQUEST)


@swagger_auto_schema(method='post',
                     request_body=UserSerializer,
                     responses={
                         status.HTTP_201_CREATED: "Created",
                         status.HTTP_400_BAD_REQUEST: "Bad Request",
                     })
@api_view(['POST'])
@permission_classes([AllowAny])
def register(request):
    """
    Создание пользователя
    """
    serializer = UserSerializer(data=request.data)
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@swagger_auto_schema(method='post',
                     responses={
                         status.HTTP_204_NO_CONTENT: "No content",
                         status.HTTP_403_FORBIDDEN: "Forbidden",
                     })
@api_view(['POST'])
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
                     request_body=UserUpdateSerializer,
                     responses={
                         status.HTTP_200_OK: UserSerializer(),
                         status.HTTP_400_BAD_REQUEST: "Bad Request",
                         status.HTTP_403_FORBIDDEN: "Forbidden",
                     })
@api_view(['PUT'])
@permission_classes([IsAuth])
@authentication_classes([AuthBySessionID])
def update_user(request):
    """
    Обновление данных пользователя
    """
    serializer = UserSerializer(request.user, data=request.data, partial=True)
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data, status=status.HTTP_200_OK)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@swagger_auto_schema(method='put')
@api_view(['PUT'])
@permission_classes([AllowAny])
def async_result(request):
    """
    Обработка асинхронного результата от Go-сервера
    """
    print(f"Async result data: {request.data}")
    try:
        json_data = request.data
        const_token = 'icebreaker_secret_token'

        if const_token != json_data.get('token'):
            return Response(data={'message': 'Ошибка, токен не соответствует'}, status=status.HTTP_403_FORBIDDEN)

        icebreaker_id = json_data.get('icebreaker_id')
        result = json_data.get('result')

        icebreaker = Icebreaker.objects.filter(id=icebreaker_id).first()
        if icebreaker is None:
            return Response("Icebreaker not found", status=status.HTTP_404_NOT_FOUND)

        icebreaker.result = result
        icebreaker.save()

        return Response(data={'message': 'Результат успешно обновлен'}, status=status.HTTP_200_OK)
    except Exception as e:
        print(f"Error in async_result: {e}")
        return Response(data={'message': 'Ошибка обработки запроса'}, status=status.HTTP_400_BAD_REQUEST)
