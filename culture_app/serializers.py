from rest_framework import serializers
from django.core.validators import MinLengthValidator
from django.core.validators import EmailValidator
from datetime import datetime
from .models import User, Event, Category, Location, Favorite, Review

class UserSerializator(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, validators=[MinLengthValidator(8)])

    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'password', 'bio']

    def validate_username(self, value):
        if value.isalnum() == False:
            raise serializers.ValidationError("В имени пользователя должны быть только буквы и цифры.")
        return value

    def validate_email(self, value):        
        validator = EmailValidator()
        validator(value)
        return value

class EventSerializator(serializers.ModelSerializer):
    category = serializers.PrimaryKeyRelatedField(queryset=Category.objects.all())
    location = serializers.PrimaryKeyRelatedField(queryset=Location.objects.all())
    date = serializers.DateTimeField(format='%Y-%m-%dT%H:%M:%SZ', input_formats=['%Y-%m-%dT%H:%M:%SZ'])

    class Meta:
        model = Event
        fields = ['id', 'title', 'description', 'date', 'category', 'location']

    def validate_title(self, value):
        if len(value) == 0:
            raise serializers.ValidationError("Нужно ввести заголовок!")
        return value

    def validate_date(self, value):
        current_year = datetime.now().year
        if value.year < current_year:
            raise serializers.ValidationError("Дата должна быть в будущем или текущем году!")
        return value

class CategorySerializator(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ['id', 'name']

    def validate_name(self, value):
        if len(value) < 3:
            raise serializers.ValidationError("Имя категории слишком короткое!")
        return value

class LocationSerializator(serializers.ModelSerializer):
    class Meta:
        model = Location
        fields = ['id', 'name', 'address']

    def validate_name(self, value):
        if value == '':
            raise serializers.ValidationError("Имя локации обязательно!")
        return value

class FavoriteSerializator(serializers.ModelSerializer):
    event = serializers.PrimaryKeyRelatedField(queryset=Event.objects.all())

    class Meta:
        model = Favorite
        fields = ['id', 'user', 'event']

    def create(self, validated_data):
        user = validated_data['user']
        event = validated_data['event']
        if Favorite.objects.filter(user=user, event=event).exists():
            raise serializers.ValidationError("Это событие уже добавленно в избранном!")
        return Favorite.objects.create(**validated_data)

class ReviewSerializator(serializers.ModelSerializer):
   
    event = serializers.PrimaryKeyRelatedField(queryset=Event.objects.all())

    class Meta:
        model = Review
        fields = ['id', 'user', 'event', 'text', 'rating', 'created_at']
        read_only_fields = ['created_at']
        
    def create(self, validated_data):
        validated_data['user'] = self.context['request'].user
        return super().create(validated_data)
    
    def validate_rating(self, value):
        if value < 1 or value > 5:
            raise serializers.ValidationError("Рейтинг только от 1 до 5!")
        return value

    def validate_text(self, value):
        if len(value) < 5:
            raise serializers.ValidationError("Отзыв слишком короткий, напишите больше :)")
        return value