from django.db import models
from django.contrib.auth.models import AbstractUser
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone
from django.utils.text import slugify


class User(AbstractUser):
    bio = models.TextField(blank=True)
    birth_date = models.DateField(null=True, blank=True)
    # TODO: добавить поле avatar

    def __str__(self):
        return self.username


class Category(models.Model):
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(unique=True, blank=True)

    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(self.name)
            slug = base_slug
            counter = 1
            while Category.objects.filter(slug=slug).exists():
                slug = f"{base_slug}-{counter}"
                counter += 1
            self.slug = slug
        super().save(*args, **kwargs)


class Location(models.Model):
    name = models.CharField(max_length=150)
    city = models.CharField(max_length=80, default="Москва")
    address = models.TextField(blank=True)

    def __str__(self):
        return f"{self.name} ({self.city})"


class EventManager(models.Manager):
    def published(self):             
        return self.filter(status="published", date__gte=timezone.now())                    

    def upcoming(self):         
        now = timezone.now()      
        return self.filter(date__gte=now).order_by("date")


class Event(models.Model):
    STATUS_CHOICES = (
        ("draft", "Черновик"),
        ("published", "Опубликовано"),
        ("cancelled", "Отменено"),
    )

    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    date = models.DateTimeField()
    is_online = models.BooleanField(default=False)
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True)
    location = models.ForeignKey(Location, on_delete=models.SET_NULL, null=True, blank=True)
    organizer = models.ForeignKey(User, on_delete=models.CASCADE, related_name="events")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="draft")
    created = models.DateTimeField(auto_now_add=True)

    objects = EventManager()

    class Meta:
        ordering = ["-date"]
        constraints = [
            models.UniqueConstraint(
                fields=["title", "date", "location"],   
                name="uniq_event_title_date_location"
            ),
            models.UniqueConstraint(
                fields=["title", "date"],
                condition=models.Q(is_online=True), 
                name="uniq_online_event_title_date"
            ),
        ]
        indexes = [
            models.Index(fields=["title", "date"]),
            models.Index(fields=["date"]),
        ]

    def __str__(self):
        return f"{self.title} [{self.date:%d.%m}]"

    def clean(self):
        if not self.is_online and not self.location:
            raise models.ValidationError("Оффлайн-событие должно иметь локацию!")
        if self.date < timezone.now() and self.status != "cancelled":
            raise models.ValidationError("Ошибка! Дата события не может быть в прошлом!")

    def save(self, *args, **kwargs):       
        if self.status == "draft" and self.date < timezone.now():
            self.date = timezone.now() + timezone.timedelta(days=7)
        super().save(*args, **kwargs)

    @property    
    def avg_rating(self):
        r = self.reviews.aggregate(models.Avg("rating"))
        return round(r["rating__avg"], 2) if r["rating__avg"] else None

class Favorite(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    event = models.ForeignKey(Event, on_delete=models.CASCADE)
    added_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("user", "event")

    def __str__(self):
        return f"{self.user} {self.event.title}"


class Review(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name="reviews")
    text = models.TextField()
    rating = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)]
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.user.username}: {self.rating}/5"

    def clean(self):
        txt = self.text.strip()
        if len(txt) < 8:
            raise models.ValidationError("Отзыв слишком короткий (мин. 8 символов)!")
        if Review.objects.filter(user=self.user, event=self.event).exclude(id=self.id).exists():
            raise models.ValidationError("Вы уже писали отзыв для этого события!")
