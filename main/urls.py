from rest_framework import routers
from .api import AccountViewSet, LocationViewSet, AnimalTypeViewSet, AnimalViewSet, AreaViewSet

router = routers.DefaultRouter(trailing_slash=False)
router.register('accounts', AccountViewSet, 'accounts')
router.register('locations', LocationViewSet, 'locations')
router.register('animals/types', AnimalTypeViewSet, 'animaltype')
router.register('animals', AnimalViewSet, 'animals')
router.register('areas', AreaViewSet, 'areas')
urlpatterns = router.urls
