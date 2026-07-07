from .models import Task, Mesaj

def notificari(request):
    # Verificăm dacă utilizatorul este logat, ca să nu dea eroare
    if request.user.is_authenticated:
        # Numărăm mesajele care au fost trimise către el și încă nu au fost citite
        mesaje_necitite = Mesaj.objects.filter(destinatar=request.user, citit=False).count()
        
        # Numărăm task-urile care stau pe statusul "in_asteptare" (doar pentru angajați)
        if getattr(request.user, 'role', '') == 'angajat':
            taskuri_noi = Task.objects.filter(atribuit_catre=request.user, status='in_asteptare').count()
        else:
            taskuri_noi = 0 # Șefii nu au notificări de task-uri aici
            
        return {
            'mesaje_necitite': mesaje_necitite,
            'taskuri_noi': taskuri_noi,
        }
    return {}