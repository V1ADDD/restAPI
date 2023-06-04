import base64
import json
from datetime import datetime
from itertools import chain

from django.core.exceptions import ObjectDoesNotExist
from django.shortcuts import get_object_or_404

from .api_authenticate import AuthAccount, NotAuth, Auth
import re
from django.db.models import ProtectedError, Q
from django.http import JsonResponse, HttpResponse
from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action, api_view, authentication_classes
from .polygons import Point, Polygon, does_interact_with_old, is_inside_old, is_inside_new, is_point_inside_polygon, \
    is_identical_to_old
from .models import Account, Location, AnimalType, AnimalLocation, Animal, Area
from .serializers import AccountSerializer, LocationSerializer, AnimalTypeSerializer, AnimalSerializer, AreaSerializer
import geohash


# validation for right value > 0
def check_error_400_404(*args):
    result = []
    for arg in args:
        if arg is None:
            return JsonResponse({"error": "ERROR 400"}, status=status.HTTP_400_BAD_REQUEST)
        try:
            arg_ = int(arg)
            if arg_ <= 0:
                return JsonResponse({"error": "ERROR 400"}, status=status.HTTP_400_BAD_REQUEST)
            result.append(arg_)
        except:
            return JsonResponse({"error": "ERROR 404"}, status=status.HTTP_404_NOT_FOUND)
    return result


# look for the next value in location list
def find_next_prev(animal, id_animal, next=True):
    if next:
        related_obj = animal.visitedLocations.filter(id__gt=id_animal).order_by('id').first()
    else:
        related_obj = animal.visitedLocations.filter(id__lt=id_animal).order_by('-id').first()
    if related_obj:
        return related_obj.locationPointId.id
    return None


# convert instance to dict for further json response
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


# registration
@api_view(['POST'])
@authentication_classes([NotAuth])
def RegistrationView(request):
    try:
        data = json.loads(request.body)
        firstName = data['firstName']
        lastName = data['lastName']
        email = data['email']
        password = data['password']
    except (json.JSONDecodeError, KeyError, TypeError):
        return JsonResponse({"error": "ERROR 400"}, status=status.HTTP_400_BAD_REQUEST)

    # email validation
    regex = re.compile(r'([A-Za-z0-9]+[._-])*[A-Za-z0-9]+@[A-Za-z0-9-]+(\.[A-Z|a-z]{2,})+')
    if not re.fullmatch(regex, email):
        return JsonResponse({"error": "ERROR 400"}, status=status.HTTP_400_BAD_REQUEST)

    # validation
    if not all(map(str.strip, (firstName, lastName, password))):
        return JsonResponse({"error": "ERROR 400"}, status=status.HTTP_400_BAD_REQUEST)

    # check if email already exists
    if Account.objects.filter(email=email).exists():
        return JsonResponse({"error": "ERROR 409"}, status=status.HTTP_409_CONFLICT)

    # register a new account
    new_account = Account(firstName=firstName, lastName=lastName, email=email, password=password)
    new_account.save()
    serializer = AccountSerializer(new_account)
    return JsonResponse(serializer.data, safe=False, status=status.HTTP_201_CREATED)


# view set for account functionality
class AccountViewSet(viewsets.ModelViewSet):
    authentication_classes = (AuthAccount,)
    queryset = Account.objects.all()
    permission_classes = [permissions.AllowAny]
    serializer_class = AccountSerializer

    # admin creates new users
    def create(self, request):
        if request.user.role != 'ADMIN':
            return JsonResponse({"error": "ERROR 403"}, status=status.HTTP_403_FORBIDDEN)

        email = request.data.get('email')
        if not email:
            return JsonResponse({"error": "ERROR 400"}, status=status.HTTP_400_BAD_REQUEST)

        if not re.fullmatch(r'([A-Za-z0-9]+[._-])*[A-Za-z0-9]+@[A-Za-z0-9-]+(\.[A-Z|a-z]{2,})+', email):
            return JsonResponse({"error": "ERROR 400"}, status=status.HTTP_400_BAD_REQUEST)

        if Account.objects.filter(email=email).exists():
            return JsonResponse({"error": "ERROR 409"}, status=status.HTTP_409_CONFLICT)

        return super().create(request)

    # get user
    def retrieve(self, request, pk=None):
        user = request.user

        # admin can search for users
        if pk == "search":
            if user.role != 'ADMIN':
                return JsonResponse({"error": "ERROR 403"}, status=status.HTTP_403_FORBIDDEN)

            firstname = self.request.query_params.get('firstName')
            lastname = self.request.query_params.get('lastName')
            email = self.request.query_params.get('email')
            from_ = int(self.request.query_params.get('from', 0))
            size = int(self.request.query_params.get('size', 10))

            if from_ < 0 or size <= 0:
                return JsonResponse({"error": "ERROR 400"}, status=status.HTTP_400_BAD_REQUEST)

            queryset = Account.objects.all()
            if firstname:
                queryset = queryset.filter(firstName__icontains=firstname)
            if lastname:
                queryset = queryset.filter(lastName__icontains=lastname)
            if email:
                queryset = queryset.filter(email__icontains=email)

            results = [to_dict(acc) for acc in queryset[from_:from_ + size]]
            return JsonResponse(results, safe=False, status=status.HTTP_200_OK)

        account = get_object_or_404(Account, id=pk)

        if user.role == 'ADMIN' or user.id == account.id:
            return super().retrieve(request, pk=pk)

        return JsonResponse({"error": "ERROR 403"}, status=status.HTTP_403_FORBIDDEN)

    # updating user's info
    def update(self, request, pk):
        user = request.user
        account = Account.objects.filter(id=pk).first()

        if user.role != 'ADMIN' and user.id != int(pk):
            return JsonResponse({"error": "ERROR 403"}, status=status.HTTP_403_FORBIDDEN)

        if not account:
            return JsonResponse({"error": "ERROR 404"}, status=status.HTTP_404_NOT_FOUND)

        data = json.loads(request.body)
        first_name = data.get('firstName', '').strip()
        last_name = data.get('lastName', '').strip()
        email = data.get('email', '').strip()
        password = data.get('password', '').strip()

        if not all([first_name, last_name, email, password]):
            return JsonResponse({"error": "ERROR 400"}, status=status.HTTP_400_BAD_REQUEST)

        if not re.fullmatch(r'([A-Za-z0-9]+[._-])*[A-Za-z0-9]+@[A-Za-z0-9-]+(\.[A-Z|a-z]{2,})+', email):
            return JsonResponse({"error": "ERROR 400"}, status=status.HTTP_400_BAD_REQUEST)

        if Account.objects.filter(email=email).exclude(id=pk).exists():
            return JsonResponse({"error": "ERROR 409"}, status=status.HTTP_409_CONFLICT)

        return super().update(request, pk)

    # delete user
    def destroy(self, request, pk):
        user = request.user
        account = Account.objects.filter(id=pk).first()

        if user.role != 'ADMIN' and user.id != int(pk):
            return JsonResponse({"error": "ERROR 403"}, status=status.HTTP_403_FORBIDDEN)

        if not account:
            return JsonResponse({"error": "ERROR 404"}, status=status.HTTP_404_NOT_FOUND)

        try:
            account.delete()
            return JsonResponse({}, status=status.HTTP_200_OK)
        except ProtectedError:
            return JsonResponse({"error": "ERROR 400"}, status=status.HTTP_400_BAD_REQUEST)


# view set for locations functionality
class LocationViewSet(viewsets.ModelViewSet):
    authentication_classes = (Auth,)
    queryset = Location.objects.all()
    permission_classes = [permissions.AllowAny]
    serializer_class = LocationSerializer

    # secret endpoint 1
    def list(self, request):
        latitude = request.query_params.get('latitude', None)
        longitude = request.query_params.get('longitude', None)
        if latitude is None or longitude is None:
            return JsonResponse({'error': 'ERROR 400'}, status=status.HTTP_400_BAD_REQUEST)
        try:
            location = get_object_or_404(Location, latitude=latitude, longitude=longitude)
            return HttpResponse(location.id, content_type='application/json')
        except:
            return JsonResponse({'error': 'ERROR 404'}, status=status.HTTP_404_NOT_FOUND)

    # secret endpoint 2
    @action(detail=False, url_path='geohash')
    def geohash(self, request):
        latitude = request.query_params.get('latitude', None)
        longitude = request.query_params.get('longitude', None)
        if latitude is None or longitude is None:
            return JsonResponse({'error': 'ERROR 400'}, status=status.HTTP_400_BAD_REQUEST)
        try:
            location = get_object_or_404(Location, latitude=latitude, longitude=longitude)
            return HttpResponse(geohash.encode(float(latitude), float(longitude)), content_type='application/json')
        except:
            return JsonResponse({'error': 'ERROR 404'}, status=status.HTTP_404_NOT_FOUND)

    # secret endpoint 3
    @action(detail=False, url_path='geohashv2')
    def geohash2(self, request):
        latitude = request.query_params.get('latitude', None)
        longitude = request.query_params.get('longitude', None)
        if latitude is None or longitude is None:
            return JsonResponse({'error': 'ERROR 400'}, status=status.HTTP_400_BAD_REQUEST)
        try:
            location = get_object_or_404(Location, latitude=latitude, longitude=longitude)
            geohash_str = geohash.encode(float(latitude), float(longitude)).encode('ascii')
            return HttpResponse(base64.b64encode(geohash_str), content_type='application/json')
        except:
            return JsonResponse({'error': 'ERROR 404'}, status=status.HTTP_404_NOT_FOUND)

    # secret endpoint 4 ?
    @action(detail=False, url_path='geohashv3')
    def geohash3(self, request):
        latitude = request.query_params.get('latitude', None)
        longitude = request.query_params.get('longitude', None)
        if latitude is None or longitude is None:
            return JsonResponse({'error': 'ERROR 400'}, status=status.HTTP_400_BAD_REQUEST)
        try:
            location = get_object_or_404(Location, latitude=latitude, longitude=longitude)
            return HttpResponse(geohash.encode(float(latitude), float(longitude)), content_type='application/json')
        except:
            return JsonResponse({'error': 'ERROR 404'}, status=status.HTTP_404_NOT_FOUND)

    # get location
    def retrieve(self, request, pk):
        # validating pk
        data_check = check_error_400_404(pk)
        if isinstance(data_check, JsonResponse):
            return data_check

        return super().retrieve(request, pk)

    # create location
    def create(self, request):
        if request.user.role == 'USER':
            return JsonResponse({'error': 'ERROR 403'}, status=status.HTTP_403_FORBIDDEN)

        try:
            latitude = float(request.data.get('latitude'))
            longitude = float(request.data.get('longitude'))
        except ValueError:
            return JsonResponse({"error": "ERROR 400"}, status=status.HTTP_400_BAD_REQUEST)

        if not (-90 <= latitude <= 90 and -180 <= longitude <= 180):
            return JsonResponse({"error": "ERROR 400"}, status=status.HTTP_400_BAD_REQUEST)

        if Location.objects.filter(latitude=latitude, longitude=longitude).exists():
            return JsonResponse({"error": "ERROR 409"}, status=status.HTTP_409_CONFLICT)

        return super().create(request)

    # update location
    def update(self, request, pk=None):
        if request.user.role == 'USER':
            return JsonResponse({'error': 'ERROR 403'}, status=status.HTTP_403_FORBIDDEN)

        try:
            latitude = float(request.data.get('latitude'))
            longitude = float(request.data.get('longitude'))
        except ValueError:
            return JsonResponse({"error": "ERROR 400"}, status=status.HTTP_400_BAD_REQUEST)

        if not (-90 <= latitude <= 90 and -180 <= longitude <= 180):
            return JsonResponse({"error": "ERROR 400"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            location = Location.objects.get(id=pk)
        except ObjectDoesNotExist:
            return JsonResponse({"error": "ERROR 404"}, status=status.HTTP_404_NOT_FOUND)

        if AnimalLocation.objects.filter(locationPointId=location.id).exists() or \
                Animal.objects.filter(chippingLocationId=location.id).exists():
            return JsonResponse({"error": "ERROR 400"}, status=status.HTTP_400_BAD_REQUEST)

        return super().update(request, pk=pk)

    # destroy location
    def destroy(self, request, pk):
        if request.user.role != 'ADMIN':
            return JsonResponse({'error': 'ERROR 403'}, status=status.HTTP_403_FORBIDDEN)

        data_check = check_error_400_404(pk)
        if isinstance(data_check, list):
            pk = data_check[0]
        else:
            return data_check

        try:
            location = Location.objects.get(id=pk)
        except ObjectDoesNotExist:
            return JsonResponse({"error": "ERROR 404"}, status=status.HTTP_404_NOT_FOUND)

        try:
            location.delete()
            return JsonResponse({}, status=status.HTTP_200_OK)
        except ProtectedError:
            return JsonResponse({"error": "ERROR 400"}, status=status.HTTP_400_BAD_REQUEST)


# view set for animal type functionality
class AnimalTypeViewSet(viewsets.ModelViewSet):
    authentication_classes = (Auth,)
    queryset = AnimalType.objects.all()
    permission_classes = [
        permissions.AllowAny
    ]
    serializer_class = AnimalTypeSerializer

    # create animal type
    def create(self, request):
        if request.user.role == 'USER':
            return JsonResponse({'error': 'ERROR 403'}, status=status.HTTP_403_FORBIDDEN)

        type_exists = AnimalType.objects.filter(type=request.data.get('type')).exists()
        if type_exists:
            return JsonResponse({"error": "ERROR 409"}, status=status.HTTP_409_CONFLICT)

        return super().create(request)

    # get animal type
    def retrieve(self, request, pk=None):
        data_check = check_error_400_404(pk)
        if isinstance(data_check, JsonResponse):
            return data_check

        return super().retrieve(request, pk)

    # update animal type
    def update(self, request, pk=None):
        if request.user.role == 'USER':
            return JsonResponse({'error': 'ERROR 403'}, status=status.HTTP_403_FORBIDDEN)

        data_check = check_error_400_404(pk)
        if isinstance(data_check, JsonResponse):
            return data_check

        type_exists = AnimalType.objects.filter(type=request.data.get('type')).exists()
        if type_exists:
            return JsonResponse({"error": "ERROR 409"}, status=status.HTTP_409_CONFLICT)

        return super().update(request, pk)

    # delete animal type
    def destroy(self, request, pk=None):
        if request.user.role != 'ADMIN':
            return JsonResponse({'error': 'ERROR 403'}, status=status.HTTP_403_FORBIDDEN)

        data_check = check_error_400_404(pk)
        if isinstance(data_check, list):
            pk = data_check[0]
        else:
            return data_check

        type_exists = AnimalType.objects.filter(id=pk).exists()
        if not type_exists:
            return JsonResponse({"error": "ERROR 404"}, status=status.HTTP_404_NOT_FOUND)

        has_animals = Animal.objects.filter(animalTypes__id=pk).exists()
        if has_animals:
            return JsonResponse({"error": "ERROR 400"}, status=status.HTTP_400_BAD_REQUEST)

        AnimalType.objects.filter(id=pk).delete()
        return JsonResponse({}, status=status.HTTP_200_OK)


# view set for area's functionality
class AreaViewSet(viewsets.ModelViewSet):
    authentication_classes = (Auth,)
    queryset = Area.objects.all()
    permission_classes = [
        permissions.AllowAny
    ]
    serializer_class = AreaSerializer

    # get area
    def retrieve(self, request, pk):
        data_check = check_error_400_404(pk)
        if isinstance(data_check, JsonResponse):
            return data_check
        return super().retrieve(request, pk)

    # delete area
    def destroy(self, request, pk):
        if request.user.role != 'ADMIN':
            return JsonResponse({'error': 'ERROR 403'}, status=status.HTTP_403_FORBIDDEN)

        data_check = check_error_400_404(pk)
        if isinstance(data_check, JsonResponse):
            return data_check

        area = Area.objects.filter(id=pk).first()
        if area is None:
            return JsonResponse({"error": "ERROR 404"}, status=status.HTTP_404_NOT_FOUND)

        area.delete()
        return JsonResponse({}, status=status.HTTP_200_OK)

    # add area
    def create(self, request):
        if request.user.role != 'ADMIN':
            return JsonResponse({'error': 'ERROR 403'}, status=status.HTTP_403_FORBIDDEN)
        if request.data.get('areaPoints') is None:
            return JsonResponse({"error": "ERROR 400"}, status=status.HTTP_400_BAD_REQUEST)
        list_points = request.data.get('areaPoints')
        if None in list_points:
            return JsonResponse({"error": "ERROR 400"}, status=status.HTTP_400_BAD_REQUEST)
        for point in list_points:
            if point['longitude'] is None or float(point['longitude']) < -180 or float(point['longitude']) > 180:
                return JsonResponse({"error": "ERROR 400"}, status=status.HTTP_400_BAD_REQUEST)
            elif point['latitude'] is None or float(point['latitude']) < -90 or float(point['latitude']) > 90:
                return JsonResponse({"error": "ERROR 400"}, status=status.HTTP_400_BAD_REQUEST)

        # Polygon and Point classes and methods with them are in polygons.py file
        areaPoints = Polygon(list_points)
        if not areaPoints.is_valid():
            return JsonResponse({"error": "not valid polygon"}, status=status.HTTP_400_BAD_REQUEST)
        polygons = [Polygon(area.areaPoints) for area in Area.objects.all()]
        if does_interact_with_old(polygons, areaPoints):
            return JsonResponse({"error": "interact old"}, status=status.HTTP_400_BAD_REQUEST)
        if is_inside_old(polygons, areaPoints):
            return JsonResponse({"error": "inside old"}, status=status.HTTP_400_BAD_REQUEST)
        if is_inside_new(polygons, areaPoints):
            return JsonResponse({"error": "inside new"}, status=status.HTTP_400_BAD_REQUEST)
        if is_identical_to_old(polygons, areaPoints):
            return JsonResponse({"error": "ERROR 409"}, status=status.HTTP_409_CONFLICT)
        if Area.objects.filter(name=request.data.get('name')).exists():
            return JsonResponse({"error": "ERROR 409"}, status=status.HTTP_409_CONFLICT)
        return super().create(request)

    # update area
    def update(self, request, pk):
        if request.user.role != 'ADMIN':
            return JsonResponse({'error': 'ERROR 403'}, status=status.HTTP_403_FORBIDDEN)
        data_check = check_error_400_404(pk)
        if isinstance(data_check, JsonResponse):
            return data_check
        if request.data.get('areaPoints') is None:
            return JsonResponse({"error": "ERROR 400"}, status=status.HTTP_400_BAD_REQUEST)
        list_ = request.data.get('areaPoints')
        if None in list_:
            return JsonResponse({"error": "ERROR 400"}, status=status.HTTP_400_BAD_REQUEST)
        for point in list_:
            if point['longitude'] is None or float(point['longitude']) < -180 or float(point['longitude']) > 180:
                return JsonResponse({"error": "ERROR 400"}, status=status.HTTP_400_BAD_REQUEST)
            elif point['latitude'] is None or float(point['latitude']) < -90 or float(point['latitude']) > 90:
                return JsonResponse({"error": "ERROR 400"}, status=status.HTTP_400_BAD_REQUEST)
        areaPoints = Polygon(list_)
        if not areaPoints.is_valid():
            return JsonResponse({"error": "not valid polygon"}, status=status.HTTP_400_BAD_REQUEST)
        polygons = [Polygon(area.areaPoints) for area in Area.objects.filter(~Q(id=pk))]
        if does_interact_with_old(polygons, areaPoints):
            return JsonResponse({"error": "interact old"}, status=status.HTTP_400_BAD_REQUEST)
        if is_inside_old(polygons, areaPoints):
            return JsonResponse({"error": "inside old"}, status=status.HTTP_400_BAD_REQUEST)
        if is_inside_new(polygons, areaPoints):
            return JsonResponse({"error": "inside new"}, status=status.HTTP_400_BAD_REQUEST)
        if is_identical_to_old(polygons, areaPoints):
            return JsonResponse({"error": "ERROR 409"}, status=status.HTTP_409_CONFLICT)
        if Area.objects.filter(name=request.data.get('name')).exists():
            return JsonResponse({"error": "ERROR 409"}, status=status.HTTP_409_CONFLICT)
        return super().update(request)

    # area analytics
    @action(methods=['get'], detail=True, url_path='analytics')
    def analytics(self, request, pk):
        if request.user is None:
            return JsonResponse({"error": "ERROR 401"}, status=status.HTTP_401_UNAUTHORIZED)

        data_check = check_error_400_404(pk)
        if isinstance(data_check, JsonResponse):
            return data_check

        start_date = request.query_params.get('startDate')
        end_date = request.query_params.get('endDate')
        if start_date:
            try:
                start_date = datetime.fromisoformat(start_date)
            except ValueError:
                return JsonResponse({"error": "ERROR 400"}, status=status.HTTP_400_BAD_REQUEST)
        if end_date:
            try:
                end_date = datetime.fromisoformat(end_date)
            except ValueError:
                return JsonResponse({"error": "ERROR 400"}, status=status.HTTP_400_BAD_REQUEST)
        if start_date and end_date and start_date >= end_date:
            return JsonResponse({"error": "ERROR 400"}, status=status.HTTP_400_BAD_REQUEST)

        area = get_object_or_404(Area, id=pk)
        area = Polygon(area.areaPoints)

        # init response
        response = {
            'totalQuantityAnimals': 0,
            'totalAnimalsArrived': 0,
            'totalAnimalsGone': 0,
            'animalsAnalytics': [

            ]
        }

        # init separate object for animalsAnalytics from response
        animalsAnalytics = {
            type_.type: {
                'animalType': type_.type,
                'animalTypeId': type_.id,
                'quantityAnimals': 0,
                'animalsArrived': 0,
                'animalsGone': 0,
            } for type_ in AnimalType.objects.all()
        }

        for animal in Animal.objects.all():
            point = Point(float(animal.chippingLocationId.longitude), float(animal.chippingLocationId.latitude))
            count_locations = len(animal.visitedLocations.values())
            chip_date = animal.chippingDateTime
            if count_locations != 0:
                next_location = animal.visitedLocations.all().first()
                next_location_date = next_location.dateTimeOfVisitLocationPoint
                next_point = Point(float(next_location.locationPointId.longitude),
                                   float(next_location.locationPointId.latitude))

            # in following if we are checking point where animal was chipped, so if after this animal hasn't visited any
            # points we make continue_ = False, so we don't go further with checking
            continue_ = True
            if is_point_inside_polygon(point, area):
                # animal was chipped inside the zone in or before the timeframe and hasn't visited anything after
                if end_date.timestamp() >= chip_date.timestamp() and count_locations == 0:
                    # so this animal is in this area
                    response['totalQuantityAnimals'] = response['totalQuantityAnimals'] + 1
                    for type_ in animal.animalTypes.all():
                        animalsAnalytics[type_.type]['quantityAnimals'] = animalsAnalytics[type_.type][
                                                                              'quantityAnimals'] + 1
                    continue_ = False

                # animal was chipped inside the timeframe but left the polygon after end_date
                elif start_date.timestamp() <= chip_date.timestamp() and count_locations != 0:
                    if end_date.timestamp() >= next_location_date.timestamp():

                        # check if animal left the polygon
                        if not is_point_inside_polygon(next_point, area):

                            # then animal is not in the zone, and it's gone
                            response['totalAnimalsGone'] = response['totalAnimalsGone'] + 1
                            for type_ in animal.animalTypes.all():
                                animalsAnalytics[type_.type]['animalsGone'] = animalsAnalytics[type_.type][
                                                                                  'animalsGone'] + 1

                            # as the animal left we skip all the future checks for it
                            continue_ = False

                        # if animal has only one visited location and didn't leave the area
                        elif count_locations == 1:
                            response['totalQuantityAnimals'] = response['totalQuantityAnimals'] + 1
                            for type_ in animal.animalTypes.all():
                                animalsAnalytics[type_.type]['quantityAnimals'] = animalsAnalytics[type_.type][
                                                                                      'quantityAnimals'] + 1

                            # as the animal has only one visited location we skip all the future checks for it
                            continue_ = False

            # going on to the next point after chipization if continue_
            if continue_:
                for location in animal.visitedLocations.all():
                    point = Point(float(location.locationPointId.longitude), float(location.locationPointId.latitude))
                    location_date = location.dateTimeOfVisitLocationPoint
                    try:
                        next_location = AnimalLocation.objects.get(id=find_next_prev(animal, location.id))
                    except ObjectDoesNotExist:
                        next_location = None
                    if is_point_inside_polygon(point, area):
                        # if entered polygon before timeframe and is last or left after timeframe
                        if start_date.timestamp() >= location_date.timestamp() and (
                                location == animal.visitedLocations.last() or
                                end_date.timestamp() <= next_location.dateTimeOfVisitLocationPoint.timestamp()):
                            # so this animal is in the zone
                            response['totalQuantityAnimals'] = response['totalQuantityAnimals'] + 1
                            for type_ in animal.animalTypes.all():
                                animalsAnalytics[type_.type]['quantityAnimals'] = animalsAnalytics[type_.type][
                                                                                      'quantityAnimals'] + 1
                            break

                        # if animal entered point and left to other inside the timeframe, and it's not it's last
                        elif start_date.timestamp() <= location_date.timestamp() and \
                                location != animal.visitedLocations.last():
                            if end_date.timestamp() >= next_location.dateTimeOfVisitLocationPoint.timestamp():
                                # animal arrived, was and left
                                response['totalQuantityAnimals'] = response['totalQuantityAnimals'] + 1
                                response['totalAnimalsArrived'] = response['totalAnimalsArrived'] + 1
                                response['totalAnimalsGone'] = response['totalAnimalsGone'] + 1
                                for type_ in animal.animalTypes.all():
                                    animalsAnalytics[type_.type]['quantityAnimals'] = animalsAnalytics[type_.type][
                                                                                          'quantityAnimals'] + 1
                                    animalsAnalytics[type_.type]['animalsArrived'] = animalsAnalytics[type_.type][
                                                                                         'animalsArrived'] + 1
                                    animalsAnalytics[type_.type]['animalsGone'] = animalsAnalytics[type_.type][
                                                                                      'animalsGone'] + 1
                                break

                        # if not all of it and visited inside the timeframe
                        if start_date.timestamp() <= location_date.timestamp():
                            # it arrived, was, but didn't leave
                            response['totalQuantityAnimals'] = response['totalQuantityAnimals'] + 1
                            response['totalAnimalsArrived'] = response['totalAnimalsArrived'] + 1
                            for type_ in animal.animalTypes.all():
                                animalsAnalytics[type_.type]['quantityAnimals'] = animalsAnalytics[type_.type][
                                                                                      'quantityAnimals'] + 1
                                animalsAnalytics[type_.type]['animalsArrived'] = animalsAnalytics[type_.type][
                                                                                     'animalsArrived'] + 1
                            break

                        # if not all of that, location is not last and left inside the timeframe
                        if location != animal.visitedLocations.last():
                            if end_date.timestamp() >= next_location.dateTimeOfVisitLocationPoint.timestamp():
                                # it was and left, but arrived before the timeframe
                                response['totalQuantityAnimals'] = response['totalQuantityAnimals'] + 1
                                response['totalAnimalsGone'] = response['totalAnimalsGone'] + 1
                                for type_ in animal.animalTypes:
                                    animalsAnalytics[type_.type]['quantityAnimals'] = animalsAnalytics[type_.type][
                                                                                          'quantityAnimals'] + 1
                                    animalsAnalytics[type_.type]['animalsGone'] = animalsAnalytics[type_.type][
                                                                                      'animalsGone'] + 1
                                break

        # loading info into response
        response['animalsAnalytics'] = [
            {
                'animalType': animalsAnalytics[type_]['animalType'],
                'animalTypeId': animalsAnalytics[type_]['animalTypeId'],
                'quantityAnimals': animalsAnalytics[type_]['quantityAnimals'],
                'animalsArrived': animalsAnalytics[type_]['animalsArrived'],
                'animalsGone': animalsAnalytics[type_]['animalsGone'],
            } for type_ in animalsAnalytics]
        k = 0
        for i in range(len(response['animalsAnalytics'])):
            if response['animalsAnalytics'][i - k]['quantityAnimals'] == 0 and \
                    response['animalsAnalytics'][i - k]['animalsArrived'] == 0 and \
                    response['animalsAnalytics'][i - k]['animalsGone'] == 0:
                del response['animalsAnalytics'][i - k]
                k += 1
        return JsonResponse(response, status=status.HTTP_200_OK)


# view set for animals functionality
class AnimalViewSet(viewsets.ModelViewSet):
    authentication_classes = (Auth,)
    queryset = Animal.objects.all()
    permission_classes = [
        permissions.AllowAny
    ]
    serializer_class = AnimalSerializer

    # get and search animals
    def retrieve(self, request, pk=None):
        if pk == "search":
            if request.query_params.get('startDateTime') is None:
                start_date_time = None
            else:
                try:
                    start_date_time = datetime.fromisoformat(request.query_params.get('startDateTime')[:-1])
                except ValueError:
                    return JsonResponse({"error": "ERROR 400"}, status=status.HTTP_400_BAD_REQUEST)
            if request.query_params.get('endDateTime') is None:
                end_date_time = None
            else:
                try:
                    end_date_time = datetime.fromisoformat(request.query_params.get('endDateTime')[:-1])
                except ValueError:
                    return JsonResponse({"error": "ERROR 400_"}, status=status.HTTP_400_BAD_REQUEST)

            data_check1 = check_error_400_404(self.request.query_params.get('chipperId'))
            if isinstance(data_check1, list):
                chipper_id = data_check1[0]
            else:
                chipper_id = None

            data_check2 = check_error_400_404(self.request.query_params.get('chippingLocationId'))
            if isinstance(data_check2, list):
                chipping_location_id = data_check2[0]
            else:
                chipping_location_id = None

            # life status, gender validation
            life_status = self.request.query_params.get('lifeStatus')
            gender = self.request.query_params.get('gender')
            if life_status not in ('ALIVE', 'DEAD', None) or gender not in ('MALE', 'FEMALE', 'OTHER', None):
                return JsonResponse({"error": "ERROR 400"}, status=status.HTTP_400_BAD_REQUEST)

            from_ = request.query_params.get('from', 0)
            size = request.query_params.get('size', 10)
            try:
                from_ = int(from_)
                size = int(size)
            except ValueError:
                return JsonResponse({"error": "ERROR 400"}, status=status.HTTP_400_BAD_REQUEST)

            if from_ < 0 or size <= 0:
                return JsonResponse({"error": "ERROR 400"}, status=status.HTTP_400_BAD_REQUEST)

            query = Animal.objects.all()
            if start_date_time:
                query = query.filter(chippingDateTime__gte=start_date_time)
            if end_date_time:
                query = query.filter(chippingDateTime__lte=end_date_time)
            if chipper_id:
                query = query.filter(chipperId_id=chipper_id)
            if chipping_location_id:
                query = query.filter(chippingLocationId_id=chipping_location_id)
            if gender:
                query = query.filter(gender=gender)
            if life_status:
                query = query.filter(lifeStatus=life_status)

            result = [to_dict(animal) for animal in query]
            return JsonResponse(result[from_:from_ + size], safe=False)

        data_check = check_error_400_404(pk)
        if isinstance(data_check, JsonResponse):
            return data_check

        return super(AnimalViewSet, self).retrieve(request, pk=None)

    # add animal
    def create(self, request):
        if request.user.role == 'USER':
            return JsonResponse({'error': 'ERROR 403'}, status=status.HTTP_403_FORBIDDEN)

        data_check = check_error_400_404(request.data.get('chipperId'), request.data.get('chippingLocationId'))
        if isinstance(data_check, list):
            chipper_id, chipping_location_id = data_check
        else:
            return data_check

        if not Account.objects.filter(id=chipper_id).exists() or not Location.objects.filter(
                id=chipping_location_id).exists():
            return JsonResponse({"error": "ERROR 404"}, status=status.HTTP_404_NOT_FOUND)

        weight = request.data.get('weight')
        length = request.data.get('length')
        height = request.data.get('height')

        if weight is None or length is None or height is None:
            return JsonResponse({"error": "ERROR 400"}, status=status.HTTP_400_BAD_REQUEST)

        if weight <= 0 or length <= 0 or height <= 0:
            return JsonResponse({"error": "ERROR 400"}, status=status.HTTP_400_BAD_REQUEST)

        animal_types = request.data.get('animalTypes')

        if animal_types is not None:
            for animal_type in animal_types:
                if animal_type is not None and not AnimalType.objects.filter(id=animal_type).exists():
                    return JsonResponse({"error": "ERROR 404"}, status=status.HTTP_404_NOT_FOUND)

        return super(AnimalViewSet, self).create(request)

    # update animal
    def update(self, request, pk):
        if request.user.role == 'USER':
            return JsonResponse({'error': 'ERROR 403'}, status=status.HTTP_403_FORBIDDEN)

        data_check = check_error_400_404(pk, request.data.get('chipperId'), request.data.get('chippingLocationId'))
        if isinstance(data_check, list):
            pk, chipper_id, chipping_location_id = data_check
        else:
            return data_check

        animal = get_object_or_404(Animal, id=pk)

        weight = request.data.get('weight')
        length = request.data.get('length')
        height = request.data.get('height')
        if weight is None or length is None or height is None:
            return JsonResponse({'error': 'ERROR 400'}, status=status.HTTP_400_BAD_REQUEST)
        if weight <= 0 or length <= 0 or height <= 0:
            return JsonResponse({'error': 'ERROR 400'}, status=status.HTTP_400_BAD_REQUEST)

        if request.data.get('lifeStatus'):
            life_status = request.data.get('lifeStatus')
            visited_locations = animal.visitedLocations.all()
            if life_status == 'ALIVE' and animal.lifeStatus == 'DEAD':
                return JsonResponse({"error": "ERROR 400"}, status=status.HTTP_400_BAD_REQUEST)
            if len(animal.visitedLocations.values()) != 0 and \
                    chipping_location_id == visited_locations.first().locationPointId_id:
                return JsonResponse({"error": "ERROR 400"}, status=status.HTTP_400_BAD_REQUEST)
            if not Account.objects.filter(id=chipper_id).exists():
                return JsonResponse({"error": "ERROR 404"}, status=status.HTTP_404_NOT_FOUND)
            if not Location.objects.filter(id=chipping_location_id).exists():
                return JsonResponse({"error": "ERROR 404"}, status=status.HTTP_404_NOT_FOUND)

        request.data['animalTypes'] = list(Animal.objects.get(id=pk).animalTypes.all().values_list('id', flat=True))
        return super(AnimalViewSet, self).update(request, pk)

    # delete animal
    def destroy(self, request, pk):
        if request.user.role != 'ADMIN':
            return JsonResponse({'error': 'ERROR 403'}, status=status.HTTP_403_FORBIDDEN)

        data_check = check_error_400_404(pk)
        if isinstance(data_check, list):
            pk = data_check[0]
        else:
            return data_check

        animal = get_object_or_404(Animal, id=pk)

        if len(animal.visitedLocations.values()) > 0:
            return JsonResponse({"error": "ERROR 400"}, status=status.HTTP_400_BAD_REQUEST)

        animal.delete()
        return JsonResponse({}, status=200)

    @action(methods=['delete', 'post'], detail=True, url_path='types/(?P<typeId>[^/.]+)')
    def type_post_delete(self, request, pk, typeId):
        if request.user.role == 'USER':
            return JsonResponse({'error': 'ERROR 403'}, status=status.HTTP_403_FORBIDDEN)

        data_check = check_error_400_404(pk, typeId)
        if isinstance(data_check, list):
            pk, typeId = data_check
        else:
            return data_check

        animal = get_object_or_404(Animal, id=pk)
        animal_type = get_object_or_404(AnimalType, id=typeId)

        # delete type from animal
        if request.method == 'DELETE':
            if not animal.animalTypes.filter(id=typeId).exists():
                return JsonResponse({"error": "ERROR 404"}, status=status.HTTP_404_NOT_FOUND)

            if len(animal.animalTypes.values('id')) == 1 and animal.animalTypes.values('id')[0] == {'id': typeId}:
                return JsonResponse({"error": "ERROR 400"}, status=status.HTTP_400_BAD_REQUEST)

            animal.animalTypes.remove(animal_type)
            queryset = super().get_queryset().get(id=pk)
            serializer = AnimalSerializer(queryset)
            return JsonResponse(serializer.data, safe=False, status=status.HTTP_200_OK)

        # add type to animal
        elif request.method == 'POST':
            if animal.animalTypes.filter(id=typeId).exists():
                return JsonResponse({"error": "ERROR 409"}, status=status.HTTP_409_CONFLICT)

            animal.animalTypes.add(animal_type)
            queryset = super().get_queryset().get(id=pk)
            serializer = AnimalSerializer(queryset)
            return JsonResponse(serializer.data, status=status.HTTP_201_CREATED)

    @action(methods=['put'], detail=True, url_path='types')
    def update_types(self, request, pk):
        if request.user.role == 'USER':
            return JsonResponse({'error': 'ERROR 403'}, status=status.HTTP_403_FORBIDDEN)

        data_check = check_error_400_404(pk, request.data.get('oldTypeId'), request.data.get('newTypeId'))
        if isinstance(data_check, list):
            pk, old_type_id, new_type_id = data_check
        else:
            return data_check

        animal = get_object_or_404(Animal, id=pk)
        old_type = get_object_or_404(AnimalType, id=old_type_id)
        new_type = get_object_or_404(AnimalType, id=new_type_id)
        if not animal.animalTypes.filter(id=old_type_id).exists():
            return JsonResponse({"error": "ERROR 404"}, status=status.HTTP_404_NOT_FOUND)
        if animal.animalTypes.filter(id=new_type_id).exists():
            return JsonResponse({"error": "ERROR 409"}, status=status.HTTP_409_CONFLICT)

        animal.animalTypes.remove(old_type)
        animal.animalTypes.add(new_type)
        queryset = super().get_queryset().get(id=pk)
        serializer = AnimalSerializer(queryset)
        return JsonResponse(serializer.data, safe=False, status=status.HTTP_200_OK)

    @action(methods=['get', 'put'], detail=True, url_path='locations')
    def get_edit_locations(self, request, pk):
        data_check = check_error_400_404(pk)
        if isinstance(data_check, list):
            animalId = data_check[0]
        else:
            return data_check

        animal = get_object_or_404(Animal, id=animalId)

        # get animal locations
        if request.method == 'GET':

            if self.request.query_params.get('startDateTime') is None:
                start_date_time = None
            else:
                try:
                    start_date_time = datetime.fromisoformat(self.request.query_params.get('startDateTime')[:-1])
                except ValueError:
                    return JsonResponse({"error": "ERROR 400"}, status=status.HTTP_400_BAD_REQUEST)
            if self.request.query_params.get('endDateTime') is None:
                end_date_time = None
            else:
                try:
                    end_date_time = datetime.fromisoformat(self.request.query_params.get('endDateTime')[:-1])
                except ValueError:
                    return JsonResponse({"error": "ERROR 400"}, status=status.HTTP_400_BAD_REQUEST)

            from_ = int(self.request.query_params.get('from', 0))
            size = int(self.request.query_params.get('size', 10))

            if from_ < 0 or size <= 0:
                return JsonResponse({"error": "ERROR 400"}, status=status.HTTP_400_BAD_REQUEST)

            query = animal.visitedLocations.all()

            if start_date_time:
                query = query.filter(dateTimeOfVisitLocationPoint__gte=start_date_time)
            if end_date_time:
                query = query.filter(dateTimeOfVisitLocationPoint__lte=end_date_time)

            result = [to_dict(location) for location in query]
            return JsonResponse(result[from_:from_ + size], safe=False)

        # update animal locations
        elif request.method == 'PUT':
            if request.user.role == 'USER':
                return JsonResponse({'error': 'ERROR 403'}, status=status.HTTP_403_FORBIDDEN)

            data_check = check_error_400_404(request.data.get('visitedLocationPointId'),
                                             request.data.get('locationPointId'))
            if isinstance(data_check, list):
                visitedLocationPointId, locationPointId = data_check
            else:
                return data_check

            animal_location = get_object_or_404(AnimalLocation, id=visitedLocationPointId)
            location_point = get_object_or_404(Location, id=locationPointId)

            if not animal.visitedLocations.filter(id=visitedLocationPointId).exists():
                return JsonResponse({"error": "ERROR 404"}, status=status.HTTP_404_NOT_FOUND)

            if animal_location == animal.visitedLocations.first() and animal.chippingLocationId.id == locationPointId:
                return JsonResponse({"error": "ERROR 400"}, status=status.HTTP_400_BAD_REQUEST)

            if animal_location.locationPointId.id == locationPointId:
                return JsonResponse({"error": "ERROR 400"}, status=status.HTTP_400_BAD_REQUEST)

            # if equal to previous or future points
            if animal_location == animal.visitedLocations.first() and animal_location == animal.visitedLocations.last():
                pass
            elif animal_location == animal.visitedLocations.first():
                if find_next_prev(animal, visitedLocationPointId) == locationPointId:
                    return JsonResponse({"error": "ERROR 400"}, status=status.HTTP_400_BAD_REQUEST)
            elif animal_location == animal.visitedLocations.last():
                if find_next_prev(animal, visitedLocationPointId, next=False) == locationPointId:
                    return JsonResponse({"error": "ERROR 400"}, status=status.HTTP_400_BAD_REQUEST)
            elif find_next_prev(animal, visitedLocationPointId, next=False) == locationPointId or \
                    find_next_prev(animal, visitedLocationPointId) == locationPointId:
                return JsonResponse({"error": "ERROR 400"}, safe=False, status=status.HTTP_400_BAD_REQUEST)

            animal_location.locationPointId = location_point
            animal_location.save()

            return JsonResponse(to_dict(animal_location), status=status.HTTP_200_OK)

    @action(methods=['post', 'delete'], detail=True, url_path='locations/(?P<pointId>[^/.]+)')
    def add_delete_locations(self, request, pk, pointId):

        data_check = check_error_400_404(pk, pointId)
        if isinstance(data_check, list):
            animalId, point = data_check
        else:
            return data_check

        animal = get_object_or_404(Animal, id=animalId)

        # add location for animal
        if request.method == 'POST':
            if request.user.role == 'USER':
                return JsonResponse({'error': 'ERROR 403'}, status=status.HTTP_403_FORBIDDEN)

            location_point = get_object_or_404(Location, id=point)

            if animal.lifeStatus == 'DEAD':
                return JsonResponse({"error": "ERROR 400"}, status=status.HTTP_400_BAD_REQUEST)

            if len(animal.visitedLocations.values()) == 0 and animal.chippingLocationId == location_point:
                return JsonResponse({"error": "ERROR 400"}, status=status.HTTP_400_BAD_REQUEST)

            if location_point == animal.visitedLocations.last():
                return JsonResponse({"error": "ERROR 400"}, status=status.HTTP_400_BAD_REQUEST)

            animal_location = AnimalLocation.objects.create(dateTimeOfVisitLocationPoint=datetime.now(),
                                                            locationPointId=location_point)
            animal.visitedLocations.add(animal_location)
            return JsonResponse(to_dict(animal_location), status=status.HTTP_201_CREATED)

        # remove location from animal
        if request.method == 'DELETE':
            if request.user.role != 'ADMIN':
                return JsonResponse({'error': 'ERROR 403'}, status=status.HTTP_403_FORBIDDEN)

            animal_location = get_object_or_404(AnimalLocation, id=point)

            if not animal.visitedLocations.filter(id=point).exists():
                return JsonResponse({"error": "ERROR 404"}, status=status.HTTP_404_NOT_FOUND)

            animal_location.delete()

            # if second point after deleted is equal to chipping than delete
            while len(animal.visitedLocations.values()) > 0:
                if animal.visitedLocations.first() == animal.chippingLocationId.id:
                    AnimalLocation.objects.get(id=animal.visitedLocations.first().id).delete()
                else:
                    return JsonResponse({}, status=status.HTTP_200_OK)

            return JsonResponse({}, status=status.HTTP_200_OK)
