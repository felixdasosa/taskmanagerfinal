from django.shortcuts import render, redirect, get_object_or_404
from django.shortcuts import get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone
from .models import Task
from django.core.cache import cache
from django.core.mail import send_mail
from django.contrib.auth.signals import user_logged_in, user_logged_out
import os
from django.conf import settings
from django.http import HttpResponse
from django.db.models import Q
from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.forms import PasswordChangeForm
from django.dispatch import receiver
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from webpush import send_user_notification
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from .models import Reminder # Asigură-te că ai importat modelul
from .forms import ReminderForm # Va trebui să creezi acest form (vezi mai jos)

import random
import string
import openpyxl
from openpyxl.styles import Font, Alignment

from .forms import AdaugaUtilizatorForm, AdaugaTaskForm, TrimiteMesajForm, incarca_locatii
from .models import Task, User, Mesaj, AuditLog


# --- SISTEMUL NOU DE AUDIT ---
def get_client_ip(request):
    """Extrage IP-ul real chiar și prin tuneluri sau proxy/NAT"""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip

def salveaza_log(request, actiune):
    """Salvează logul în baza de date"""
    ip = get_client_ip(request)
    user = request.user if request.user.is_authenticated else None
    AuditLog.objects.create(user=user, ip_address=ip, actiune=actiune)

# Logare automată pentru Login și Logout folosind semnale Django
@receiver(user_logged_in)
def log_user_login(sender, request, user, **kwargs):
    salveaza_log(request, "🔓 A intrat în cont (Login)")

@receiver(user_logged_out)
def log_user_logout(sender, request, user, **kwargs):
    salveaza_log(request, "🔒 A ieșit din cont (Logout)")


# --- FUNCȚIILE APLICAȚIEI ---

@login_required(login_url='login')
def dashboard(request):
    acum = timezone.now()

    if request.user.role in ['superadmin', 'manager']:
        taskuri_totale = Task.objects.all()
        notificari_recente = Task.objects.filter(status='finalizat').order_by('-data_finalizarii')[:5]
        
        # Superadminii și managerii văd TOATE taskurile întârziate din firmă
        taskuri_intarziate = Task.objects.filter(
            deadline__lt=acum
        ).exclude(status='finalizat')
        
    else:
        taskuri_totale = Task.objects.filter(atribuit_catre=request.user)
        notificari_recente = []
        
        # Angajații văd STRICT taskurile care le sunt atribuite lor
        taskuri_intarziate = Task.objects.filter(
            atribuit_catre=request.user,  # ⬅️ Aici lipsea acest filtru!
            deadline__lt=acum
        ).exclude(status='finalizat') 
    
    total = taskuri_totale.count()
    active = taskuri_totale.exclude(status='finalizat').count()
    finalizate = taskuri_totale.filter(status='finalizat').count()

    context = {
        'total': total,
        'active': active,
        'finalizate': finalizate,
        'notificari_recente': notificari_recente,
        'taskuri_intarziate': taskuri_intarziate,
    }
    
    return render(request, 'core/dashboard.html', context)


@login_required(login_url='login')
def lista_taskuri(request):
    if request.user.role in ['superadmin', 'manager']:
        toate_taskurile = Task.objects.all().order_by('-data_crearii').prefetch_related('atribuit_catre')
    else:
        toate_taskurile = Task.objects.filter(atribuit_catre=request.user).order_by('-data_crearii').prefetch_related('atribuit_catre')
        
    query = request.GET.get('q', '')
    if query:
        toate_taskurile = toate_taskurile.filter(Q(titlu__icontains=query) | Q(descriere__icontains=query))
        
    taskuri_active = toate_taskurile.exclude(status='finalizat')
    taskuri_finalizate = toate_taskurile.filter(status='finalizat')
        
    return render(request, 'core/taskuri.html', {
        'taskuri_active': taskuri_active,
        'taskuri_finalizate': taskuri_finalizate,
        'query': query
    })


@login_required(login_url='login')
def creeaza_task(request):
    if request.method == 'POST':
        form = AdaugaTaskForm(request.POST)
        if form.is_valid():
            task = form.save(commit=False)
            task.creat_de = request.user
            task.save()
            form.save_m2m() 
            
            salveaza_log(request, f"📝 A creat task-ul: '{task.titlu}'")

            # --- PRELUARE BĂIEȚI ALOCAȚI ---
            baieti_alocati = task.atribuit_catre.all()
            
            # --- 1. TRIMITERE NOTIFICĂRI PUSH PE TELEFON ---
            payload = {
                "head": "⚠️ Intervenție Nouă",
                "body": f"Locație: {task.locatie}\nTask: {task.titlu}",
                "icon": "https://i.postimg.cc/c15115Nm/taskmanager-icon-1.png",
                "url": "/"
            }
            
            for angajat in baieti_alocati:
                try:
                    send_user_notification(user=angajat, payload=payload, ttl=1000)
                    pass
                except Exception as e:
                    # Dacă un angajat nu și-a activat notificările, trecem mai departe fără să blocăm aplicația
                    print(f"Notificare Push ratată pentru {angajat.username}: {e}")

            # --- 2. TRIMITERE EMAILURI ORIGINALE ---
            emailuri_destinatari = [angajat.email for angajat in baieti_alocati if angajat.email]
            if emailuri_destinatari:
                mesaj_email = f"""Salut,\n\nAi fost alocat la un task nou. Iată detaliile intervenției:\n\n📍 Locație: {task.locatie}\n📝 Descriere: {task.descriere}\n🛠️ Acțiuni: {task.actiune}\n⚠️ Observații: {task.observatii}\n\nTe rugăm să intri în aplicație pentru mai multe detalii. \nIMPORTANT: Nu uita să dai click pe butonul "Începe Task" în momentul în care te apuci de treabă!\n\nSpor la lucru!"""
                send_mail(
                    subject=f'Task Nou: {task.locatie}',
                    message=mesaj_email,
                    from_email=None,
                    recipient_list=emailuri_destinatari,
                    fail_silently=True,
                )
                
            return redirect('lista_taskuri')
    else:
        form = AdaugaTaskForm()
        
    return render(request, 'core/creeaza_task.html', {'form': form})


@login_required(login_url='login')
def incepe_task(request, task_id):
    task = get_object_or_404(Task, id=task_id)
    
    if request.method == 'POST':
        if request.user in task.atribuit_catre.all() and task.status == 'in_asteptare':
            
            # Preluăm coordonatele din formular (dacă GPS-ul a mers)
            lat = request.POST.get('lat')
            lng = request.POST.get('lng')
            
            # Dacă GPS-ul a mers, le salvăm. Dacă nu, ne asigurăm că rămân goale.
            if lat and lng:
                task.latitudine_inceput = float(lat)
                task.longitudine_inceput = float(lng)
            else:
                task.latitudine_inceput = None
                task.longitudine_inceput = None
            
            task.status = 'in_lucru'
            task.data_inceperii = timezone.now()
            task.save() # Salvăm în baza de date

    return redirect('lista_taskuri')

@login_required(login_url='login')
def pauza_task(request, task_id):
    task = get_object_or_404(Task, id=task_id)
    if request.user in task.atribuit_catre.all() and task.status == 'in_lucru':
        task.ultima_incepere_pauza = timezone.now() # Salvăm momentul exact când a intrat în pauză
        task.status = 'in_pauza'
        task.save()
        salveaza_log(request, f"⏸️ A pus pe pauză task-ul: '{task.titlu}'")
    return redirect('lista_taskuri')


@login_required(login_url='login')
def relua_task(request, task_id):
    task = get_object_or_404(Task, id=task_id)
    if request.user in task.atribuit_catre.all() and task.status == 'in_pauza':
        # Când reia, calculăm cât a stat în pauză și adunăm la totalul pauzelor
        if task.ultima_incepere_pauza:
            diff = timezone.now() - task.ultima_incepere_pauza
            task.suma_pauze_secunde += int(diff.total_seconds())
            task.ultima_incepere_pauza = None # Resetăm
            
        task.status = 'in_lucru'
        task.save()
        salveaza_log(request, f"▶️ A reluat task-ul: '{task.titlu}'")
    return redirect('lista_taskuri')


@login_required(login_url='login')
def finalizeaza_task(request, task_id):
    task = get_object_or_404(Task, id=task_id)
    
    if not task.data_inceperii:
        task.data_inceperii = timezone.now()

    now = timezone.now()
    timp_total_brut = (now - task.data_inceperii).total_seconds()
    suma_pauze_finala = task.suma_pauze_secunde
    
    # Dacă cumva a dat finalizare direct din pauză, adunăm și ultima pauză
    if task.status == 'in_pauza' and task.ultima_incepere_pauza:
        suma_pauze_finala += (now - task.ultima_incepere_pauza).total_seconds()
    
    # Salvăm secundele efective (Total Brut - Pauze)
    task.timp_lucrat_secunde = max(0, int(timp_total_brut - suma_pauze_finala))
    task.status = 'finalizat'
    task.data_finalizarii = now
    task.save()
        
    salveaza_log(request, f"✅ A finalizat task-ul: '{task.titlu}'")
        
    if task.creat_de and task.creat_de.email:
        subiect = f'✅ Task Finalizat: {task.titlu}'
        # Folosim direct proprietatea creată în models.py
        mesaj = f'Salut {task.creat_de.username},\n\nAngajatul {request.user.username} a finalizat task-ul.\n\nTimp lucrat: {task.timp_lucrat_formatat}'
        send_mail(subiect, mesaj, settings.EMAIL_HOST_USER, [task.creat_de.email], fail_silently=True)

    if task.creat_de:
        payload = {
            "head": "✅ Task Finalizat",
            "body": f"Locație: {task.locatie}\nTask: {task.titlu}\nEchipă: {request.user.username}",
            "icon": "https://i.postimg.cc/c15115Nm/taskmanager-icon-1.png",
            "url": "/"
        }
        try:
            send_user_notification(user=task.creat_de, payload=payload, ttl=1000)
        except Exception as e:
            print(f"Notificare Push ratată: {e}")

    return redirect('lista_taskuri')

@login_required(login_url='login')
def istoric_taskuri(request):
    if request.user.role not in ['superadmin', 'manager']:
        return redirect('dashboard')
    
    angajati = User.objects.filter(role='angajat')
    
    locatii_excel = cache.get('locatii_salvate_din_excel')
    if not locatii_excel:
        locatii_excel = incarca_locatii()
        cache.set('locatii_salvate_din_excel', locatii_excel, 86400)

    locatii = [loc[0] for loc in locatii_excel if loc[0] not in ['Implicit', 'Eroare']]
    
    angajat_selectat_id = request.GET.get('angajat')
    locatie_selectata = request.GET.get('locatie')
    data_start = request.GET.get('data_start')
    data_end = request.GET.get('data_end')
    
    taskuri = Task.objects.filter(status='finalizat').order_by('-data_finalizarii').prefetch_related('atribuit_catre')
    
    if angajat_selectat_id:
        taskuri = taskuri.filter(atribuit_catre__id=angajat_selectat_id)
        angajat_selectat_id = int(angajat_selectat_id)
        
    if locatie_selectata:
        taskuri = taskuri.filter(locatie=locatie_selectata)
        
    if data_start:
        taskuri = taskuri.filter(data_finalizarii__date__gte=data_start)
    if data_end:
        taskuri = taskuri.filter(data_finalizarii__date__lte=data_end)
        
    paginator = Paginator(taskuri, 15)
    page_number = request.GET.get('page')
    
    try:
        taskuri_paginate = paginator.page(page_number)
    except PageNotAnInteger:
        taskuri_paginate = paginator.page(1)
    except EmptyPage:
        taskuri_paginate = paginator.page(paginator.num_pages)

    return render(request, 'core/istoric_taskuri.html', {
        'taskuri': taskuri_paginate,
        'angajati': angajati,
        'locatii': locatii,
        'angajat_selectat': angajat_selectat_id,
        'locatie_selectata': locatie_selectata,
        'data_start': data_start,
        'data_end': data_end
    })


@login_required(login_url='login')
def lista_mesaje(request):
    Mesaj.objects.filter(destinatar=request.user, citit=False).update(citit=True)
    
    mesaje_primite = Mesaj.objects.filter(destinatar=request.user).order_by('-data_trimitere')
    mesaje_trimise = Mesaj.objects.filter(expeditor=request.user).order_by('-data_trimitere')
    
    if request.method == 'POST':
        form = TrimiteMesajForm(request.POST)
        if form.is_valid():
            mesaj = form.save(commit=False)
            mesaj.expeditor = request.user
            mesaj.save()
            salveaza_log(request, f"✉️ A trimis un mesaj către: '{mesaj.destinatar.username}'")
            return redirect('lista_mesaje')
    else:
        form = TrimiteMesajForm()
        
    return render(request, 'core/mesaje.html', {
        'mesaje_primite': mesaje_primite,
        'mesaje_trimise': mesaje_trimise,
        'form': form
    })


@login_required(login_url='login')
def adauga_utilizator(request):
    if request.user.role != 'superadmin':
        return redirect('dashboard')
    
    if request.method == 'POST':
        form = AdaugaUtilizatorForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            parola_clara = form.cleaned_data['parola']
            user.set_password(parola_clara)
            user.save()
            
            subiect = "Contul tău a fost creat"
            mesaj = f"Salut {user.username},\n\nContul tău a fost creat cu succes pe platformă.\n\nDate de logare:\nUsername: {user.username}\nParolă: {parola_clara}"
            send_mail(subiect, mesaj, settings.EMAIL_HOST_USER, [user.email], fail_silently=False)
            
            salveaza_log(request, f"👤 A creat contul pentru utilizatorul: '{user.username}' ({user.email})")
            return redirect('dashboard')
    else:
        form = AdaugaUtilizatorForm()
    return render(request, 'core/adauga_utilizator.html', {'form': form})


@login_required(login_url='login')
def lista_utilizatori(request):
    if request.user.role not in ['superadmin', 'manager']:
        return redirect('dashboard')
    
    utilizatori = User.objects.all().order_by('-date_joined')
    return render(request, 'core/lista_utilizatori.html', {'utilizatori': utilizatori})


@login_required(login_url='login')
def reseteaza_parola(request, user_id):
    if request.user.role != 'superadmin':
        return redirect('dashboard')
    
    user_tinta = get_object_or_404(User, id=user_id)
    caractere = string.ascii_letters + string.digits
    parola_noua = ''.join(random.choice(caractere) for i in range(10))
    user_tinta.set_password(parola_noua)
    user_tinta.save()
    
    subiect = "Resetare parolă"
    mesaj = f"Salut,\n\nParola ta a fost resetată.\nNoua ta parolă este: {parola_noua}"
    send_mail(subiect, mesaj, settings.EMAIL_HOST_USER, [user_tinta.email], fail_silently=False)
    
    salveaza_log(request, f"🔑 A resetat parola pentru utilizatorul: '{user_tinta.username}'")
    return redirect('lista_utilizatori')


@login_required(login_url='login')
def profil_utilizator(request):
    if request.method == 'POST':
        form = PasswordChangeForm(request.user, request.POST)
        if form.is_valid():
            user = form.save()
            update_session_auth_hash(request, user)
            return redirect('dashboard')
    else:
        form = PasswordChangeForm(request.user)
        
    return render(request, 'core/profil.html', {'form': form})


@login_required(login_url='login')
def sterge_utilizator(request, user_id):
    if request.user.role != 'superadmin':
        return redirect('dashboard')
    
    user_de_sters = get_object_or_404(User, id=user_id)
    if user_de_sters == request.user:
        return redirect('lista_utilizatori')
        
    salveaza_log(request, f"❌ A șters utilizatorul: '{user_de_sters.username}'")
    user_de_sters.delete()
    return redirect('lista_taskuri')


@login_required(login_url='login')
def editeaza_task(request, task_id):
    if request.user.role not in ['superadmin', 'manager']:
        return redirect('lista_taskuri')
        
    task = get_object_or_404(Task, id=task_id)
    
    if request.method == 'POST':
        form = AdaugaTaskForm(request.POST, instance=task)
        if form.is_valid():
            task = form.save(commit=False)
            task.save()
            form.save_m2m()
            salveaza_log(request, f"✏️ A modificat task-ul: '{task.titlu}' (ID: {task.id})")
            return redirect('lista_taskuri')
    else:
        form = AdaugaTaskForm(instance=task)
        
    return render(request, 'core/creeaza_task.html', {'form': form, 'editare': True})


@login_required(login_url='login')
def sterge_task(request, task_id):
    if request.user.role not in ['superadmin', 'manager']:
        return redirect('lista_taskuri')
        
    task = get_object_or_404(Task, id=task_id)
    salveaza_log(request, f"🗑️ A șters definitiv task-ul: '{task.titlu}' (ID: {task.id})")
    task.delete()
    return redirect('lista_taskuri')


@login_required(login_url='login')
def export_raport_excel(request):
    if request.user.role not in ['superadmin', 'manager']:
        return redirect('dashboard')
    
    locatie = request.GET.get('locatie')
    angajat_id = request.GET.get('angajat')
    data_start = request.GET.get('data_start')
    data_end = request.GET.get('data_end')
    
    taskuri = Task.objects.filter(status='finalizat').prefetch_related('atribuit_catre')
    
    nume_angajat = ""
    if angajat_id:
        taskuri = taskuri.filter(atribuit_catre__id=angajat_id)
        angajat_obj = User.objects.filter(id=angajat_id).first()
        if angajat_obj:
            nume_angajat = angajat_obj.username
            
    if locatie:
        taskuri = taskuri.filter(locatie=locatie)
        
    if data_start:
        taskuri = taskuri.filter(data_finalizarii__date__gte=data_start)
    if data_end:
        taskuri = taskuri.filter(data_finalizarii__date__lte=data_end)
    
    nume_fisier = "Raport_Interventii"
    if nume_angajat and locatie:
        nume_fisier = f"Raport_{nume_angajat}_{locatie}"
    elif nume_angajat:
        nume_fisier = f"Raport_{nume_angajat}"
    elif locatie:
        nume_fisier = f"Raport_{locatie}"
        
    if data_start and data_end:
        nume_fisier += f"_{data_start}_to_{data_end}"
        
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Istoric Taskuri"
    
    headers = [
        'Titlu Task', 'Locație', 'Acțiuni Necesare', 'Responsabili', 
        'Data Începerii', 'Data Finalizării', 'Durată Lucru', 'Status Timp', 'Raport Angajat'
    ]
    ws.append(headers)
    
    for cell in ws[1]:
        cell.font = Font(bold=True)
        cell.alignment = Alignment(horizontal='center', vertical='center')
    
    for task in taskuri:
        durata_min = 0
        if task.data_inceperii and task.data_finalizarii:
            diff = task.data_finalizarii - task.data_inceperii
            durata_min = int(diff.total_seconds() / 60)
            
        responsabili = ", ".join([u.username for u in task.atribuit_catre.all()])
        
        status_timp = "La timp"
        if task.data_finalizarii and task.deadline:
            if task.data_finalizarii > task.deadline:
                status_timp = "Întârziat"
        
        ws.append([
            task.titlu,
            task.locatie,
            task.actiune,
            responsabili,
            task.data_inceperii.strftime('%d-%m-%Y %H:%M') if task.data_inceperii else '-',
            task.data_finalizarii.strftime('%d-%m-%Y %H:%M') if task.data_finalizarii else '-',
            f"{durata_min} min",
            status_timp,
            task.raport_finalizare or ""
        ])
    
    for col in ws.columns:
        max_length = 0
        col_letter = col[0].column_letter
        for cell in col:
            try:
                if cell.value:
                    lines = str(cell.value).split('\n')
                    for line in lines:
                        if len(line) > max_length:
                            max_length = len(line)
            except:
                pass
        
        adjusted_width = max_length + 2
        if adjusted_width > 45:
            adjusted_width = 45
            for cell in col:
                if cell.row != 1:
                    cell.alignment = Alignment(wrap_text=True, vertical='top')
        
        ws.column_dimensions[col_letter].width = adjusted_width
        
    # Înregistrăm acțiunea în Audit chiar înainte de return
    salveaza_log(request, f"📥 A descărcat un raport Excel (Filtre: Locație={locatie or 'Toate'}, Angajat={nume_angajat or 'Toți'})")

    response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    response['Content-Disposition'] = f'attachment; filename="{nume_fisier}.xlsx"'
    wb.save(response)
    return response


@login_required(login_url='login')
def vizualizare_audit(request):
    if request.user.role not in ['superadmin', 'manager']:
        return redirect('dashboard')
    
    # 1. Preluăm logurile
    loguri = AuditLog.objects.select_related('user').all()
    
    # 2. Preluăm ce a selectat utilizatorul în filtre
    query = request.GET.get('q', '')
    data_start = request.GET.get('data_start', '')
    data_end = request.GET.get('data_end', '')
    
    # 3. Aplicăm filtrele dacă au fost completate
    if query:
        # Caută textul fie în acțiune, fie în numele utilizatorului (de aia folosim Q)
        loguri = loguri.filter(Q(actiune__icontains=query) | Q(user__username__icontains=query))
        
    if data_start:
        loguri = loguri.filter(data_ora__gte=data_start)
        
    if data_end:
        loguri = loguri.filter(data_ora__lte=data_end)
        
    # 4. Paginarea (după ce am filtrat)
    paginator = Paginator(loguri, 50)
    page_number = request.GET.get('page')
    
    try:
        loguri_paginate = paginator.page(page_number)
    except PageNotAnInteger:
        loguri_paginate = paginator.page(1)
    except EmptyPage:
        loguri_paginate = paginator.page(paginator.num_pages)
        
    return render(request, 'core/audit.html', {
        'loguri': loguri_paginate,
        'query': query,
        'data_start': data_start,
        'data_end': data_end
        
    })
@login_required
def lista_reminders(request):
    # Verificăm dacă e manager sau superadmin
    if not (request.user.role == 'superadmin' or request.user.role == 'manager'):
        return redirect('dashboard')
        
    if request.method == 'POST':
        form = ReminderForm(request.POST)
        if form.is_valid():
            reminder = form.save(commit=False)
            reminder.user = request.user
            reminder.save()
            return redirect('lista_reminders')
    else:
        form = ReminderForm()
        
    reminders = Reminder.objects.filter(user=request.user).order_by('data_reminder')
    
    # Am specificat calea 'core/reminders.html' 
    # Te rog să te asiguri că fișierul este în core/templates/core/reminders.html
    return render(request, 'core/reminders.html', {'reminders': reminders, 'form': form})

@login_required
def sterge_reminder(request, reminder_id):
    # Doar autorul poate șterge reminder-ul
    reminder = get_object_or_404(Reminder, id=reminder_id, user=request.user)
    reminder.delete()
    return redirect('lista_reminders')