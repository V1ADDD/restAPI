from rest_framework import routers
from .api import AccountViewSet, LocationViewSet, AnimalTypeViewSet

router = routers.DefaultRouter()
router.register('accounts', AccountViewSet, 'accounts')
router.register('locations', LocationViewSet, 'locations')
router.register('animals/types', AnimalTypeViewSet, 'animaltype')

urlpatterns = router.urls
