from rest_framework import routers
from django.urls import path
from .api import AccountViewSet, LocationViewSet, AnimalTypeViewSet, AnimalViewSet, RegistrationView

router = routers.DefaultRouter(trailing_slash=False)
router.register('accounts', AccountViewSet, 'accounts')
router.register('locations', LocationViewSet, 'locations')
router.register('animals/types', AnimalTypeViewSet, 'animaltype')
router.register('animals', AnimalViewSet, 'animals')
router.urls.append(path('registration', RegistrationView, name='registration'))
urlpatterns = router.urls
