import base64

from .models import Account
from rest_framework import authentication
from rest_framework import exceptions


def authProcess(request, noAuth=True):
    # looking for basic auth info
    if 'HTTP_AUTHORIZATION' in request.META:
        auth = request.META['HTTP_AUTHORIZATION'].split()
        if len(auth) == 2 and auth[0].lower() == "basic":
            email, password = str(base64.b64decode(auth[1])).split(':')
            email = email[2::]
            password = password[:-1]
        else:
            raise exceptions.AuthenticationFailed('Invalid user')
    else:

        # if authentication is not necessary (for example - GET)
        if noAuth:
            return (None, None)
        else:
            raise exceptions.AuthenticationFailed('Invalid user')

    try:
        # try to auth with basic auth info
        user = Account.objects.get(email=email)
        if user.password != password:
            raise exceptions.AuthenticationFailed('Invalid password')
    except Account.DoesNotExist:
        raise exceptions.AuthenticationFailed('No such user')

    # authentication
    return (user, None)


class AuthAccount(authentication.BaseAuthentication):
    def authenticate(self, request):
        if request.method == 'GET' or request.method == 'POST':
            return authProcess(request)
        else:
            try:
                return authProcess(request, noAuth=False)
            except:
                raise exceptions.AuthenticationFailed('Auth error')

    def authenticate_header(self, request):
        return '{"username" : <username>, "password" : <password>}'


class Auth(authentication.BaseAuthentication):
    def authenticate(self, request):
        if request.method == 'GET':
            return authProcess(request)
        else:
            try:
                return authProcess(request, noAuth=False)
            except:
                raise exceptions.AuthenticationFailed('Auth error')

    def authenticate_header(self, request):
        return '{"username" : <username>, "password" : <password>}'


# for registration, we need to know that the user is not authenticated
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

                # password is incorrect - user not auth
                if user.password != password:
                    return (None, None)

            except Account.DoesNotExist:
                return (None, None)

        except:
            return (None, None)

        # successfull auth is an exception in this case =)
        raise exceptions.AuthenticationFailed('Authenticated user')
