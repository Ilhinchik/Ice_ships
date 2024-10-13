from django.contrib.auth.models import User
from django.db import connection
from django.shortcuts import render, redirect
from django.utils import timezone

from .models import Ship, Icebreaker, ShipIcebreaker


def index(request):
    ship_name = request.GET.get("ship_name", "")
    ships = Ship.objects.filter(status=1)

    if ship_name:
        ships = ships.filter(ship_name__icontains=ship_name)

    draft_icebreaker = get_draft_icebreaker()

    context = {
        "ship_name": ship_name,
        "ships": ships
    }

    if draft_icebreaker:
        context["ships_count"] = len(draft_icebreaker.get_ships())
        context["draft_icebreaker"] = draft_icebreaker

    return render(request, "ships_page.html", context)


def add_ship_to_draft_icebreaker(request, ship_id):
    ship = Ship.objects.get(pk=ship_id)

    draft_icebreaker = get_draft_icebreaker()

    if draft_icebreaker is None:
        draft_icebreaker = Icebreaker.objects.create()
        draft_icebreaker.owner = get_current_user()
        draft_icebreaker.date_created = timezone.now()
        draft_icebreaker.save()

    if ShipIcebreaker.objects.filter(icebreaker=draft_icebreaker, ship=ship).exists():
        return redirect("/")

    item = ShipIcebreaker(
        icebreaker=draft_icebreaker,
        ship=ship
    )
    item.save()

    return redirect("/")


def ship(request, ship_id):
    context = {
        "ship": Ship.objects.get(id=ship_id)
    }

    return render(request, "ship_page.html", context)


def delete_icebreaker(request, icebreaker_id):
    if not Icebreaker.objects.filter(pk=icebreaker_id).exists():
        return redirect("/")

    with connection.cursor() as cursor:
        cursor.execute("UPDATE icebreakers SET status=5 WHERE id = %s", [icebreaker_id])

    return redirect("/")


def icebreaker(request, icebreaker_id):
    if not Icebreaker.objects.filter(pk=icebreaker_id).exists():
        return redirect("/")

    context = {
        "icebreaker": Icebreaker.objects.get(id=icebreaker_id),
    }

    return render(request, "icebreaker_page.html", context)


def get_draft_icebreaker():
    return Icebreaker.objects.filter(status=1).first()


def get_current_user():
    return User.objects.filter(is_superuser=False).first()

