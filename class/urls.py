from django.urls import path
from . import views
urlpatterns = [
    path('', views.home, name='class-home'),
    path('create/', views.create_class, name='create-class'),
    path('<int:class_id>/', views.class_detail, name='class-detail'),
    path('<int:class_id>/join/', views.join_class, name='join-class'),
    path('<int:class_id>/leave/', views.leave_class, name='leave-class'),
    path('lesson/<uuid:lesson_uuid>/', views.lesson_detail, name='lesson-detail'),
    path('lesson/<uuid:lesson_uuid>/subtitles/', views.lesson_subtitles, name='lesson-subtitles'),
]
