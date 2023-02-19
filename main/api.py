from datetime import datetime
from itertools import chain

from django.db.models import ProtectedError
from django.http import HttpResponse
from django.http import JsonResponse
from rest_framework import viewsets, permissions, mixins
from rest_framework.decorators import action

from .models import Account, Location, AnimalType, AnimalLocation, Animal
from .serializers import AccountSerializer, LocationSerializer, AnimalTypeSerializer, AnimalLocationSerializer, \
    AnimalSerializer


def to_dict(instance):
    opts = instance._meta
    data = {}
    for f in chain(opts.concrete_fields, opts.private_fields):
        if f.name != 'password':
            data[f.name] = f.value_from_object(instance)
    for f in opts.many_to_many:
        data[f.name] = [i.id for i in f.value_from_object(instance)]
    return data


class AccountViewSet(viewsets.ModelViewSet):
    queryset = Account.objects.all()
    permission_classes = [
        permissions.AllowAny
    ]
    serializer_class = AccountSerializer

    def retrieve(self, request, pk):
        if pk == "search":
            firstname = self.request.query_params.get('firstName')
            lastname = self.request.query_params.get('lastName')
            email = self.request.query_params.get('email')
            if self.request.query_params.get('from') is None:
                from_ = 0
            else:
                try:
                    from_ = int(self.request.query_params.get('from'))
                except:
                    return HttpResponse(status=400)
            if self.request.query_params.get('size') is None:
                size = 10
            else:
                try:
                    size = int(self.request.query_params.get('size'))
                except:
                    return HttpResponse(status=400)
            if from_ < 0 or size <= 0:
                return HttpResponse(status=400)
            query = Account.objects.all()
            list = []
            for acc in query:
                if firstname is None or firstname.lower() in acc.firstName.lower():
                    if lastname is None or lastname.lower() in acc.lastname.lower():
                        if email is None or email.lower() in acc.email.lower():
                            list.append(to_dict(acc))
            return JsonResponse(list[from_:size], safe=False)
        if pk is None or int(pk) <= 0:
            return HttpResponse(status=400)
        return super(AccountViewSet, self).retrieve(request, pk=None)

    def update(self, request, pk):
        if pk is None or int(pk) <= 0:
            return HttpResponse(status=400)
        query = Account.objects.all()
        if {'id': int(pk)} not in query.values('id'):
            return HttpResponse(status=403)
        for acc in query:
            if acc.email == Account.objects.get(id=pk).email and acc.id != pk:
                return HttpResponse(status=409)
        return super(AccountViewSet, self).update(request, pk=None)

    def destroy(self, request, pk):
        if pk is None or int(pk) <= 0:
            return HttpResponse(status=400)
        query = Account.objects.all()
        for acc in query:
            if int(acc.id) == int(pk):
                return super(AccountViewSet, self).destroy(request, pk=None)
        return HttpResponse(status=403)


class LocationViewSet(viewsets.ModelViewSet):
    queryset = Location.objects.all()
    permission_classes = [
        permissions.AllowAny
    ]
    serializer_class = LocationSerializer

    def retrieve(self, request, pk):
        if pk is None or int(pk) <= 0:
            return HttpResponse(status=400)
        return super(LocationViewSet, self).retrieve(request, pk=None)

    def create(self, request):
        latitude = float(request.data.get('latitude'))
        longitude = float(request.data.get('longitude'))
        if latitude < -90 or latitude > 90 or longitude < -180 or longitude > 180:
            return HttpResponse(status=400)
        for loc in Location.objects.all():
            if loc.latitude == latitude and loc.longitude == longitude:
                return HttpResponse(status=409)
        return super(LocationViewSet, self).create(request)

    def update(self, request, pk=None):
        latitude = float(request.data.get('latitude'))
        longitude = float(request.data.get('longitude'))
        if pk is None or int(pk) <= 0:
            return HttpResponse(status=400)
        if latitude < -90 or latitude > 90 or longitude < -180 or longitude > 180:
            return HttpResponse(status=400)
        for loc in Location.objects.all():
            if loc.latitude == latitude and loc.longitude == longitude:
                return HttpResponse(status=409)
        return super(LocationViewSet, self).update(request, pk=None)

    def destroy(self, request, pk):
        if pk is None or int(pk) <= 0:
            return HttpResponse(status=400)
        try:
            return super(LocationViewSet, self).destroy(request, pk=None)
        except ProtectedError:
            return HttpResponse(status=400)


class AnimalTypeViewSet(viewsets.ModelViewSet):
    queryset = AnimalType.objects.all()
    permission_classes = [
        permissions.AllowAny
    ]
    serializer_class = AnimalTypeSerializer

    def create(self, request):
        type_ = request.data.get('type')
        for types in AnimalType.objects.all():
            if types.type == type_:
                return HttpResponse(status=409)
        return super(AnimalTypeViewSet, self).create(request)

    def retrieve(self, request, pk=None):
        if pk is None or int(pk) <= 0:
            return HttpResponse(status=400)
        return super(AnimalTypeViewSet, self).retrieve(request, pk=None)

    def update(self, request, pk=None):
        if pk is None or int(pk) <= 0:
            return HttpResponse(status=400)
        type_ = request.data.get('type')
        for types in AnimalType.objects.all():
            if types.type == type_:
                return HttpResponse(status=409)
        return super(AnimalTypeViewSet, self).update(request, pk=None)

    def destroy(self, request, pk=None):
        if pk is None or int(pk) <= 0:
            return HttpResponse(status=400)
        return super(AnimalTypeViewSet, self).destroy(request, pk=None)


class AnimalLocationViewSet(viewsets.ModelViewSet):
    queryset = AnimalLocation.objects.all()
    permission_classes = [
        permissions.AllowAny
    ]
    serializer_class = AnimalLocationSerializer


class AnimalViewSet(viewsets.ModelViewSet):
    queryset = Animal.objects.all()
    permission_classes = [
        permissions.AllowAny
    ]
    serializer_class = AnimalSerializer

    def retrieve(self, request, pk=None):
        if pk == "search":
            if self.request.query_params.get('startDateTime') is None:
                startdatetime = None
            else:
                try:
                    startdatetime = datetime.fromisoformat(self.request.query_params.get('startDateTime'))
                except:
                    return HttpResponse(status=400)
            if self.request.query_params.get('endDateTime') is None:
                enddatetime = None
            else:
                try:
                    enddatetime = datetime.fromisoformat(self.request.query_params.get('endDateTime'))
                except:
                    return HttpResponse(status=400)
            try:
                if self.request.query_params.get('chipperId') is not None:
                    chipperid = int(self.request.query_params.get('chipperId'))
                else:
                    chipperid = None
            except:
                return HttpResponse(status=400)
            try:
                if self.request.query_params.get('chippingLocationId') is not None:
                    chippinglocationid = int(self.request.query_params.get('chippingLocationId'))
                else:
                    chippinglocationid = None
            except:
                return HttpResponse(status=400)
            lifestatus = self.request.query_params.get('lifeStatus')
            gender = self.request.query_params.get('gender')
            if lifestatus != 'ALIVE' and lifestatus != 'DEAD' and lifestatus is not None:
                return HttpResponse(status=400)
            if gender != 'MALE' and gender != 'FEMALE' and gender != 'OTHER' and gender is not None:
                return HttpResponse(status=400)
            if self.request.query_params.get('from') is None:
                from_ = 0
            else:
                try:
                    from_ = int(self.request.query_params.get('from'))
                except:
                    return HttpResponse(status=400)
            if self.request.query_params.get('size') is None:
                size = 10
            else:
                try:
                    size = int(self.request.query_params.get('size'))
                except:
                    return HttpResponse(status=400)
            if from_ < 0 or size <= 0 or (chipperid is not None and chipperid <= 0) or (
                    chippinglocationid is not None and chippinglocationid <= 0):
                return HttpResponse(status=400)
            query = Animal.objects.all()
            list = []
            for animal in query:
                if startdatetime is None or startdatetime.timestamp() <= animal.chippingDateTime.timestamp():
                    if enddatetime is None or enddatetime.timestamp() >= animal.chippingDateTime.timestamp():
                        if chipperid is None or chipperid == animal.chipperId.id:
                            if chippinglocationid is None or chippinglocationid == animal.chippingLocationId.id:
                                if gender is None or gender == animal.gender:
                                    if lifestatus is None or lifestatus == animal.lifeStatus:
                                        list.append(to_dict(animal))

            return JsonResponse(list[from_:size], safe=False)
        if pk is None or int(pk) <= 0:
            return HttpResponse(status=400)
        return super(AnimalViewSet, self).retrieve(request, pk=None)

    def create(self, request):
        types = request.data.get('animalTypes')
        chipperid = request.data.get('chipperId')
        chippinglocationid = request.data.get('chippingLocationId')
        if request.data.get('weight') is not None and request.data.get('length') is not None and request.data.get(
                'height') is not None:
            if request.data.get('weight') <= 0 or request.data.get('length') <= 0 or request.data.get('height') <= 0:
                return HttpResponse(status=400)
            if types is not None:
                if types != list(set(types)):
                    return HttpResponse(status=409)
                for animaltype in types:
                    if animaltype is not None:
                        if animaltype > 0 and {'id': animaltype} not in AnimalType.objects.values('id'):
                            return HttpResponse(status=404)
                if chipperid is not None and chippinglocationid is not None:
                    if chipperid > 0 and {'id': chipperid} not in Account.objects.values('id'):
                        return HttpResponse(status=404)
                    if chippinglocationid > 0 and {'id': chippinglocationid} not in Location.objects.values('id'):
                        return HttpResponse(status=404)
        return super(AnimalViewSet, self).create(request)

    def update(self, request, pk):
        if pk is None or int(pk) <= 0:
            return HttpResponse(status=400)
        if {"id": pk} not in Animal.objects.values('id'):
            return HttpResponse(status=404)
        chipperid = request.data.get('chipperId')
        chippinglocationid = request.data.get('chippingLocationId')
        if request.data.get('weight') is not None and request.data.get('length') is not None and request.data.get(
                'height') is not None:
            if request.data.get('weight') <= 0 or request.data.get('length') <= 0 or request.data.get('height') <= 0:
                return HttpResponse(status=400)
            if request.data.get('lifeStatus'):
                if request.data.get('lifeStatus') == 'ALIVE' and Animal.objects.get(id=pk).lifeStatus == 'DEAD':
                    return HttpResponse(status=400)
                if chipperid is not None and chippinglocationid is not None:
                    if chippinglocationid == Animal.objects.get(id=pk).visitedLocations.values()[0][
                        'locationPointId_id']:
                        return HttpResponse(status=400)
                    if chipperid > 0 and {'id': chipperid} not in Account.objects.values('id'):
                        return HttpResponse(status=404)
                    if chippinglocationid > 0 and {'id': chippinglocationid} not in Location.objects.values('id'):
                        return HttpResponse(status=404)
        return super(AnimalViewSet, self).update(request, pk)

    def destroy(self, request, pk):
        if pk is None or int(pk) <= 0:
            return HttpResponse(status=400)
        if {"id": int(pk)} not in Animal.objects.values('id'):
            return HttpResponse(status=404)
        if len(Animal.objects.get(id=pk).visitedLocations.values()) > 0:
            return HttpResponse(status=400)
        return super(AnimalViewSet, self).destroy(request, pk)

    @action(methods=['delete', 'post'], detail=True, url_path='types/(?P<typeId>[^/.]+)')
    def type_post_delete(self, request, pk, typeId):
        if request.method == 'DELETE':
            if pk is None or typeId is None or int(pk) <= 0 or int(typeId) <= 0:
                return HttpResponse(status=400)
            if {"id": int(pk)} not in Animal.objects.values('id') or {
                "id": int(typeId)} not in AnimalType.objects.values(
                    'id'):
                return HttpResponse(status=404)
            if {'id': int(typeId)} not in Animal.objects.get(id=int(pk)).animalTypes.values('id'):
                return HttpResponse(status=404)
            if len(Animal.objects.get(id=int(pk)).animalTypes.values('id')) == 1 and \
                    Animal.objects.get(id=int(pk)).animalTypes.values('id')[0] == {'id': int(typeId)}:
                return HttpResponse(status=400)
            removeAnimalType = Animal.objects.get(id=int(pk)).animalTypes.get(id=int(typeId))
            Animal.objects.get(id=int(pk)).animalTypes.remove(removeAnimalType)
            queryset = super(AnimalViewSet, self).get_queryset().get(id=pk)
            serializer = AnimalSerializer(queryset)
            return JsonResponse(serializer.data, safe=False)

        elif request.method == 'POST':
            if pk is None or typeId is None or int(pk) <= 0 or int(typeId) <= 0:
                return HttpResponse(status=400)
            if {"id": int(pk)} not in Animal.objects.values('id') or {
                "id": int(typeId)} not in AnimalType.objects.values(
                'id'):
                return HttpResponse(status=404)
            if {'id': int(typeId)} not in AnimalType.objects.values('id'):
                return HttpResponse(status=404)
            if {'id': int(typeId)} in Animal.objects.get(id=int(pk)).animalTypes.values('id'):
                return HttpResponse(status=409)
            Animal.objects.get(id=int(pk)).animalTypes.add(AnimalType.objects.get(id=int(typeId)))
            queryset = super(AnimalViewSet, self).get_queryset().get(id=pk)
            serializer = AnimalSerializer(queryset)
            return JsonResponse(serializer.data, safe=False, status=201)

    @action(methods=['put'], detail=True, url_path='types')
    def update_types(self, request, pk):
        oldtypeid = request.data.get('oldTypeId')
        newtypeid = request.data.get('newTypeId')
        if pk is None or oldtypeid is None or newtypeid is None or int(pk) <= 0 or int(oldtypeid) <= 0 or int(
                newtypeid) <= 0:
            return HttpResponse(status=400)
        if {'id': int(pk)} not in Animal.objects.values('id'):
            return HttpResponse(status=404)
        if {'id': int(oldtypeid)} not in AnimalType.objects.values('id') or {'id': int(newtypeid)} not in AnimalType.\
                objects.values('id'):
            return HttpResponse(status=404)
        if {'id': int(oldtypeid)} not in Animal.objects.get(id=int(pk)).animalTypes.values('id'):
            return HttpResponse(status=404)
        if {'id': int(newtypeid)} in Animal.objects.get(id=int(pk)).animalTypes.values('id'):
            return HttpResponse(status=409)
        removeAnimalType = Animal.objects.get(id=int(pk)).animalTypes.get(id=int(oldtypeid))
        Animal.objects.get(id=int(pk)).animalTypes.remove(removeAnimalType)
        Animal.objects.get(id=int(pk)).animalTypes.add(AnimalType.objects.get(id=int(newtypeid)))
        queryset = super(AnimalViewSet, self).get_queryset().get(id=pk)
        serializer = AnimalSerializer(queryset)
        return JsonResponse(serializer.data, safe=False, status=200)
