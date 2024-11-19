import random
from django.core.management.base import BaseCommand
from bmstu_lab.models import Ship, Icebreaker, ShipIcebreaker
from django.contrib.auth.models import User
from datetime import date


def add_users(ratio):
    # Создаем суперпользователя
    User.objects.create_superuser("ilha", "ilha@root.com", "ilha")

    users = []
    for i in range(ratio):
        user = User(
            username=f"user{i}",
            email=f"user{i}@user.com"
        )
        user.set_password(f"user{i}")  # Устанавливаем пароль, например "password1", "password2"...
        users.append(user)

    User.objects.bulk_create(users, ignore_conflicts=True)

    print("Пользователи созданы")


def add_ships(ratio):
    ships = [
        Ship(
            ship_name=f"Танкер TBN0{i}",
            year=random.randint(1990, 2024),
            ice_class=random.choice(['1D', '1C', '1A']),
            length=random.uniform(50, 300),
            engine="Главный двигатель MAN-B&W мощностью 20000 л.с.",
            status=random.choice([1, 2]),
            image=f"http://127.0.0.1:9000/image/{i}.png",
            description=f"Описание корабля {i}",
        )
        for i in range(1, ratio + 1)
    ]
    Ship.objects.bulk_create(ships)
    print("Корабли созданы")


def add_icebreakers(ratio, users):
    status=random.choice([1, 2, 3, 4, 5])
    icebreakers = [
        Icebreaker(
            status=status,
            date_created=date.today(),
            date_formation=date.today() if status == 2 or status == 3 else None,
            date_complete=date.today()  if status == 3 else None,
            owner=random.choice(users),
            date=date.today(),
            start_point="Точка А",
            finish_point="Точка Б",
            result=random.choice([True, False]) if status == 3 else None,
        )
        for _ in range(ratio)
    ]
    Icebreaker.objects.bulk_create(icebreakers)
    print("Проводки созданы")
    return icebreakers


def add_ship_icebreakers(ratio, ships, icebreakers):
    ship_icebreakers = []
    
    for icebreaker in icebreakers:
        # Получаем все корабли, которые будут связаны с этой проводкой
        related_ships = random.sample(ships, random.randint(1, 5))  # Для примера выбираем случайное количество кораблей
        
        # Сортируем корабли, чтобы порядок был от 1 до N
        related_ships.sort(key=lambda x: x.id)  # Сортируем по id или другому критерию, если нужно
        
        # Присваиваем порядковый номер (order) каждому кораблю в рамках этой проводки
        for index, ship in enumerate(related_ships, start=1):
            ship_icebreakers.append(
                ShipIcebreaker(
                    ship=ship,
                    icebreaker=icebreaker,
                    order=index  # Присваиваем порядковый номер
                )
            )

    ShipIcebreaker.objects.bulk_create(ship_icebreakers)
    print("Связи кораблей и проводок созданы")

class Command(BaseCommand):
    help = 'Заполнение базы данных тестовыми данными'

    def add_arguments(self, parser):
        parser.add_argument('ratio', type=int, help='Количество сущностей для генерации')

    def handle(self, *args, **options):
        ratio = options['ratio']

        add_users(ratio)
        users = list(User.objects.all())

        add_ships(ratio)
        ships = list(Ship.objects.all())

        icebreakers = add_icebreakers(ratio, users)
        add_ship_icebreakers(ratio, ships, icebreakers)

        self.stdout.write(self.style.SUCCESS('База данных успешно заполнена'))
