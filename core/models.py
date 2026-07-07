from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils import timezone

class User(AbstractUser):
    ROLE_CHOICES = [
        ('superadmin', 'Superadmin'),
        ('manager', 'Manager'),
        ('gestionar', 'Gestionar'),
        ('sofer', 'Sofer'),
        ('tehnician', 'Tehnician'),
        ('inginer', 'Inginer'),
    ]
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='angajat')

class Task(models.Model):
    STATUS_CHOICES = [
        ('in_asteptare', 'În așteptare'),
        ('in_lucru', 'În lucru'),
        ('in_pauza', 'În pauză'), # Obligatoriu pentru funcția de pauză
        ('finalizat', 'Finalizat'),
    ]
    
    PRIORITY_CHOICES = [
        ('scazuta', 'Scăzută'),
        ('normala', 'Normală'),
        ('urgenta', 'Urgentă'),
    ]
    
    # --- DATE GENERALE TASK ---
    titlu = models.CharField(max_length=200, blank=True) 
    descriere = models.TextField(blank=True)
    locatie = models.CharField(max_length=200, default='Locatie noua')
    actiune = models.CharField(max_length=200, default='Actiune noua')
    observatii = models.TextField(blank=True, verbose_name="Observații suplimentare")
    raport_finalizare = models.TextField(blank=True, verbose_name="Raport Finalizare (Angajat)")
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='in_asteptare')
    prioritate = models.CharField(max_length=20, choices=PRIORITY_CHOICES, default='normala')
    notificare_trimisa = models.BooleanField(default=False)
    
    # --- RELAȚII ---
    creat_de = models.ForeignKey(User, on_delete=models.CASCADE, related_name='taskuri_create')
    atribuit_catre = models.ManyToManyField(User, related_name='taskuri_primite')
    
    # --- TIMP, LOCAȚIE ȘI PAUZE ---
    data_crearii = models.DateTimeField(auto_now_add=True)
    deadline = models.DateTimeField()
    data_inceperii = models.DateTimeField(null=True, blank=True)
    data_finalizarii = models.DateTimeField(null=True, blank=True)
    
    latitudine_inceput = models.FloatField(blank=True, null=True)
    longitudine_inceput = models.FloatField(blank=True, null=True)
    
    # Câmpuri vitale pentru pauze (Curățate de duplicate)
    ultima_incepere_pauza = models.DateTimeField(null=True, blank=True)
    suma_pauze_secunde = models.IntegerField(default=0)
    timp_lucrat_secunde = models.IntegerField(default=0)

    # --- FUNCȚII INTELIGENTE ---
    @property
    def timp_lucrat_formatat(self):
        """Calculul definitiv și inteligent al timpului lucrat."""
        secunde = getattr(self, 'timp_lucrat_secunde', 0)
        
        # Sistemul de siguranță: dacă nu s-a salvat în BD, calculează acum live
        if (not secunde or secunde == 0) and self.data_inceperii and self.data_finalizarii:
            secunde = (self.data_finalizarii - self.data_inceperii).total_seconds()
            suma_pauze = getattr(self, 'suma_pauze_secunde', 0)
            secunde = max(0, secunde - suma_pauze)
            
        if not secunde or secunde <= 0:
            return "0h 0m"
            
        ore = int(secunde // 3600)
        minute = int((secunde % 3600) // 60)
        return f"{ore}h {minute}m"

    @property
    def link_google_maps(self):
        if self.latitudine_inceput and self.longitudine_inceput:
            return f"http://maps.google.com/?q={self.latitudine_inceput},{self.longitudine_inceput}"
        return None

    @property
    def este_intarziat(self):
        if self.deadline and self.deadline < timezone.now() and self.status != 'finalizat':
            return True
        return False

    @property
    def intarziere(self):
        if self.status == 'finalizat' and self.data_finalizarii and self.deadline:
            if self.data_finalizarii > self.deadline:
                diferenta = self.data_finalizarii - self.deadline
                zile = diferenta.days
                secunde_ramase = diferenta.seconds
                ore = secunde_ramase // 3600
                minute = (secunde_ramase % 3600) // 60
                
                parti = []
                if zile > 0: parti.append(f"{zile} zile")
                if ore > 0: parti.append(f"{ore} ore")
                if minute > 0: parti.append(f"{minute} minute")
                
                return ", ".join(parti)
        return None

    def save(self, *args, **kwargs):
        if not self.titlu:
            self.titlu = f"{self.actiune} - {self.locatie}"
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.titlu}"

class Mesaj(models.Model):
    expeditor = models.ForeignKey(User, on_delete=models.CASCADE, related_name='mesaje_trimise')
    destinatar = models.ForeignKey(User, on_delete=models.CASCADE, related_name='mesaje_primite')
    continut = models.TextField()
    data_trimitere = models.DateTimeField(auto_now_add=True)
    citit = models.BooleanField(default=False)

    def __str__(self):
        return f"Mesaj de la {self.expeditor.username} pentru {self.destinatar.username}"

class AuditLog(models.Model):
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    ip_address = models.CharField(max_length=50)
    actiune = models.CharField(max_length=255)
    data_ora = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-data_ora']

    def __str__(self):
        return f"{self.data_ora} - {self.user} - {self.actiune}"

class Reminder(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    titlu = models.CharField(max_length=200)
    detalii = models.TextField()
    data_reminder = models.DateTimeField()
    creat_la = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.titlu} - {self.user.username}"