import json
from datetime import datetime
from itertools import chain
from .api_authenticate import AuthAccount, NotAuth, Auth
import re
from django.db.models import ProtectedError
from django.http import JsonResponse
from rest_framework import viewsets, permissions
from rest_framework.decorators import action, api_view, authentication_classes

from .models import Account, Location, AnimalType, AnimalLocation, Animal
from .serializers import AccountSerializer, LocationSerializer, AnimalTypeSerializer, AnimalSerializer


def check_error_400_404(*args):
    result = []
    for arg in args:
        if arg is None:
            return JsonResponse({"Error": "ERROR 400"}, safe=False, status=400)
        try:
            arg_ = int(arg)
            if arg_ <= 0:
                return JsonResponse({"Error": "ERROR 400"}, safe=False, status=400)
            result.append(arg_)
        except:
            return JsonResponse({"Error": "ERROR 400"}, safe=False, status=404)
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
            if type(f.value_from_object(instance)) == datetime:
                data[f.name] = str(f.value_from_object(instance)) + "Z"
                data[f.name] = data[f.name].replace("+00:00", "")
                data[f.name] = data[f.name].replace(" ", "T")
            else:
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
        return JsonResponse({"Error": "ERROR 400"}, safe=False, status=400)
    try:

        # email validation
        regex = re.compile(r'([A-Za-z0-9]+[._-])*[A-Za-z0-9]+@[A-Za-z0-9-]+(\.[A-Z|a-z]{2,})+')
        if not re.fullmatch(regex, email):
            return JsonResponse({"Error": "ERROR 400"}, safe=False, status=400)

        # validation
        if len(firstName.rstrip('\n\t ')) == 0 or len(lastName.rstrip('\n\t ')) == 0 or len(
                password.rstrip('\n\t ')) == 0:
            return JsonResponse({"Error": "ERROR 400"}, safe=False, status=400)
    except TypeError:

        # none
        return JsonResponse({"Error": "ERROR 400"}, safe=False, status=400)
    except AttributeError:

        # none
        return JsonResponse({"Error": "ERROR 400"}, safe=False, status=400)

    # email already exists
    if {'email': email} in Account.objects.values('email'):
        return JsonResponse({"Error": "ERROR 409"}, safe=False, status=409)

    # ?????????????????????? ???????????? ????????????????
    newAccount = Account(firstName=firstName, lastName=lastName, email=email, password=password)
    newAccount.save()
    serializer = AccountSerializer(newAccount)
    return JsonResponse(serializer.data, safe=False, status=201)


class AccountViewSet(viewsets.ModelViewSet):
    authentication_classes = (AuthAccount,)
    queryset = Account.objects.all()
    permission_classes = [
        permissions.AllowAny
    ]
    serializer_class = AccountSerializer

    def retrieve(self, request, pk):
        # ?????????? ?????????????????? ?????????????????????????? ???? ????????????????????
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
                    return JsonResponse({"Error": "ERROR 400"}, safe=False, status=400)
            if self.request.query_params.get('size') is None:
                size = 10
            else:
                try:
                    size = int(self.request.query_params.get('size'))
                except:
                    return JsonResponse({"Error": "ERROR 400"}, safe=False, status=400)
            if from_ < 0 or size <= 0:
                return JsonResponse({"Error": "ERROR 400"}, safe=False, status=400)

            query = Account.objects.all()
            result = []
            for acc in query:
                if firstname is None or firstname.lower() in acc.firstName.lower():
                    if lastname is None or lastname.lower() in acc.lastName.lower():
                        if email is None or email.lower() in acc.email.lower():
                            result.append(to_dict(acc))
            return JsonResponse(result[from_:from_ + size], safe=False)

        # validating pk
        data_check = check_error_400_404(pk)
        if type(data_check) != list:
            return data_check

        # ?????????????????? ???????????????????? ???? ???????????????? ????????????????????????
        return super(AccountViewSet, self).retrieve(request, pk=None)

    def update(self, request, pk):
        # validating pk
        data_check = check_error_400_404(pk)
        if type(data_check) != list:
            return data_check

        # not your account
        if request.user.id != int(pk):
            return JsonResponse({"Error": "ERROR 403"}, safe=False, status=403)

        query = Account.objects.all()

        # ?????????????? ???? ????????????
        if {'id': int(pk)} not in query.values('id'):
            return JsonResponse({"Error": "ERROR 403"}, safe=False, status=403)

        # validation
        data = json.loads(request.body)
        try:
            firstName = data['firstName']
            lastName = data['lastName']
            email = data['email']
            password = data['password']
        except KeyError:

            # check if wasn't in a request
            return JsonResponse({"Error": "ERROR 400"}, safe=False, status=400)
        try:

            # email validation
            regex = re.compile(r'([A-Za-z0-9]+[._-])*[A-Za-z0-9]+@[A-Za-z0-9-]+(\.[A-Z|a-z]{2,})+')
            if not re.fullmatch(regex, email):
                return JsonResponse({"Error": "ERROR 400"}, safe=False, status=400)

            # validation
            if len(firstName.rstrip('\n\t ')) == 0 or len(lastName.rstrip('\n\t ')) == 0 or len(
                    password.rstrip('\n\t ')) == 0:
                return JsonResponse({"Error": "ERROR 400"}, safe=False, status=400)
        except TypeError:

            # none
            return JsonResponse({"Error": "ERROR 400"}, safe=False, status=400)
        except AttributeError:

            # none
            return JsonResponse({"Error": "ERROR 400"}, safe=False, status=400)

        # ?????????????? ?? ?????????? email ?????? ????????????????????
        for acc in query:
            if acc.email == Account.objects.get(id=pk).email and acc.id != int(pk):
                return JsonResponse({"Error": "ERROR 409"}, safe=False, status=409)

        # ???????????????????? ???????????? ???????????????? ????????????????????????
        return super(AccountViewSet, self).update(request, pk=None)

    def destroy(self, request, pk):
        # validating pk
        data_check = check_error_400_404(pk)
        if type(data_check) != list:
            return data_check

        # not your account
        if request.user.id != int(pk):
            return JsonResponse({"Error": "ERROR 403"}, safe=False, status=403)

        # ?????????????? ?? ?????????? accountId ???? ????????????
        if {'id': int(pk)} not in Account.objects.values('id'):
            return JsonResponse({"Error": "ERROR 403"}, safe=False, status=403)

        # ???????????????? ???????????????? ????????????????????????
        try:
            Account.objects.get(id=pk).delete()
            return JsonResponse({}, status=200)
        except ProtectedError:
            # ?????????????? ???????????? ?? ????????????????
            return JsonResponse({"Error": "ERROR 400"}, safe=False, status=400)


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

        # ?????????????????? ???????????????????? ?? ?????????? ?????????????? ????????????????
        return super(LocationViewSet, self).retrieve(request, pk=None)

    def create(self, request):
        # validating latitude and longitude
        try:
            latitude = float(request.data.get('latitude'))
            longitude = float(request.data.get('longitude'))
        except:
            return JsonResponse({"Error": "ERROR 400"}, safe=False, status=400)
        if latitude < -90 or latitude > 90 or longitude < -180 or longitude > 180:
            return JsonResponse({"Error": "ERROR 400"}, safe=False, status=400)

        # ?????????? ?????????????? ?? ???????????? latitude ?? longitude ?????? ????????????????????
        for loc in Location.objects.all():
            if loc.latitude == latitude and loc.longitude == longitude:
                return JsonResponse({"Error": "ERROR 409"}, safe=False, status=409)

        # ???????????????????? ?????????? ?????????????? ????????????????
        return super(LocationViewSet, self).create(request)

    def update(self, request, pk=None):
        # validating latitude and longitude
        try:
            latitude = float(request.data.get('latitude'))
            longitude = float(request.data.get('longitude'))
        except:
            return JsonResponse({"Error": "ERROR 400"}, safe=False, status=400)
        if latitude < -90 or latitude > 90 or longitude < -180 or longitude > 180:
            return JsonResponse({"Error": "ERROR 400"}, safe=False, status=400)

        # validating pk
        data_check = check_error_400_404(pk)
        if type(data_check) != list:
            return data_check

        # ?????????? ?????????????? ?? ???????????? latitude ?? longitude ?????? ????????????????????
        for loc in Location.objects.all():
            if loc.latitude == latitude and loc.longitude == longitude:
                return JsonResponse({"Error": "ERROR 409"}, safe=False, status=409)

        # ?????????????????? ?????????? ?????????????? ????????????????
        return super(LocationViewSet, self).update(request, pk=None)

    def destroy(self, request, pk):
        # validating pk
        data_check = check_error_400_404(pk)
        if type(data_check) == list:
            pk = data_check[0]
        else:
            return data_check

        # ?????????? ?????????????? ?? ?????????? pointId ???? ??????????????
        if {'id': pk} not in Location.objects.values('id'):
            return JsonResponse({"Error": "ERROR 404"}, safe=False, status=404)

        # ???????????????? ?????????? ?????????????? ????????????????
        try:
            Location.objects.get(id=pk).delete()
            return JsonResponse({}, status=200)
        except ProtectedError:
            # ?????????? ?????????????? ?????????????? ?? ????????????????
            return JsonResponse({"Error": "ERROR 400"}, safe=False, status=400)


class AnimalTypeViewSet(viewsets.ModelViewSet):
    authentication_classes = (Auth,)
    queryset = AnimalType.objects.all()
    permission_classes = [
        permissions.AllowAny
    ]
    serializer_class = AnimalTypeSerializer

    def create(self, request):
        # ?????? ?????????????????? ?? ?????????? type ?????? ????????????????????
        if {'type': request.data.get('type')} in AnimalType.objects.values('type'):
            return JsonResponse({"Error": "ERROR 409"}, safe=False, status=409)

        # ???????????????????? ???????? ??????????????????
        return super(AnimalTypeViewSet, self).create(request)

    def retrieve(self, request, pk=None):
        # validating pk
        data_check = check_error_400_404(pk)
        if type(data_check) != list:
            return data_check

        # ?????????????????? ???????????????????? ?? ???????? ??????????????????
        return super(AnimalTypeViewSet, self).retrieve(request, pk=None)

    def update(self, request, pk=None):
        # validating pk
        data_check = check_error_400_404(pk)
        if type(data_check) != list:
            return data_check

        # ?????? ?????????????????? ?? ?????????? type ?????? ????????????????????
        if {'type': request.data.get('type')} in AnimalType.objects.values('type'):
            return JsonResponse({"Error": "ERROR 409"}, safe=False, status=409)

        # ?????????????????? ???????? ??????????????????
        return super(AnimalTypeViewSet, self).update(request, pk=None)

    def destroy(self, request, pk=None):
        # validating pk
        data_check = check_error_400_404(pk)
        if type(data_check) == list:
            pk = data_check[0]
        else:
            return data_check

        # ?????? ?????????????????? ?? ?????????? typeId ???? ????????????
        if {'id': pk} not in AnimalType.objects.values('id'):
            return JsonResponse({"Error": "ERROR 404"}, safe=False, status=404)

        # ???????? ???????????????? ?? ?????????? ?? typeId
        for animal in Animal.objects.all():
            if {'id': pk} in animal.animalTypes.values('id'):
                return JsonResponse({"Error": "ERROR 400"}, safe=False, status=400)

        # ???????????????? ???????? ??????????????????
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
        # ?????????? ???????????????? ???? ????????????????????
        if pk == "search":
            # validating dateTimes
            if self.request.query_params.get('startDateTime') is None:
                startdatetime = None
            else:
                try:
                    startdatetime = datetime.fromisoformat(
                        self.request.query_params.get('startDateTime')[:-1])
                except:
                    return JsonResponse({"Error": "ERROR 400"}, safe=False, status=400)
            if self.request.query_params.get('endDateTime') is None:
                enddatetime = None
            else:
                try:
                    enddatetime = datetime.fromisoformat(
                        self.request.query_params.get('endDateTime')[:-1])
                except:
                    return JsonResponse({"Error": "ERROR 400_"}, safe=False, status=400)

            # chipperId, chippingLocationId validation
            data_check1 = check_error_400_404(self.request.query_params.get('chipperId'))
            if type(data_check1) == list:
                chipperid = data_check1[0]
            else:
                chipperid = None
            data_check2 = check_error_400_404(self.request.query_params.get('chippingLocationId'))
            if type(data_check2) == list:
                chippinglocationid = data_check2[0]
            else:
                chippinglocationid = None
            # lifestatus, gender validation
            lifestatus = self.request.query_params.get('lifeStatus')
            gender = self.request.query_params.get('gender')
            if lifestatus != 'ALIVE' and lifestatus != 'DEAD' and lifestatus is not None:
                return JsonResponse({"Error": "ERROR 400"}, safe=False, status=400)
            if gender != 'MALE' and gender != 'FEMALE' and gender != 'OTHER' and gender is not None:
                return JsonResponse({"Error": "ERROR 400"}, safe=False, status=400)

            # from, size validation and default
            if self.request.query_params.get('from') is None:
                from_ = 0
            else:
                try:
                    from_ = int(self.request.query_params.get('from'))
                except:
                    return JsonResponse({"Error": "ERROR 400"}, safe=False, status=400)
            if self.request.query_params.get('size') is None:
                size = 10
            else:
                try:
                    size = int(self.request.query_params.get('size'))
                except:
                    return JsonResponse({"Error": "ERROR 400"}, safe=False, status=400)
            if from_ < 0 or size <= 0:
                return JsonResponse({"Error": "ERROR 400"}, safe=False, status=400)

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
            return JsonResponse(result[from_:from_ + size], safe=False)
        # validating pk
        data_check = check_error_400_404(pk)
        if type(data_check) != list:
            return data_check

        # ?????????????????? ???????????????????? ?? ????????????????
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
            return JsonResponse({"Error": "ERROR 404"}, safe=False, status=404)

        types = request.data.get('animalTypes')

        # weight, length, height validation
        if request.data.get('weight') is None or request.data.get('length') is None or request.data.get(
                'height') is None:
            return JsonResponse({"Error": "ERROR 400"}, safe=False, status=400)
        if request.data.get('weight') <= 0 or request.data.get('length') <= 0 or request.data.get('height') <= 0:
            return JsonResponse({"Error": "ERROR 400"}, safe=False, status=400)

        # types validation
        if types is not None:
            if types != list(set(types)):
                return JsonResponse({"Error": "ERROR 409"}, safe=False, status=409)
            for animaltype in types:
                if animaltype is not None:
                    if animaltype > 0 and {'id': animaltype} not in AnimalType.objects.values('id'):
                        return JsonResponse({"Error": "ERROR 404"}, safe=False, status=404)

        #  ???????????????????? ???????????? ??????????????????
        return super(AnimalViewSet, self).create(request)

    def update(self, request, pk):
        # pk, chipperId, chippingLocationId validation
        data_check = check_error_400_404(pk, request.data.get('chipperId'), request.data.get('chippingLocationId'))
        if type(data_check) == list:
            pk, chipperid, chippinglocationid = data_check
        else:
            return data_check
        if {"id": pk} not in Animal.objects.values('id'):
            return JsonResponse({"Error": "ERROR 404"}, safe=False, status=404)

        # weight, length, height validation
        if request.data.get('weight') is None or request.data.get('length') is None or request.data.get(
                'height') is None:
            return JsonResponse({"Error": "ERROR 400"}, safe=False, status=400)
        if request.data.get('weight') <= 0 or request.data.get('length') <= 0 or request.data.get('height') <= 0:
            return JsonResponse({"Error": "ERROR 400"}, safe=False, status=400)

        # lifeStatus, location, chipper validations
        if request.data.get('lifeStatus'):
            if request.data.get('lifeStatus') == 'ALIVE' and Animal.objects.get(id=pk).lifeStatus == 'DEAD':
                return JsonResponse({"Error": "ERROR 400"}, safe=False, status=400)
            if len(Animal.objects.get(id=pk).visitedLocations.values()) != 0 and \
                    chippinglocationid == Animal.objects.get(id=pk).visitedLocations.values()[0]['locationPointId_id']:
                return JsonResponse({"Error": "ERROR 400"}, safe=False, status=400)
            if {'id': chipperid} not in Account.objects.values('id'):
                return JsonResponse({"Error": "ERROR 404"}, safe=False, status=404)
            if {'id': chippinglocationid} not in Location.objects.values('id'):
                return JsonResponse({"Error": "ERROR 404"}, safe=False, status=404)
        request.data['animalTypes'] = list(Animal.objects.get(id=pk).animalTypes.all().values_list('id', flat=True))
        # ???????????????????? ???????????????????? ?? ????????????????
        return super(AnimalViewSet, self).update(request, pk)

    def destroy(self, request, pk):
        # pk validation
        data_check = check_error_400_404(pk)
        if type(data_check) == list:
            pk = data_check[0]
        else:
            return data_check
        if {"id": pk} not in Animal.objects.values('id'):
            return JsonResponse({"Error": "ERROR 404"}, safe=False, status=404)

        # ???????????????? ???????????????? ?????????????? ??????????????????????, ?????? ???????? ???????? ???????????? ???????????????????? ??????????
        if len(Animal.objects.get(id=pk).visitedLocations.values()) > 0:
            return JsonResponse({"Error": "ERROR 400"}, safe=False, status=400)

        # ???????????????? ??????????????????
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
            return JsonResponse({"Error": "ERROR 404"}, safe=False, status=404)

        if request.method == 'DELETE':
            # ?? ?????????????????? ?? animalId ?????? ???????? ?? typeId
            if {'id': int(typeId)} not in Animal.objects.get(id=pk).animalTypes.values('id'):
                return JsonResponse({"Error": "ERROR 404"}, safe=False, status=404)

            # ?? ?????????????????? ???????????? ???????? ?????? ?? ?????? ?????? ?? typeId
            if len(Animal.objects.get(id=pk).animalTypes.values('id')) == 1 and \
                    Animal.objects.get(id=pk).animalTypes.values('id')[0] == {'id': typeId}:
                return JsonResponse({"Error": "ERROR 400"}, safe=False, status=400)

            # ???????????????? ???????? ?????????????????? ?? ??????????????????
            removeAnimalType = Animal.objects.get(id=pk).animalTypes.get(id=typeId)
            Animal.objects.get(id=pk).animalTypes.remove(removeAnimalType)
            queryset = super(AnimalViewSet, self).get_queryset().get(id=pk)
            serializer = AnimalSerializer(queryset)
            return JsonResponse(serializer.data, safe=False, status=200)

        elif request.method == 'POST':
            # ?????? ?????????????????? ?? typeId ?????? ???????? ?? ?????????????????? ?? animalId
            if {'id': typeId} in Animal.objects.get(id=pk).animalTypes.values('id'):
                return JsonResponse({"Error": "ERROR 409"}, safe=False, status=409)

            # ???????????????????? ???????? ?????????????????? ?? ??????????????????
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
            return JsonResponse({"Error": "ERROR 404"}, safe=False, status=404)
        if {'id': oldtypeid} not in AnimalType.objects.values('id') or {'id': newtypeid} not in AnimalType. \
                objects.values('id'):
            return JsonResponse({"Error": "ERROR 404"}, safe=False, status=404)
        if {'id': oldtypeid} not in Animal.objects.get(id=pk).animalTypes.values('id'):
            return JsonResponse({"Error": "ERROR 404"}, safe=False, status=404)
        if {'id': newtypeid} in Animal.objects.get(id=pk).animalTypes.values('id'):
            return JsonResponse({"Error": "ERROR 409"}, safe=False, status=409)

        # ?????????????????? ???????? ?????????????????? ?? ??????????????????
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
            return JsonResponse({"Error": "ERROR 404"}, safe=False, status=404)

        if request.method == 'GET':

            # startDateTime and endDateTime validation
            if self.request.query_params.get('startDateTime') is None:
                startdatetime = None
            else:
                try:
                    startdatetime = datetime.fromisoformat(self.request.query_params.get('startDateTime')[:-1])
                except:
                    return JsonResponse({"Error": "ERROR 400"}, safe=False, status=400)
            if self.request.query_params.get('endDateTime') is None:
                enddatetime = None
            else:
                try:
                    enddatetime = datetime.fromisoformat(self.request.query_params.get('endDateTime')[:-1])
                except:
                    return JsonResponse({"Error": "ERROR 400"}, safe=False, status=400)

            # from and size validation and setting to default
            if self.request.query_params.get('from') is None:
                from_ = 0
            else:
                try:
                    from_ = int(self.request.query_params.get('from'))
                except:
                    return JsonResponse({"Error": "ERROR 400"}, safe=False, status=400)
            if self.request.query_params.get('size') is None:
                size = 10
            else:
                try:
                    size = int(self.request.query_params.get('size'))
                except:
                    return JsonResponse({"Error": "ERROR 400"}, safe=False, status=400)
            if from_ < 0 or size <= 0:
                return JsonResponse({"Error": "ERROR 400"}, safe=False, status=400)

            query = Animal.objects.get(id=animalId).visitedLocations.all()

            # ???????????????? ?????????? ??????????????, ???????????????????? ????????????????
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

            # ???????????? ?? ?????????????????????? ?? ???????????????????? ?????????? ?????????????? ?? visitedLocationPointId ???? ????????????.
            if {'id': visitedLocationPointId} not in AnimalLocation.objects.values('id'):
                return JsonResponse({"Error": "ERROR 404"}, safe=False, status=404)

            # ?????????? ?????????????? ?? locationPointId ???? ????????????
            if {'id': locationPointId} not in Location.objects.values('id'):
                return JsonResponse({"Error": "ERROR 404"}, safe=False, status=404)

            animal = Animal.objects.get(id=animalId)

            # ?? ?????????????????? ?????? ?????????????? ?? ?????????????????????? ?? ???????????????????? ?????????? ?????????????? ?? visitedLocationPointId
            if {'id': visitedLocationPointId} not in animal.visitedLocations.values('id'):
                return JsonResponse({"Error": "ERROR 404"}, safe=False, status=404)

            # ???????????????????? ???????????? ???????????????????? ?????????? ???? ?????????? ??????????????????????
            if {'id': visitedLocationPointId} == \
                    animal.visitedLocations.values('id').first() \
                    and animal.chippingLocationId.id == locationPointId:
                return JsonResponse({"Error": "ERROR 400"}, safe=False, status=400)

            # ???????????????????? ?????????? ???? ?????????? ???? ??????????
            if AnimalLocation.objects.get(id=visitedLocationPointId).locationPointId.id == locationPointId:
                return JsonResponse({"Error": "ERROR 400"}, safe=False, status=400)

            # ???????????????????? ?????????? ?????????????? ???? ??????????, ?????????????????????? ???? ?????????????????? ??/?????? ?? ???????????????????? ??????????????
            if {'id': visitedLocationPointId} == animal.visitedLocations.values('id').first() and \
                    {'id': visitedLocationPointId} == animal.visitedLocations.values('id').last():
                pass
            elif {'id': visitedLocationPointId} == animal.visitedLocations.values('id').first():
                if find_next_prev(animal, visitedLocationPointId) == locationPointId:
                    return JsonResponse({"Error": "ERROR 400"}, safe=False, status=400)
            elif {'id': visitedLocationPointId} == animal.visitedLocations.values('id').last():
                if find_next_prev(animal, visitedLocationPointId, next=False) == locationPointId:
                    return JsonResponse({"Error": "ERROR 400"}, safe=False, status=400)
            elif find_next_prev(animal, visitedLocationPointId, next=False) == locationPointId or \
                    find_next_prev(animal, visitedLocationPointId) == locationPointId:
                return JsonResponse({"Error": "ERROR 400"}, safe=False, status=400)

            # ?????????????????? ?????????? ??????????????, ???????????????????? ????????????????
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
            return JsonResponse({"Error": "ERROR 404"}, safe=False, status=404)

        if request.method == 'POST':

            # ?????????? ?????????????? ?? pointId ???? ??????????????
            if {'id': point} not in Location.objects.values('id'):
                return JsonResponse({"Error": "ERROR 404"}, safe=False, status=404)

            # ?? ?????????????????? lifeStatus = "DEAD"
            if Animal.objects.get(id=animalId).lifeStatus == 'DEAD':
                return JsonResponse({"Error": "ERROR 400"}, safe=False, status=400)

            # ???????????????? ?????????????????? ?? ?????????? ?????????????????????? ?? ???????????? ???? ????????????????????????,
            # ?????????????? ???????????????? ?????????? ??????????????, ???????????? ?????????? ??????????????????????.
            if len(Animal.objects.get(id=animalId).visitedLocations.values()) == 0 and \
                    Animal.objects.get(id=animalId).chippingLocationId.id == point:
                return JsonResponse({"Error": "ERROR 400"}, safe=False, status=400)

            # ?????????????? ???????????????? ?????????? ??????????????, ?? ?????????????? ?????? ?????????????????? ????????????????
            if {'locationPointId_id': point} == \
                    Animal.objects.get(id=animalId).visitedLocations.values('locationPointId_id').last():
                return JsonResponse({"Error": "ERROR 400"}, safe=False, status=400)

            # ???????????????????? ?????????? ??????????????, ???????????????????? ????????????????
            animalloc = AnimalLocation.objects.create(dateTimeOfVisitLocationPoint=datetime.now(),
                                                      locationPointId=Location.objects.get(id=point))
            Animal.objects.get(id=animalId).visitedLocations.add(animalloc)
            return JsonResponse(to_dict(animalloc), safe=False, status=201)

        if request.method == 'DELETE':

            # ???????????? ?? ?????????????????????? ?? ???????????????????? ?????????? ?????????????? ?? visitedPointId ???? ????????????.
            if {'id': point} not in AnimalLocation.objects.values('id'):
                return JsonResponse({"Error": "ERROR 404"}, safe=False, status=404)

            animal = Animal.objects.get(id=animalId)

            # ?? ?????????????????? ?????? ?????????????? ?? ?????????????????????? ?? ???????????????????? ?????????? ?????????????? ?? visitedLocationPointId
            if {'id': point} not in animal.visitedLocations.values('id'):
                return JsonResponse({"Error": "ERROR 404"}, safe=False, status=404)

            # ???????????????? ?????????? ??????????????, ???????????????????? ????????????????
            AnimalLocation.objects.get(id=point).delete()

            # ???????? ?????????????????? ???????????? ???????????????????? ?????????? ??????????????, ?? ???????????? ??????????
            # ?????????????????? ?? ???????????? ??????????????????????, ???? ?????? ?????????????????? ??????????????????????????
            while len(animal.visitedLocations.values()) > 0:
                if animal.visitedLocations.values('locationPointId_id').first() == \
                        {'locationPointId_id': animal.chippingLocationId.id}:
                    AnimalLocation.objects.get(id=animal.visitedLocations.values('id').first().get('id')).delete()
                else:
                    return JsonResponse({}, status=200)

            return JsonResponse({}, status=200)
