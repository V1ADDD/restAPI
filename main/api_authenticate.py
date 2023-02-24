import base64

from .models import Account
from rest_framework import authentication
from rest_framework import exceptions


class Auth(authentication.BaseAuthentication):
    def authenticate(self, request):
        if request.method == 'GET' or request.method == 'POST':
            if 'HTTP_AUTHORIZATION' in request.META:
                auth = request.META['HTTP_AUTHORIZATION'].split()
                if len(auth) == 2 and auth[0].lower() == "basic":
                    email, password = str(base64.b64decode(auth[1])).split(':')
                    email = email[2::]
                    password = password[:-1]
                else:
                    raise exceptions.AuthenticationFailed('Invalid user')
            else:
                return (None, None)
            try:
                user = Account.objects.get(email=email)
                if user.password != password:
                    raise exceptions.AuthenticationFailed('Invalid password')
            except Account.DoesNotExist:
                raise exceptions.AuthenticationFailed('No such user')

            return (user, None)
        else:
            try:
                if 'HTTP_AUTHORIZATION' in request.META:
                    auth = request.META['HTTP_AUTHORIZATION'].split()
                    if len(auth) == 2 and auth[0].lower() == "basic":
                        email, password = str(base64.b64decode(auth[1])).split(':')
                        email = email[2::]
                        password = password[:-1]
                    else:
                        raise exceptions.AuthenticationFailed('Invalid user')
                else:
                    raise exceptions.AuthenticationFailed('Invalid user')
                try:
                    user = Account.objects.get(email=email)
                    if user.password != password:
                        raise exceptions.AuthenticationFailed('Invalid password')
                except Account.DoesNotExist:
                    raise exceptions.AuthenticationFailed('No such user')
            except:
                raise exceptions.AuthenticationFailed('Auth error')

            return (user, None)

    def authenticate_header(self, request):
        return '{"username" : <username>, "password" : <password>}'


class NotAuth(authentication.BaseAuthentication):
    def authenticate(self, request):
        try:
            if 'HTTP_AUTHORIZATION' in request.META:
                auth = request.META['HTTP_AUTHORIZATION'].split()
                if len(auth) == 2 and auth[0].lower() == "basic":
                    email, password = str(base64.b64decode(auth[1])).split(':')
                    email = email[2::]
                    password = password[:-1]
            try:
                user = Account.objects.get(email=email)
                if user.password != password:
                    return (None, None)
            except Account.DoesNotExist:
                return (None, None)

            raise exceptions.AuthenticationFailed('Authenticated user')
        except:
            return (None, None)
