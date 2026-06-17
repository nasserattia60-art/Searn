from django.urls import path
from . import views
urlpatterns = [
    path('', views.home, name='class-home'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('create/', views.create_class, name='create-class'),
    path('<int:class_id>/', views.class_detail, name='class-detail'),
    path('<int:class_id>/join/', views.join_class, name='join-class'),
    path('<int:class_id>/leave/', views.leave_class, name='leave-class'),
    path('lesson/<uuid:lesson_uuid>/', views.lesson_detail, name='lesson-detail'),
    path('lesson/<uuid:lesson_uuid>/subtitles/', views.lesson_subtitles, name='lesson-subtitles'),
    path('lesson/<uuid:lesson_uuid>/complete/', views.mark_completed, name='mark-completed'),
    path('lesson/<uuid:lesson_uuid>/position/', views.save_position, name='save-position'),
    
    # Quiz URLs
    path('<int:class_id>/quizzes/', views.quiz_list, name='quiz-list'),
    path('lesson/<int:lesson_id>/quiz/', views.quiz_detail, name='quiz-detail'),
    path('lesson/<int:lesson_id>/quiz/response/<int:question_id>/', views.quiz_submit_response, name='quiz-response'),
    path('lesson/<int:lesson_id>/quiz/results/', views.quiz_results, name='quiz-results'),
    path('lesson/<int:lesson_id>/quiz/retry/', views.quiz_retry, name='quiz-retry'),
]