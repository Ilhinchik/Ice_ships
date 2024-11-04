from django.db import models
from django.utils import timezone
from django.contrib.auth.models import User


class Ship(models.Model):
    STATUS_CHOICES = (
        (1, 'Действует'),
        (2, 'Удалена'),
    )

    ship_name = models.CharField(max_length=100, verbose_name="Название")
    year = models.IntegerField(verbose_name="Год постройки", null=True, blank=True)
    ice_class = models.CharField(max_length=10, verbose_name="Ледовый класс", blank=True)
    length = models.FloatField(verbose_name="Длина", blank=True, null=True)
    engine = models.CharField(max_length=255, verbose_name="Двигатель", blank=True)
    status = models.IntegerField(choices=STATUS_CHOICES, default=1, verbose_name="Статус")
    image = models.ImageField(verbose_name="Изображение", null=True, blank=True)
    description = models.TextField(verbose_name="Описание", blank=True)

    def __str__(self):
        return self.ship_name

    class Meta:
        verbose_name = "Корабль"
        verbose_name_plural = "Корабли"
        db_table = "ships"


class Icebreaker(models.Model):
    STATUS_CHOICES = (
        (1, 'Введён'),
        (2, 'В работе'),
        (3, 'Завершен'),
        (4, 'Отклонен'),
        (5, 'Удален')
    )

    status = models.IntegerField(choices=STATUS_CHOICES, default=1, verbose_name="Статус")
    date_created = models.DateTimeField(default=timezone.now(), verbose_name="Дата создания")
    date_formation = models.DateTimeField(verbose_name="Дата формирования", blank=True, null=True)
    date_complete = models.DateTimeField(verbose_name="Дата завершения", blank=True, null=True)

    owner = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name="Пользователь", related_name='owner', default=1)
    moderator = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name="Модератор", blank=True, null=True, related_name='moderator')

    date = models.DateField(verbose_name="Дата проводки", blank=True, null=True)
    start_point = models.CharField(max_length=255, verbose_name="Начальная точка проводки", blank=True, null=True)
    finish_point = models.CharField(max_length=255, verbose_name="Конечная точка проводки", blank=True, null=True)

    result = models.BooleanField(default=False, verbose_name="Результат проводки (0/1)")

    def __str__(self):
        return f"Проводка №{self.pk} от {self.date}"

    def get_ships(self):
        return [
            setattr(item.ship, "order", item.order) or item.ship
            for item in ShipIcebreaker.objects.filter(icebreaker=self)
        ]
    
    def get_status(self):
        return dict(self.STATUS_CHOICES).get(self.status)
    
    def update_result(self):
        if self.status == 3:
            ships = self.get_ships()
            self.result = all(bool(ship.ice_class) for ship in ships)
            self.save()

    class Meta:
        verbose_name = "Проводка"
        verbose_name_plural = "Проводки"
        ordering = ('-date_formation',)
        db_table = "icebreakers"


class ShipIcebreaker(models.Model):
    ship = models.ForeignKey(Ship, on_delete=models.DO_NOTHING, blank=True, verbose_name="Корабль")
    icebreaker = models.ForeignKey(Icebreaker, on_delete=models.DO_NOTHING, blank=True, verbose_name="Проводка")
    order = models.IntegerField (verbose_name="Порядок", blank=True, null=True)

    def __str__(self):
        return f"Связь корабль {self.ship.id} - проводка {self.icebreaker.id}"

    class Meta:
        verbose_name = "Связь корабль-проводка"
        verbose_name_plural = "Связи корабль-проводка"
        db_table = "ship_icebreaker"
