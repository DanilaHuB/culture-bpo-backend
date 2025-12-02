from django.urls import path
from . import views

urlpatterns = [
    path('register/', views.UserRegisterView.as_view(), name='register'),
    path('login/', views.UserLoginView.as_view(), name='login'),
    path('logout/', views.UserLogoutView.as_view(), name='logout'),
    path('profile/', views.UserProfileView.as_view(), name='profile'),

    path('events/', views.EventsListView.as_view(), name='event-list'),
    path('events/<int:pk>/', views.EventDetailsView.as_view(), name='event-detail'),
    path('events/search/', views.EventsSearchView.as_view(), name='event-search'),

    path('categories/', views.CategoriesListView.as_view(), name='category-list'),
    path('locations/', views.LocationsListView.as_view(), name='location-list'),

    path('favorites/', views.FavoritesListView.as_view(), name='favorite-list'),
    path('favorites/add/', views.AddToFavoritesView.as_view(), name='add-favorite'),
    path('favorites/remove/<int:event_id>/', views.RemoveFromFavoritesView.as_view(), name='remove-favorite'),

    path('events/create/', views.CreateEventView.as_view(), name='create-event'),
    path('events/update/<int:pk>/', views.EventUpdateView.as_view(), name='update-event'),

    path('reviews/<int:event_id>/', views.ReviewListView.as_view(), name='review-list'),
    path('reviews/create/', views.CreateReviewView.as_view(), name='create-review'),
    path('reviews/update/<int:pk>/', views.UpdateReviewView.as_view(), name='update-review'),
    path('reviews/delete/<int:pk>/', views.DeleteReviewView.as_view(), name='delete-review'),
]