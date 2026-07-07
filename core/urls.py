from django.urls import path, include
from django.contrib.auth import views as auth_views
from . import views

urlpatterns = [
    # Logare / Logout
    path('login/', auth_views.LoginView.as_view(template_name='core/login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(next_page='login'), name='logout'),
    
    # Dashboard
    path('', views.dashboard, name='dashboard'),
    
    # Utilizatori
    path('adauga-utilizator/', views.adauga_utilizator, name='adauga_utilizator'),
    path('utilizatori/', views.lista_utilizatori, name='lista_utilizatori'),
    path('utilizatori/reseteaza/<int:user_id>/', views.reseteaza_parola, name='reseteaza_parola'),
    path('utilizatori/sterge/<int:user_id>/', views.sterge_utilizator, name='sterge_utilizator'),
    path('profil/', views.profil_utilizator, name='profil'),
    
    # Task-uri
    path('creeaza-task/', views.creeaza_task, name='creeaza_task'),
    path('taskuri/', views.lista_taskuri, name='lista_taskuri'),
    path('task/incepe/<int:task_id>/', views.incepe_task, name='incepe_task'),
    path('task/finalizeaza/<int:task_id>/', views.finalizeaza_task, name='finalizeaza_task'),
    path('editeaza-task/<int:task_id>/', views.editeaza_task, name='editeaza_task'),
    path('sterge-task/<int:task_id>/', views.sterge_task, name='sterge_task'),
    path('pauza-task/<int:task_id>/', views.pauza_task, name='pauza_task'),
    path('relua-task/<int:task_id>/', views.relua_task, name='relua_task'),
    
    # Istoric, Audit și Export
    path('istoric/', views.istoric_taskuri, name='istoric_taskuri'),
    path('audit/', views.vizualizare_audit, name='vizualizare_audit'),
    path('export-raport-excel/', views.export_raport_excel, name='export_raport_excel'),
    
    # Mesaje și Notificări
    path('mesaje/', views.lista_mesaje, name='lista_mesaje'),
    path('webpush/', include('webpush.urls')),
    
    # Reminders (Noile rute)
    path('reminders/', views.lista_reminders, name='lista_reminders'),
    path('reminders/sterge/<int:reminder_id>/', views.sterge_reminder, name='sterge_reminder'),
]