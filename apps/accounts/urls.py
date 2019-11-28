# coding:utf-8
from django.urls import path, re_path
from accounts.views.auth import LoginView, OAuthRedirectView, OAuthAuthView, LogoutView, Profile
from accounts.views.user import user, UserListView, OaUserListAPIView
from accounts.views.permission import perm, PermListView, PermDetailView, perm_group, PermGroupListView

app_name = 'accounts'

# API
urlpatterns = [
        re_path('(?P<version>[v1|v2]+)/oa_user_list/', OaUserListAPIView.as_view(), name='api-oa-user-list'),
]

urlpatterns += [
        path('login/', LoginView.as_view(), name='login'),
        path('logout/', LogoutView.as_view(), name='logout'),
        path('oauth/redirect/', OAuthRedirectView.as_view(), name='oauth-redirect'),
        path('oauth/auth/', OAuthAuthView.as_view(), name='oauth-auth'),
        path('profile/', Profile.as_view(), name='profile'),
        path('pass_change/', Profile.as_view(), name='pass_change'),
        path('user/', user, name='user'),
        path('user_list/', UserListView.as_view(), name="user-list"),
        path('perm/', perm, name='perm'),
        path('perm_list/', PermListView.as_view(), name="perm-list"),
        re_path('perm_detail/(?P<pk>\d+)?/?$', PermDetailView.as_view(), name="perm-detail"),
        path('perm_group/', perm_group, name='perm-group'),
        path('perm_group_list/', PermGroupListView.as_view(), name="perm-group-list"),
]
