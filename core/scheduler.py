from apscheduler.schedulers.background import BackgroundScheduler
from django.core.mail import send_mail
from django.utils import timezone
from django.conf import settings
from .models import Task 

def verifica_si_trimite_mail():
    # Căutăm taskuri întârziate pentru care nu s-a trimis încă mail
    taskuri_problema = Task.objects.filter(
        deadline__lt=timezone.now(),
        notificare_trimisa=False
    ).exclude(status='finalizat')

    for task in taskuri_problema:
        # Verificăm dacă știm cine a creat task-ul și dacă are adresă de mail
        if task.creat_de and task.creat_de.email:
            # Creăm o listă cu numele angajaților care trebuiau să facă treaba
            nume_angajati = ", ".join([angajat.username for angajat in task.atribuit_catre.all()])
            
            subiect = f"⚠️ URGENT: Task Întârziat - {task.locatie}"
            mesaj = f"""Salut {task.creat_de.username},

Task-ul creat de tine pentru locația '{task.locatie}' a depășit deadline-ul!

Detalii:
- Acțiune: {task.actiune}
- Atribuit către: {nume_angajati}
- Termen limită: {task.deadline.strftime("%d-%m-%Y %H:%M")}

Te rugăm să intri în aplicație și să verifici situația cu angajații.
"""
            
            # Trimite mailul exact celui care l-a creat
            send_mail(
                subiect,
                mesaj,
                settings.EMAIL_HOST_USER,
                [task.creat_de.email], 
                fail_silently=False,
            )
        
        # Marcăm ca trimis ca să nu îi dăm spam în fiecare oră
        task.notificare_trimisa = True
        task.save()

def start_scheduler():
    scheduler = BackgroundScheduler()
    # Scanează din oră în oră
    scheduler.add_job(verifica_si_trimite_mail, 'interval', minutes=1)
    scheduler.start()