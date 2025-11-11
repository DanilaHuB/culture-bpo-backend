import logging
from django_filters.rest_framework import DjangoFilterBackend
from django.contrib.auth import authenticate, get_user_model
from rest_framework import status, permissions, generics
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError

from .models import Event, Category, Location, Favorite, Review
from .serializers import (
    UserSerializator,      
    EventSerializator,     
    CategorySerializator,
    LocationSerializator,
    FavoriteSerializator,
    ReviewSerializator,
)

logger = logging.getLogger(__name__)
User = get_user_model()


class IsEventOrganizer(permissions.BasePermission):

    # !организатор события не всегда админ, у юзера есть флаг is_organizer
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and request.user.is_organizer)


class UserRegisterView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = UserSerializator(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            user.set_password(serializer.validated_data['пароль'])
            user.save()

            logger.info(f"Пользователь зарегистрирован: {user.username}")

            return Response(
                {"ok": True, "пользовтаель": UserSerializator(user).data},
                status=status.HTTP_201_CREATED
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class UserLoginView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        username = request.data.get('username') or request.data.get('login')
        password = request.data.get('password')

        if not username or not password:
            return Response({"error": "Введите логин и пароль"}, status=status.HTTP_400_BAD_REQUEST)

        user = authenticate(username=username, password=password)
        if not user:
            return Response({"error": "Неверные данные"}, status=status.HTTP_401_UNAUTHORIZED)

        refresh = RefreshToken.for_user(user)
        return Response({"refresh": str(refresh), "access": str(refresh.access_token)})


class FavoritesListView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    MAX_FAVORITES = 100

    def get(self, request):
        favorites = Favorite.objects.select_related("event").filter(user=request.user)
        return Response(FavoriteSerializator(favorites, many=True).data)

    def post(self, request):
        event_id = request.data.get("event_id")
        if not event_id:
            return Response({"error": "Нужен event_id"}, status=status.HTTP_400_BAD_REQUEST)

        if Favorite.objects.filter(user=request.user).count() >= self.MAX_FAVORITES:
            return Response({"error": "Лимит избранного исчерпан"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            event = Event.objects.get(id=event_id)
        except Event.DoesNotExist:
            return Response({"error": "Событие не найдено"}, status=status.HTTP_404_NOT_FOUND)

        Favorite.objects.get_or_create(user=request.user, event=event)
        return Response({"ok": True}, status=status.HTTP_201_CREATED)


class CreateReviewView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        # Делаю один отзыв на конкретное событие от пользвт.
        event_id = request.data.get("event")
        if Review.objects.filter(user=request.user, event_id=event_id).exists():
            return Response({"error": "Отзыв уже оставлен"}, status=status.HTTP_400_BAD_REQUEST)

        serializer = ReviewSerializator(data=request.data)
        if serializer.is_valid():
            review = serializer.save(user=request.user)
            return Response(ReviewSerializator(review).data, status=status.HTTP_201_CREATED)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class CreateEventView(generics.CreateAPIView):
    serializer_class = EventSerializator
    permission_classes = [IsEventOrganizer]

class UserLogoutView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        try:
            refresh_token = request.data.get("refresh")
            if not refresh_token:
                return Response({"error": "Токен не передан"}, status=status.HTTP_400_BAD_REQUEST)
            token = RefreshToken(refresh_token)
            token.blacklist()
            return Response({"ok": True}, status=status.HTTP_205_RESET_CONTENT)
        except (InvalidToken, TokenError):
            return Response({"error": "Неверный токен"}, status=status.HTTP_400_BAD_REQUEST)


class UserProfileView(generics.RetrieveUpdateAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = UserSerializator

    def get_object(self):
        return self.request.user


class EventsListView(generics.ListAPIView):
    queryset = Event.objects.all()
    serializer_class = EventSerializator


class EventDetailsView(generics.RetrieveAPIView):
    queryset = Event.objects.all()
    serializer_class = EventSerializator


class EventsSearchView(generics.ListAPIView):
    queryset = Event.objects.all()
    serializer_class = EventSerializator
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['title', 'date', 'category__name', 'location__name']


class CategoriesListView(generics.ListAPIView):
    queryset = Category.objects.all()
    serializer_class = CategorySerializator


class LocationsListView(generics.ListAPIView):
    queryset = Location.objects.all()
    serializer_class = LocationSerializator


class AddToFavoritesView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        event_id = request.data.get("event_id")
        if not event_id:
            return Response({"error": "Нужен event_id"}, status=status.HTTP_400_BAD_REQUEST)
        try:
            event = Event.objects.get(id=event_id)
        except Event.DoesNotExist:
            return Response({"error": "Событие не найдено"}, status=status.HTTP_404_NOT_FOUND)
        Favorite.objects.get_or_create(user=request.user, event=event)
        return Response({"ok": True}, status=status.HTTP_201_CREATED)


class RemoveFromFavoritesView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def delete(self, request, event_id):
        deleted, _ = Favorite.objects.filter(user=request.user, event_id=event_id).delete()
        if deleted:
            return Response({"ok": True}, status=status.HTTP_204_NO_CONTENT)
        return Response({"error": "Не в избранном"}, status=status.HTTP_400_BAD_REQUEST)


class EventUpdateView(APIView):
    permission_classes = [IsEventOrganizer]

    def put(self, request, pk):
        try:
            event = Event.objects.get(pk=pk)
        except Event.DoesNotExist:
            return Response({"error": "Событие не найдено"}, status=status.HTTP_404_NOT_FOUND)
        if event.organizer != request.user:
            return Response({"error": "Нет прав"}, status=status.HTTP_403_FORBIDDEN)
        serializer = EventSerializator(event, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class ReviewListView(generics.ListAPIView):
    serializer_class = ReviewSerializator

    def get_queryset(self):
        event_id = self.kwargs['event_id']
        return Review.objects.filter(event_id=event_id)


class UpdateReviewView(generics.UpdateAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = ReviewSerializator

    def get_object(self):
        obj = generics.get_object_or_404(Review, pk=self.kwargs['pk'], user=self.request.user)
        return obj


class DeleteReviewView(generics.DestroyAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = ReviewSerializator

    def get_object(self):
        obj = generics.get_object_or_404(Review, pk=self.kwargs['pk'], user=self.request.user)
        return obj
