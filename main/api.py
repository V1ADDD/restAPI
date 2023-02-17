from django.http import HttpResponse

from .models import Account, Location, AnimalType
from rest_framework import viewsets, permissions
from .serializers import AccountSerializer, LocationSerializer, AnimalTypeSerializer
from django.http import JsonResponse


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
            try:
                from_ = int(self.request.query_params.get('from'))
            except:
                from_ = 0
            try:
                size = int(self.request.query_params.get('size'))
            except:
                size = 10
            if from_ < 0 or size <= 0:
                return HttpResponse(status=400)
            query = Account.objects.all()
            list = []
            for acc in query:
                if firstname is None or firstname.lower() in acc.firstName.lower():
                    if lastname is None or lastname.lower() in acc.lastname.lower():
                        if email is None or email.lower() in acc.email.lower():
                            list.append({'id': acc.id, 'firstName': acc.firstName,
                                         'lastName': acc.lastName, 'email': acc.email})
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
        return super(LocationViewSet, self).destroy(request, pk=None)


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
