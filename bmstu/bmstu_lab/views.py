from django.shortcuts import render, redirect
from django.http import Http404
from datetime import date

ships = [
    {'id': 1, 
     'title': 'Танкер TBN0986', 
     'year': 2000, 
     'image': 'http://127.0.0.1:9000/image/1.png', 
     'description':'Танкер дедвейтом 147 080 тонн постройки, Южная Корея. Ледовый класс 1D. Оборудован скруббером.', 
     'length': 274,
     'engine': 'Главный двигатель MAN-B&W мощностью 20 942 л.с.'},

    {'id': 2,
     'title': 'Крановый сухогруз TBN0973', 
     'year': 2005, 
     'image': 'http://127.0.0.1:9000/image/2.png',
     'description':'Крановый сухогруз дедвейтом 9 000 тонн постройки, Китай. Ice class 1C. 3 крана Х 20 тонн.', 
     'length': 136.57,
     'engine': 'Главный двигатель Wartsila Х 3000 л.с.'},

    {'id': 3, 
     'title': 'Крановый контейнеровоз TBN0977', 
     'year': 2014, 
     'image': 'http://127.0.0.1:9000/image/3.png',
     'description':'Крановый контейнеровоз дедвейтом 17 300 тонн,  Китай. 2 крана Х 45 тонн. Контейнеровместимость 1 345 TEU. Ледовый класс  1D.', 
     'length': 161.3,
     'engine': 'Главный двигатель B&W мощностью 12 643 кВт'},

    {'id': 4, 
     'title': 'Танкер TBN0972', 
     'year': 2009, 
     'image': 'http://127.0.0.1:9000/image/4.png',
     'description':'Танкер дедвейтом 3300 тонн, Турция. Ледовый класс 1С.', 
     'length': 92.85,
     'engine': 'Главный двигатель MAN мощностью 2775 л.с.'},

    {'id': 5, 
     'title': 'Многоцелевой твиндекер TBN0964', 
     'year': 2017, 
     'image': 'http://127.0.0.1:9000/image/5.png',
     'description':'Многоцелевой твиндекер 31 700 мт, Китай. Ice class 1D. 2 крана Х 250 мт+ 1 кран Х 80 мт.', 
     'length': 166,
     'engine': 'Главный двигатель MAN-B&W Х 8800 л.с.'},
]

draft_request = {
    'id': 123,
    'status': 'Черновик',
    'date_created': '24.09.2024',
    'ships': [
        {'id': 1, 
         'title': 'Танкер TBN0986', 
         'year': 2000, 
         'image': 'http://127.0.0.1:9000/image/1.png', 
         'description':'Танкер дедвейтом 147 080 тонн постройки, Южная Корея. Ледовый класс 1D. Оборудован скруббером.', 
         'length': 274,
         'engine': 'Главный двигатель MAN-B&W мощностью 20 942 л.с.',
         'value': 'Классный'},  # Добавляем поле 'value'

         {'id': 2,
         'title': 'Крановый сухогруз TBN0973', 
         'year': 2005, 
         'image': 'http://127.0.0.1:9000/image/2.png',
         'description':'Крановый сухогруз дедвейтом 9 000 тонн постройки, Китай. Ice class 1C. 3 крана Х 20 тонн.', 
         'length': 136.57,
         'engine': 'Главный двигатель Wartsila Х 3000 л.с.',
         'value': 'Хороший'},  # Добавляем поле 'value'

         {'id': 3, 
         'title': 'Крановый контейнеровоз TBN0977', 
         'year': 2014, 
         'image': 'http://127.0.0.1:9000/image/3.png',
         'description':'Крановый контейнеровоз дедвейтом 17 300 тонн,  Китай. 2 крана Х 45 тонн. Контейнеровместимость 1 345 TEU. Ледовый класс  1D.', 
         'length': 161.3,
         'engine': 'Главный двигатель B&W мощностью 12 643 кВт',
         'value': 'Замечательный'},  # Добавляем поле 'value'
    ]
}

def GetShips(request):
    draft_request_count = len(draft_request['ships'])
    return render(request, 'base.html', {'data': {'ships': ships}, 'draft_request': draft_request, 'draft_request_count': draft_request_count})

def SearchShips(request):
    query = request.GET.get('query', '') 
    filtered_ships = [ship for ship in ships if query.lower() in ship['title'].lower()]
    return render(request, 'base.html', {'data': {'ships': filtered_ships}})

def GetShipDetail(request, id):
    ship = next((ship for ship in ships if ship['id'] == id), None)
    if ship is None:
        raise Http404("Корабль не найден")
    return render(request, 'ship_detail.html', {'ship': ship})

def GetDraftRequest():
    return draft_request

def GetRequestById(req_id):
    return draft_request

def request(request, req_id):
    if request.method == 'POST':
        start_point = request.POST.get('start_point')
        end_point = request.POST.get('end_point')
        
        # Обновляем комментарии для каждого корабля
        for ship in draft_request['ships']:
            comment_key = f'comment-{ship["id"]}'
            ship['value'] = request.POST.get(comment_key, '')
        
        # Здесь можно добавить логику для сохранения заявки
        return redirect('home')  # Перенаправляем на главную страницу после отправки заявки

    context = {
        'request': GetRequestById(req_id),
    }
    return render(request, "create_request.html", context)