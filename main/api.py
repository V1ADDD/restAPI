import json
from datetime import datetime
from itertools import chain
from .api_authenticate import Auth, NotAuth
import re
from django.db.models import ProtectedError
from django.http import JsonResponse
from rest_framework import viewsets, permissions
from rest_framework.decorators import action, api_view, authentication_classes

from .models import Account, Location, AnimalType, AnimalLocation, Animal
from .serializers import AccountSerializer, LocationSerializer, AnimalTypeSerializer, AnimalLocationSerializer, \
    AnimalSerializer


def check_error_400_404(*args):
    result = []
    for arg in args:
        if arg is None:
            return JsonResponse("ERROR 400", safe=False, status=400)
        try:
            arg_ = int(arg)
            if arg_ <= 0:
                return JsonResponse("ERROR 400", safe=False, status=400)
            result.append(arg_)
        except:
            return JsonResponse("ERROR 400", safe=False, status=404)
    return result


def find_next_prev(animal, id, next=True):
    if next:
        i = 1
        while True:
            try:
                return animal.visitedLocations.get(id=id + i).locationPointId.id
            except:
                i += 1
    else:
        i = 1
        while True:
            try:
                return animal.visitedLocations.get(id=id - i).locationPointId.id
            except:
                i += 1


def to_dict(instance):
    opts = instance._meta
    data = {}
    for f in chain(opts.concrete_fields, opts.private_fields):
        if f.name != 'password':
            data[f.name] = f.value_from_object(instance)
    for f in opts.many_to_many:
        data[f.name] = [i.id for i in f.value_from_object(instance)]
    return data


@api_view(['POST'])
@authentication_classes([NotAuth])
def RegistrationView(request):
    data = json.loads(request.body)
    try:
        firstName = data['firstName']
        lastName = data['lastName']
        email = data['email']
        password = data['password']
    except KeyError:

        # check if wasn't in a request
        return JsonResponse("ERROR 400", safe=False, status=400)
    try:

        # email validation
        regex = re.compile(r'([A-Za-z0-9]+[._-])*[A-Za-z0-9]+@[A-Za-z0-9-]+(\.[A-Z|a-z]{2,})+')
        if not re.fullmatch(regex, email):
            return JsonResponse("ERROR 400", safe=False, status=400)

        # validation
        if len(firstName.rstrip('\n\t ')) == 0 or len(lastName.rstrip('\n\t ')) == 0 or len(password.rstrip('\n\t ')) == 0:
            return JsonResponse("ERROR 400", safe=False, status=400)
    except TypeError:

        # none
        return JsonResponse("ERROR 400", safe=False, status=400)
    except AttributeError:

        # none
        return JsonResponse("ERROR 400", safe=False, status=400)

    # email already exists
    if {'email': email} in Account.objects.values('email'):
        return JsonResponse("ERROR 409", safe=False, status=409)

    # Регистрация нового аккаунта
    newAccount = Account(firstName=firstName, lastName=lastName, email=email, password=password)
    newAccount.save()
    serializer = AccountSerializer(newAccount)
    return JsonResponse(serializer.data, safe=False, status=201)


class AccountViewSet(viewsets.ModelViewSet):
    authentication_classes = (Auth,)
    queryset = Account.objects.all()
    permission_classes = [
        permissions.AllowAny
    ]
    serializer_class = AccountSerializer

    def retrieve(self, request, pk):
        # Поиск аккаунтов пользователей по параметрам
        if pk == "search":
            firstname = self.request.query_params.get('firstName')
            lastname = self.request.query_params.get('lastName')
            email = self.request.query_params.get('email')
            # from size validation and default
            if self.request.query_params.get('from') is None:
                from_ = 0
            else:
                try:
                    from_ = int(self.request.query_params.get('from'))
                except:
                    return JsonResponse("ERROR 400", safe=False, status=400)
            if self.request.query_params.get('size') is None:
                size = 10
            else:
                try:
                    size = int(self.request.query_params.get('size'))
                except:
                    return JsonResponse("ERROR 400", safe=False, status=400)
            if from_ < 0 or size <= 0:
                return JsonResponse("ERROR 400", safe=False, status=400)

            query = Account.objects.all()
            result = []
            for acc in query:
                if firstname is None or firstname.lower() in acc.firstName.lower():
                    if lastname is None or lastname.lower() in acc.lastName.lower():
                        if email is None or email.lower() in acc.email.lower():
                            result.append(to_dict(acc))
            return JsonResponse(result[from_:size], safe=False)

        # validating pk
        data_check = check_error_400_404(pk)
        if type(data_check) != list:
            return data_check

        # Получение информации об аккаунте пользователя
        return super(AccountViewSet, self).retrieve(request, pk=None)

    def update(self, request, pk):
        # validating pk
        data_check = check_error_400_404(pk)
        if type(data_check) != list:
            return data_check

        # not your account
        if request.user.id != int(pk):
            return JsonResponse("ERROR 403", safe=False, status=403)

        query = Account.objects.all()

        # Аккаунт не найден
        if {'id': int(pk)} not in query.values('id'):
            return JsonResponse("ERROR 403", safe=False, status=403)

        # validation
        data = json.loads(request.body)
        try:
            firstName = data['firstName']
            lastName = data['lastName']
            email = data['email']
            password = data['password']
        except KeyError:

            # check if wasn't in a request
            return JsonResponse("ERROR 400", safe=False, status=400)
        try:

            # email validation
            regex = re.compile(r'([A-Za-z0-9]+[._-])*[A-Za-z0-9]+@[A-Za-z0-9-]+(\.[A-Z|a-z]{2,})+')
            if not re.fullmatch(regex, email):
                return JsonResponse("ERROR 400", safe=False, status=400)

            # validation
            if len(firstName.rstrip('\n\t ')) == 0 or len(lastName.rstrip('\n\t ')) == 0 or len(
                    password.rstrip('\n\t ')) == 0:
                return JsonResponse("ERROR 400", safe=False, status=400)
        except TypeError:

            # none
            return JsonResponse("ERROR 400", safe=False, status=400)
        except AttributeError:

            # none
            return JsonResponse("ERROR 400", safe=False, status=400)

        # Аккаунт с таким email уже существует
        for acc in query:
            if acc.email == Account.objects.get(id=pk).email and acc.id != pk:
                return JsonResponse("ERROR 409", safe=False, status=409)



        # Обновление данных аккаунта пользователя
        return super(AccountViewSet, self).update(request, pk=None)

    def destroy(self, request, pk):
        # validating pk
        data_check = check_error_400_404(pk)
        if type(data_check) != list:
            return data_check

        # not your account
        if request.user.id != int(pk):
            return JsonResponse("ERROR 403", safe=False, status=403)

        # Аккаунт с таким accountId не найден
        if {'id': int(pk)} not in Account.objects.values('id'):
            return JsonResponse("ERROR 403", safe=False, status=403)

        # Удаление аккаунта пользователя
        try:
            Account.objects.get(id=pk).delete()
            return JsonResponse({}, status=200)
        except ProtectedError:
            # Аккаунт связан с животным
            return JsonResponse("ERROR 400", safe=False, status=400)


class LocationViewSet(viewsets.ModelViewSet):
    authentication_classes = (Auth,)
    queryset = Location.objects.all()
    permission_classes = [
        permissions.AllowAny
    ]
    serializer_class = LocationSerializer

    def retrieve(self, request, pk):
        # validating pk
        data_check = check_error_400_404(pk)
        if type(data_check) != list:
            return data_check

        # Получение информации о точке локации животных
        return super(LocationViewSet, self).retrieve(request, pk=None)

    def create(self, request):
        # validating latitude and longitude
        try:
            latitude = float(request.data.get('latitude'))
            longitude = float(request.data.get('longitude'))
        except:
            return JsonResponse("ERROR 400", safe=False, status=400)
        if latitude < -90 or latitude > 90 or longitude < -180 or longitude > 180:
            return JsonResponse("ERROR 400", safe=False, status=400)

        # Точка локации с такими latitude и longitude уже существует
        for loc in Location.objects.all():
            if loc.latitude == latitude and loc.longitude == longitude:
                return JsonResponse("ERROR 409", safe=False, status=409)

        # Добавление точки локации животных
        return super(LocationViewSet, self).create(request)

    def update(self, request, pk=None):
        # validating latitude and longitude
        try:
            latitude = float(request.data.get('latitude'))
            longitude = float(request.data.get('longitude'))
        except:
            return JsonResponse("ERROR 400", safe=False, status=400)
        if latitude < -90 or latitude > 90 or longitude < -180 or longitude > 180:
            return JsonResponse("ERROR 400", safe=False, status=400)

        # validating pk
        data_check = check_error_400_404(pk)
        if type(data_check) != list:
            return data_check

        # Точка локации с такими latitude и longitude уже существует
        for loc in Location.objects.all():
            if loc.latitude == latitude and loc.longitude == longitude:
                return JsonResponse("ERROR 409", safe=False, status=409)

        # Изменение точки локации животных
        return super(LocationViewSet, self).update(request, pk=None)

    def destroy(self, request, pk):
        # validating pk
        data_check = check_error_400_404(pk)
        if type(data_check) == list:
            pk = data_check[0]
        else:
            return data_check

        # Точка локации с таким pointId не найдена
        if {'id': pk} not in Location.objects.values('id'):
            return JsonResponse("ERROR 404", safe=False, status=404)

        # Удаление точки локации животных
        try:
            Location.objects.get(id=pk).delete()
            return JsonResponse({}, status=200)
        except ProtectedError:
            # Точка локации связана с животным
            return JsonResponse("ERROR 400", safe=False, status=400)


class AnimalTypeViewSet(viewsets.ModelViewSet):
    authentication_classes = (Auth,)
    queryset = AnimalType.objects.all()
    permission_classes = [
        permissions.AllowAny
    ]
    serializer_class = AnimalTypeSerializer

    def create(self, request):
        # Тип животного с таким type уже существует
        if {'type': request.data.get('type')} in AnimalType.objects.values('type'):
            return JsonResponse("ERROR 409", safe=False, status=409)

        # Добавление типа животного
        return super(AnimalTypeViewSet, self).create(request)

    def retrieve(self, request, pk=None):
        # validating pk
        data_check = check_error_400_404(pk)
        if type(data_check) != list:
            return data_check

        # Получение информации о типе животного
        return super(AnimalTypeViewSet, self).retrieve(request, pk=None)

    def update(self, request, pk=None):
        # validating pk
        data_check = check_error_400_404(pk)
        if type(data_check) != list:
            return data_check

        # Тип животного с таким type уже существует
        if {'type': request.data.get('type')} in AnimalType.objects.values('type'):
            return JsonResponse("ERROR 409", safe=False, status=409)

        # Изменение типа животного
        return super(AnimalTypeViewSet, self).update(request, pk=None)

    def destroy(self, request, pk=None):
        # validating pk
        data_check = check_error_400_404(pk)
        if type(data_check) == list:
            pk = data_check[0]
        else:
            return data_check

        # Тип животного с таким typeId не найден
        if {'id': pk} not in AnimalType.objects.values('id'):
            return JsonResponse("ERROR 404", safe=False, status=404)

        # Есть животные с типом с typeId
        for animal in Animal.objects.all():
            if {'id': pk} in animal.animalTypes.values('id'):
                return JsonResponse("ERROR 400", safe=False, status=400)

        # Удаление типа животного
        AnimalType.objects.get(id=pk).delete()
        return JsonResponse({}, status=200)


class AnimalViewSet(viewsets.ModelViewSet):
    authentication_classes = (Auth,)
    queryset = Animal.objects.all()
    permission_classes = [
        permissions.AllowAny
    ]
    serializer_class = AnimalSerializer

    def retrieve(self, request, pk=None):
        # Поиск животных по параметрам
        if pk == "search":
            # validating dateTimes
            if self.request.query_params.get('startDateTime') is None:
                startdatetime = None
            else:
                try:
                    startdatetime = datetime.fromisoformat(self.request.query_params.get('startDateTime'))
                except:
                    return JsonResponse("ERROR 400", safe=False, status=400)
            if self.request.query_params.get('endDateTime') is None:
                enddatetime = None
            else:
                try:
                    enddatetime = datetime.fromisoformat(self.request.query_params.get('endDateTime'))
                except:
                    return JsonResponse("ERROR 400", safe=False, status=400)

            # chipperId, chippingLocationId validation
            data_check = check_error_400_404(self.request.query_params.get('chipperId'),
                                             self.request.query_params.get('chippingLocationId'))
            if type(data_check) == list:
                chipperid, chippinglocationid = data_check
            else:
                chipperid, chippinglocationid = None, None

            # lifestatus, gender validation
            lifestatus = self.request.query_params.get('lifeStatus')
            gender = self.request.query_params.get('gender')
            if lifestatus != 'ALIVE' and lifestatus != 'DEAD' and lifestatus is not None:
                return JsonResponse("ERROR 400", safe=False, status=400)
            if gender != 'MALE' and gender != 'FEMALE' and gender != 'OTHER' and gender is not None:
                return JsonResponse("ERROR 400", safe=False, status=400)

            # from, size validation and default
            if self.request.query_params.get('from') is None:
                from_ = 0
            else:
                try:
                    from_ = int(self.request.query_params.get('from'))
                except:
                    return JsonResponse("ERROR 400", safe=False, status=400)
            if self.request.query_params.get('size') is None:
                size = 10
            else:
                try:
                    size = int(self.request.query_params.get('size'))
                except:
                    return JsonResponse("ERROR 400", safe=False, status=400)
            if from_ < 0 or size <= 0:
                return JsonResponse("ERROR 400", safe=False, status=400)

            query = Animal.objects.all()
            result = []
            for animal in query:
                if startdatetime is None or startdatetime.timestamp() <= animal.chippingDateTime.timestamp():
                    if enddatetime is None or enddatetime.timestamp() >= animal.chippingDateTime.timestamp():
                        if chipperid is None or chipperid == animal.chipperId.id:
                            if chippinglocationid is None or chippinglocationid == animal.chippingLocationId.id:
                                if gender is None or gender == animal.gender:
                                    if lifestatus is None or lifestatus == animal.lifeStatus:
                                        result.append(to_dict(animal))
            return JsonResponse(result[from_:size], safe=False)

        # validating pk
        data_check = check_error_400_404(pk)
        if type(data_check) != list:
            return data_check

        # Получение информации о животном
        return super(AnimalViewSet, self).retrieve(request, pk=None)

    def create(self, request):
        # chipperId, chippingLocationId validation
        data_check = check_error_400_404(request.data.get('chipperId'), request.data.get('chippingLocationId'))
        if type(data_check) == list:
            chipperid, chippinglocationid = data_check
        else:
            return data_check
        if {'id': chipperid} not in Account.objects.values('id') or {
            'id': chippinglocationid} not in Location.objects.values('id'):
            return JsonResponse("ERROR 404", safe=False, status=404)

        types = request.data.get('animalTypes')

        # weight, length, height validation
        if request.data.get('weight') is None or request.data.get('length') is None or request.data.get(
                'height') is None:
            return JsonResponse("ERROR 400", safe=False, status=400)
        if request.data.get('weight') <= 0 or request.data.get('length') <= 0 or request.data.get('height') <= 0:
            return JsonResponse("ERROR 400", safe=False, status=400)

        # types validation
        if types is not None:
            if types != list(set(types)):
                return JsonResponse("ERROR 409", safe=False, status=409)
            for animaltype in types:
                if animaltype is not None:
                    if animaltype > 0 and {'id': animaltype} not in AnimalType.objects.values('id'):
                        return JsonResponse("ERROR 404", safe=False, status=404)

        #  Добавление нового животного
        return super(AnimalViewSet, self).create(request)

    def update(self, request, pk):
        # pk, chipperId, chippingLocationId validation
        data_check = check_error_400_404(pk, request.data.get('chipperId'), request.data.get('chippingLocationId'))
        if type(data_check) == list:
            pk, chipperid, chippinglocationid = data_check
        else:
            return data_check
        if {"id": pk} not in Animal.objects.values('id'):
            return JsonResponse("ERROR 404", safe=False, status=404)

        # weight, length, height validation
        if request.data.get('weight') is None or request.data.get('length') is None or request.data.get(
                'height') is None:
            return JsonResponse("ERROR 400", safe=False, status=400)
        if request.data.get('weight') <= 0 or request.data.get('length') <= 0 or request.data.get('height') <= 0:
            return JsonResponse("ERROR 400", safe=False, status=400)

        # lifeStatus, location, chipper validations
        if request.data.get('lifeStatus'):
            if request.data.get('lifeStatus') == 'ALIVE' and Animal.objects.get(id=pk).lifeStatus == 'DEAD':
                return JsonResponse("ERROR 400", safe=False, status=400)
            if chippinglocationid == Animal.objects.get(id=pk).visitedLocations.values()[0]['locationPointId_id']:
                return JsonResponse("ERROR 400", safe=False, status=400)
            if {'id': chipperid} not in Account.objects.values('id'):
                return JsonResponse("ERROR 404", safe=False, status=404)
            if {'id': chippinglocationid} not in Location.objects.values('id'):
                return JsonResponse("ERROR 404", safe=False, status=404)

        # Обновление информации о животном
        return super(AnimalViewSet, self).update(request, pk)

    def destroy(self, request, pk):
        # pk validation
        data_check = check_error_400_404(pk)
        if type(data_check) == list:
            pk = data_check[0]
        else:
            return data_check
        if {"id": pk} not in Animal.objects.values('id'):
            return JsonResponse("ERROR 404", safe=False, status=404)

        # Животное покинуло локацию чипирования, при этом есть другие посещенные точки
        if len(Animal.objects.get(id=pk).visitedLocations.values()) > 0:
            return JsonResponse("ERROR 400", safe=False, status=400)

        # Удаление животного
        Animal.objects.get(id=pk).delete()
        return JsonResponse({}, status=200)

    @action(methods=['delete', 'post'], detail=True, url_path='types/(?P<typeId>[^/.]+)')
    def type_post_delete(self, request, pk, typeId):
        # pk, typeId validation
        data_check = check_error_400_404(pk, typeId)
        if type(data_check) == list:
            pk, typeId = data_check
        else:
            return data_check
        if {"id": pk} not in Animal.objects.values('id') or {
            "id": typeId} not in AnimalType.objects.values(
            'id'):
            return JsonResponse("ERROR 404", safe=False, status=404)

        if request.method == 'DELETE':
            # У животного с animalId нет типа с typeId
            if {'id': int(typeId)} not in Animal.objects.get(id=pk).animalTypes.values('id'):
                return JsonResponse("ERROR 404", safe=False, status=404)

            # У животного только один тип и это тип с typeId
            if len(Animal.objects.get(id=pk).animalTypes.values('id')) == 1 and \
                    Animal.objects.get(id=pk).animalTypes.values('id')[0] == {'id': typeId}:
                return JsonResponse("ERROR 400", safe=False, status=400)

            # Удаление типа животного у животного
            removeAnimalType = Animal.objects.get(id=pk).animalTypes.get(id=typeId)
            Animal.objects.get(id=pk).animalTypes.remove(removeAnimalType)
            queryset = super(AnimalViewSet, self).get_queryset().get(id=pk)
            serializer = AnimalSerializer(queryset)
            return JsonResponse(serializer.data, safe=False, status=200)

        elif request.method == 'POST':
            # Тип животного с typeId уже есть у животного с animalId
            if {'id': typeId} in Animal.objects.get(id=pk).animalTypes.values('id'):
                return JsonResponse("ERROR 409", safe=False, status=409)

            # Добавление типа животного к животному
            Animal.objects.get(id=pk).animalTypes.add(AnimalType.objects.get(id=typeId))
            queryset = super(AnimalViewSet, self).get_queryset().get(id=pk)
            serializer = AnimalSerializer(queryset)
            return JsonResponse(serializer.data, safe=False, status=201)

    @action(methods=['put'], detail=True, url_path='types')
    def update_types(self, request, pk):
        # pk, oldTypeId, newTypeId validation
        data_check = check_error_400_404(pk, request.data.get('oldTypeId'), request.data.get('newTypeId'))
        if type(data_check) == list:
            pk, oldtypeid, newtypeid = data_check
        else:
            return data_check
        if {'id': pk} not in Animal.objects.values('id'):
            return JsonResponse("ERROR 404", safe=False, status=404)
        if {'id': oldtypeid} not in AnimalType.objects.values('id') or {'id': newtypeid} not in AnimalType. \
                objects.values('id'):
            return JsonResponse("ERROR 404", safe=False, status=404)
        if {'id': oldtypeid} not in Animal.objects.get(id=pk).animalTypes.values('id'):
            return JsonResponse("ERROR 404", safe=False, status=404)
        if {'id': newtypeid} in Animal.objects.get(id=pk).animalTypes.values('id'):
            return JsonResponse("ERROR 409", safe=False, status=409)

        # Изменение типа животного у животного
        removeAnimalType = Animal.objects.get(id=pk).animalTypes.get(id=oldtypeid)
        Animal.objects.get(id=pk).animalTypes.remove(removeAnimalType)
        Animal.objects.get(id=pk).animalTypes.add(AnimalType.objects.get(id=newtypeid))
        queryset = super(AnimalViewSet, self).get_queryset().get(id=pk)
        serializer = AnimalSerializer(queryset)
        return JsonResponse(serializer.data, safe=False, status=200)

    @action(methods=['get', 'put'], detail=True, url_path='locations')
    def get_edit_locations(self, request, pk):

        # animalId > 0 and not None
        data_check = check_error_400_404(pk)
        if type(data_check) == list:
            animalId = data_check[0]
        else:
            return data_check
        if {'id': animalId} not in Animal.objects.values('id'):
            return JsonResponse("ERROR 404", safe=False, status=404)

        if request.method == 'GET':

            # startDateTime and endDateTime validation
            if self.request.query_params.get('startDateTime') is None:
                startdatetime = None
            else:
                try:
                    startdatetime = datetime.fromisoformat(self.request.query_params.get('startDateTime'))
                except:
                    return JsonResponse("ERROR 400", safe=False, status=400)
            if self.request.query_params.get('endDateTime') is None:
                enddatetime = None
            else:
                try:
                    enddatetime = datetime.fromisoformat(self.request.query_params.get('endDateTime'))
                except:
                    return JsonResponse("ERROR 400", safe=False, status=400)

            # from and size validation and setting to default
            if self.request.query_params.get('from') is None:
                from_ = 0
            else:
                try:
                    from_ = int(self.request.query_params.get('from'))
                except:
                    return JsonResponse("ERROR 400", safe=False, status=400)
            if self.request.query_params.get('size') is None:
                size = 10
            else:
                try:
                    size = int(self.request.query_params.get('size'))
                except:
                    return JsonResponse("ERROR 400", safe=False, status=400)
            if from_ < 0 or size <= 0:
                return JsonResponse("ERROR 400", safe=False, status=400)

            query = Animal.objects.get(id=animalId).visitedLocations.all()

            # Просмотр точек локации, посещенных животным
            result = []
            for location in query:
                if startdatetime is None or startdatetime.timestamp() <= location.dateTimeOfVisitLocationPoint.timestamp():
                    if enddatetime is None or enddatetime.timestamp() >= location.dateTimeOfVisitLocationPoint.timestamp():
                        result.append(to_dict(location))
            return JsonResponse(result[from_:size], safe=False)

        elif request.method == 'PUT':

            # visitedLocationPointId, locationPointId > 0 and not None
            data_check = check_error_400_404(request.data.get('visitedLocationPointId'),
                                             request.data.get('locationPointId'))
            if type(data_check) == list:
                visitedLocationPointId, locationPointId = data_check
            else:
                return data_check

            # Объект с информацией о посещенной точке локации с visitedLocationPointId не найден.
            if {'id': visitedLocationPointId} not in AnimalLocation.objects.values('id'):
                return JsonResponse("ERROR 404", safe=False, status=404)

            # Точка локации с locationPointId не найден
            if {'id': locationPointId} not in Location.objects.values('id'):
                return JsonResponse("ERROR 404", safe=False, status=404)

            animal = Animal.objects.get(id=animalId)

            # У животного нет объекта с информацией о посещенной точке локации с visitedLocationPointId
            if {'id': visitedLocationPointId} not in animal.visitedLocations.values('id'):
                return JsonResponse("ERROR 404", safe=False, status=404)

            # Обновление первой посещенной точки на точку чипирования
            if {'id': visitedLocationPointId} == \
                    animal.visitedLocations.values('id').first() \
                    and animal.chippingLocationId.id == locationPointId:
                return JsonResponse("ERROR 400", safe=False, status=400)

            # Обновление точки на такую же точку
            if AnimalLocation.objects.get(id=visitedLocationPointId).locationPointId.id == locationPointId:
                return JsonResponse("ERROR 400", safe=False, status=400)

            # Обновление точки локации на точку, совпадающую со следующей и/или с предыдущей точками
            if {'id': visitedLocationPointId} == animal.visitedLocations.values('id').first() and \
                    {'id': visitedLocationPointId} == animal.visitedLocations.values('id').last():
                pass
            elif {'id': visitedLocationPointId} == animal.visitedLocations.values('id').first():
                if find_next_prev(animal, visitedLocationPointId) == locationPointId:
                    return JsonResponse("ERROR 400", safe=False, status=400)
            elif {'id': visitedLocationPointId} == animal.visitedLocations.values('id').last():
                if find_next_prev(animal, visitedLocationPointId, next=False) == locationPointId:
                    return JsonResponse("ERROR 400", safe=False, status=400)
            elif find_next_prev(animal, visitedLocationPointId, next=False) == locationPointId or \
                    find_next_prev(animal, visitedLocationPointId) == locationPointId:
                return JsonResponse("ERROR 400", safe=False, status=400)

            # Изменение точки локации, посещенной животным
            animallocation = AnimalLocation.objects.get(id=visitedLocationPointId)
            animallocation.locationPointId = Location.objects.get(id=locationPointId)
            animallocation.save()

            return JsonResponse(to_dict(animallocation), status=200)

    @action(methods=['post', 'delete'], detail=True, url_path='locations/(?P<pointId>[^/.]+)')
    def add_delete_locations(self, request, pk, pointId):

        # animalId, point > 0 and not None
        data_check = check_error_400_404(pk, pointId)
        if type(data_check) == list:
            animalId, point = data_check
        else:
            return data_check
        if {'id': animalId} not in Animal.objects.values('id'):
            return JsonResponse("ERROR 404", safe=False, status=404)

        if request.method == 'POST':

            # Точка локации с pointId не найдена
            if {'id': point} not in Location.objects.values('id'):
                return JsonResponse("ERROR 404", safe=False, status=404)

            # У животного lifeStatus = "DEAD"
            if Animal.objects.get(id=animalId).lifeStatus == 'DEAD':
                return JsonResponse("ERROR 400", safe=False, status=400)

            # Животное находится в точке чипирования и никуда не перемещалось,
            # попытка добавить точку локации, равную точке чипирования.
            if len(Animal.objects.get(id=animalId).visitedLocations.values()) == 0 and \
                    Animal.objects.get(id=animalId).chippingLocationId.id == point:
                return JsonResponse("ERROR 400", safe=False, status=400)

            # Попытка добавить точку локации, в которой уже находится животное
            if {'locationPointId_id': point} == \
                    Animal.objects.get(id=animalId).visitedLocations.values('locationPointId_id').last():
                return JsonResponse("ERROR 400", safe=False, status=400)

            # Добавление точки локации, посещенной животным
            animalloc = AnimalLocation.objects.create(dateTimeOfVisitLocationPoint=datetime.now(),
                                                      locationPointId=Location.objects.get(id=point))
            Animal.objects.get(id=animalId).visitedLocations.add(animalloc)
            return JsonResponse(to_dict(animalloc), safe=False, status=201)

        if request.method == 'DELETE':

            # Объект с информацией о посещенной точке локации с visitedPointId не найден.
            if {'id': point} not in AnimalLocation.objects.values('id'):
                return JsonResponse("ERROR 404", safe=False, status=404)

            animal = Animal.objects.get(id=animalId)

            # У животного нет объекта с информацией о посещенной точке локации с visitedLocationPointId
            if {'id': point} not in animal.visitedLocations.values('id'):
                return JsonResponse("ERROR 404", safe=False, status=404)

            # Удаление точки локации, посещенной животным
            AnimalLocation.objects.get(id=point).delete()

            # Если удаляется первая посещенная точка локации, а вторая точка
            # совпадает с точкой чипирования, то она удаляется автоматически
            while len(animal.visitedLocations.values()) > 0:
                if animal.visitedLocations.values('locationPointId_id').first() == \
                        {'locationPointId_id': animal.chippingLocationId.id}:
                    AnimalLocation.objects.get(id=animal.visitedLocations.values('id').first().get('id')).delete()
                else:
                    return JsonResponse({}, status=200)

            return JsonResponse({}, status=200)
