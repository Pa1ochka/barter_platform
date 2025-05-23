from django.urls import path
from ads import views

urlpatterns = [
    path('ads/', views.ad_list, name='ad_list'),
    path('ads/create/', views.ad_create, name='ad_create'),
    path('ads/<int:pk>/', views.ad_detail, name='ad_detail'),
    path('ads/<int:pk>/edit/', views.ad_edit, name='ad_edit'),
    path('ads/<int:pk>/delete/', views.ad_delete, name='ad_delete'),
    path('register/', views.register, name='register'),
    path('ads/<int:ad_receiver_id>/propose/', views.exchange_proposal_create, name='exchange_proposal_create'),
    path('proposals/', views.exchange_proposal_list, name='exchange_proposal_list'),
    path('proposals/<int:pk>/update/', views.exchange_proposal_update, name='exchange_proposal_update'),
    path('notifications/mark-read/', views.mark_notifications_read, name='mark_notifications_read'),

]