from django.urls import path
from . import views

app_name = 'users'

urlpatterns = [
    path('register/', views.register_view, name='register'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('profile/edit/', views.edit_profile_view, name='edit_profile'),
    path('profile/<str:username>/', views.profile_view, name='profile'),
    # Friends
    path('friends/', views.friends_view, name='friends'),
    path('friends/request/<str:username>/', views.send_friend_request, name='send_friend_request'),
    path('friends/respond/<int:req_id>/', views.respond_friend_request, name='respond_friend_request'),
    path('friends/remove/<str:username>/', views.remove_friend, name='remove_friend'),
]
