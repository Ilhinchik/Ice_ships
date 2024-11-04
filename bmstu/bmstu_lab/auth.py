from rest_framework import permissions
from rest_framework.authtoken.admin import User

from .redis import session_storage

from rest_framework import authentication
from rest_framework import exceptions


class AuthBySessionID(authentication.BaseAuthentication):
    def authenticate(self, request):
        print(f"Received cookies: {request.COOKIES}")
        
        session_id = request.COOKIES.get("session_id")
        print(f"Extracted session_id: {session_id}")  # Add this line
        
        if session_id is None:
            raise exceptions.AuthenticationFailed('No session_id')

        try:
            username = session_storage.get(session_id).decode('utf-8')
            print(f"Username retrieved: {username}")
        except Exception as e:
            print(f"Session ID error: {str(e)}")  # Log the error
            raise exceptions.AuthenticationFailed('session_id not found')

        try:
            user = User.objects.get(username=username)
            print(f"Authenticated user: {user}")  # Log authenticated user
        except User.DoesNotExist:
            print(f"User not found for username: {username}")  # Log if user does not exist
            raise exceptions.AuthenticationFailed('No such user')

        return user, None


class AuthBySessionIDIfExists(authentication.BaseAuthentication):
    def authenticate(self, request):
        session_id = request.COOKIES.get("session_id")
        if session_id is None:
            return None, None

        try:
            username = session_storage.get(session_id).decode('utf-8')
        except Exception as e:
            return None, None

        user = User.objects.get(username=username)
        return user, None


class IsAuth(permissions.BasePermission):
    def has_permission(self, request, view):
        session_id = request.COOKIES.get("session_id")
        if session_id is None:
            return False
        try:
            session_storage.get(session_id).decode('utf-8')
        except Exception as e:
            return False
        return True


class IsManagerAuth(permissions.BasePermission):
    def has_permission(self, request, view):
        session_id = request.COOKIES.get("session_id")
        if session_id is None:
            return False
        try:
            username = session_storage.get(session_id).decode('utf-8')
        except Exception as e:
            return False

        user = User.objects.filter(username=username).first()
        if user is None:
            return False

        return user.is_staff