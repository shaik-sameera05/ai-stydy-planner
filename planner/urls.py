from django.contrib.auth import views as auth_views
from django.urls import path

from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('login/', views.login_view, name='login'),
    path('register/', views.register_view, name='register'),
    path('logout/', views.logout_view, name='logout'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('profile/', views.profile_view, name='profile'),
    path('subjects/', views.subjects_view, name='subjects'),
    path('topics/', views.topics_view, name='topics'),
    path('study-plan/', views.study_plan_view, name='study_plan'),
    path('study-plan/generate/', views.generate_plan_view, name='generate_plan'),
    path('progress/', views.progress_view, name='progress'),
    path('tasks/<int:task_id>/update/', views.task_update_view, name='task_update'),
    path('quizzes/', views.quizzes_view, name='quizzes'),
    path('quizzes/generate/', views.generate_quiz_view, name='generate_quiz'),
    path('quizzes/<int:quiz_id>/submit/', views.submit_quiz_view, name='submit_quiz'),
    path('ai-assistant/', views.ai_assistant_view, name='ai_assistant'),
    path('password-reset/', auth_views.PasswordResetView.as_view(template_name='planner/forgot.html', email_template_name='planner/password_reset_email.html', success_url='password_reset_done'), name='password_reset'),
    path('password-reset/done/', auth_views.PasswordResetDoneView.as_view(template_name='planner/password_reset_done.html'), name='password_reset_done'),
    path('reset/<uidb64>/<token>/', auth_views.PasswordResetConfirmView.as_view(template_name='planner/password_reset_confirm.html', success_url='password_reset_complete'), name='password_reset_confirm'),
    path('reset/complete/', auth_views.PasswordResetCompleteView.as_view(template_name='planner/password_reset_complete.html'), name='password_reset_complete'),
]