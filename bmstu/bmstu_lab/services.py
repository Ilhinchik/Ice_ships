from bmstu_lab.serializers import *
import random

from django.db import IntegrityError


def get_or_create_user_cart(user_id: int) -> int:
    """
    Если у пользователя есть заявка в статусе DRAFT (корзина), возвращает её Id.
    Если нет - создает и возвращает id созданной заявки
    """
    old_req = Icebreaker.objects.filter(owner_id=user_id,
                                        status=Icebreaker.RequestStatus.DRAFT).first()
    if old_req is not None:
        return old_req.id

    new_req = Icebreaker(owner_id=user_id,
                         status=Icebreaker.RequestStatus.DRAFT)
    new_req.save()
    return new_req.id


def result_icebreaker():
    """
    Расчет результата проводки
    """
    return random.choice([True, False])


# def is_valid_versions(icebreaker_id):
#     """
#     Проверка: у всего ПО из заявки должна быть указана версия
#     """
#     software_in_request = ShipIcebreaker.objects.filter(icebreaker_id=icebreaker_id)
#     for software in software_in_request:
#         if software.version is None or software.version == "":
#             return False
#     return True


def add_item_to_request(icebreaker_id: int, ship_id: int):
    """
    Добавление услуги в заявку
    """
    if ShipIcebreaker.objects.filter(icebreaker_id=icebreaker_id, ship_id=ship_id).exists():
        raise IntegrityError("Ship is already in the icebreaker request.")

    max_order = ShipIcebreaker.objects.filter(
        icebreaker_id=icebreaker_id).aggregate(models.Max('order'))['order__max']
    next_order = (max_order or 0) + 1  # Если max_order = None, начать с 1

    sir = ShipIcebreaker(icebreaker_id=icebreaker_id,
                         ship_id=ship_id, order=next_order)
    sir.save()
