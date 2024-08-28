from django.urls import re_path
from .views import login, switch, logout


urlpatterns = [
    re_path(r'^login/$', login, name='multiauth_login'),
    re_path(r'^u/(?P<user_index>\d+)/$', switch, name='multiauth_switch'),
    re_path(r'^logout/(?P<user_index>\d+)/$', logout, name='multiauth_logout'),
]
