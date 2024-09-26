from django.shortcuts import render, redirect
from django.http import Http404
from datetime import date

ships = [
    {'id': 1, 
     'title': 'Танкер TBN0986', 
     'year': 2000, 
     'ice_class': '1D',
     'image': 'http://127.0.0.1:9000/image/1.png', 
     'description':'Танкер дедвейтом 147 080 тонн постройки, Южная Корея. Оборудован скруббером.', 
     'length': 274,
     'engine': 'Главный двигатель MAN-B&W мощностью 20 942 л.с.'},

    {'id': 2,
     'title': 'Крановый сухогруз TBN0973', 
     'year': 2005, 
     'ice_class': '1C',
     'image': 'http://127.0.0.1:9000/image/2.png',
     'description':'Крановый сухогруз дедвейтом 9 000 тонн постройки, Китай. 3 крана Х 20 тонн.', 
     'length': 136.57,
     'engine': 'Главный двигатель Wartsila Х 3000 л.с.'},

    {'id': 3, 
     'title': 'Крановый контейнеровоз TBN0977', 
     'year': 2014, 
     'ice_class': '1D',
     'image': 'http://127.0.0.1:9000/image/3.png',
     'description':'Крановый контейнеровоз дедвейтом 17 300 тонн,  Китай. 2 крана Х 45 тонн. Контейнеровместимость 1 345 TEU.', 
     'length': 161.3,
     'engine': 'Главный двигатель B&W мощностью 12 643 кВт'},

    {'id': 4, 
     'title': 'Танкер TBN0972', 
     'year': 2009, 
     'ice_class': '1C',
     'image': 'http://127.0.0.1:9000/image/4.png',
     'description':'Танкер дедвейтом 3300 тонн, Турция.', 
     'length': 92.85,
     'engine': 'Главный двигатель MAN мощностью 2775 л.с.'},

    {'id': 5, 
     'title': 'Многоцелевой твиндекер TBN0964', 
     'year': 2017, 
     'ice_class': '1D',
     'image': 'http://127.0.0.1:9000/image/5.png',
     'description':'Многоцелевой твиндекер 31 700 мт, Китай. 2 крана Х 250 мт+ 1 кран Х 80 мт.', 
     'length': 166,
     'engine': 'Главный двигатель MAN-B&W Х 8800 л.с.'},
]

draft_icebreaker = {
    'id': 1,
    'start_point': 'Точка А',
    'finish_point': 'Точка Б',
    'date': date.today(),
    'ships': [
        {'id': 1,  
         'order': '1'},  

         {'id': 2,
         'order': '2'}, 

         {'id': 3, 
         'order': '3'},  
    ]
}


def getShipById(ship_id):
    for ship in ships:
        if ship["id"] == ship_id:
            return ship


def SearchShips(ship_title):
    res = []

    for ship in ships:
        if ship_title.lower() in ship["title"].lower():
            res.append(ship)

    return res

def GetDraftIcebreaker():
    return draft_icebreaker

def GetIcebreakerById(req_id):
    return draft_icebreaker

def index(request):
    title = request.GET.get("title", "")
    ships = SearchShips(title)
    draft_icebreaker = GetDraftIcebreaker()

    context = {
        "ships": ships,
        "title": title,
        "draft_icebreaker_count": len(draft_icebreaker['ships']) ,
        "draft_icebreaker": draft_icebreaker 
    }

    return render(request, "home_page.html", context)

def ship(request, ship_id):
    context = {
        "id": ship_id,
        "ship": getShipById(ship_id),
    }

    return render(request, "ship_detail.html", context)


def icebreaker(request, req_id):
    icebreaker = GetIcebreakerById(req_id)
    ships = [
        {**getShipById(ship["id"]), "order": ship["order"]} for ship in icebreaker["ships"]
    ]
    context = {
        'icebreaker': icebreaker,
        "draft_icebreaker": draft_icebreaker,
        "ships": ships
    }
    return render(request, "icebreaker_page.html", context)
