import os
import shutil
import zipfile
from datetime import datetime, timedelta

# --- CONFIGURARE ---
# Calea către folderul proiectului tău
BASE_DIR = r"C:\Users\Ifis\Desktop\taskmanager\aplicatie_taskuri"
DB_PATH = os.path.join(BASE_DIR, "db.sqlite3")

# Unde vrei să se salveze backup-urile (se va crea automat un folder 'backups')
BACKUP_DIR = os.path.join(BASE_DIR, "backups")
ZILE_RETINERE = 30  # Câte zile păstrăm backup-urile înainte să le ștergem

def ruleaza_backup():
    if not os.path.exists(BACKUP_DIR):
        os.makedirs(BACKUP_DIR)
        print(f"S-a creat folderul de backup: {BACKUP_DIR}")

    if not os.path.exists(DB_PATH):
        print(f"Eroare: Fișierul bazei de date nu a fost găsit la {DB_PATH}")
        return

    # Generăm numele arhivei cu data și ora curentă
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    nume_arhiva = f"backup_baza_date_{timestamp}.zip"
    cale_arhiva_completa = os.path.join(BACKUP_DIR, nume_arhiva)

    # Creăm arhiva zip și adăugăm fișierul SQLite în ea
    try:
        with zipfile.ZipFile(cale_arhiva_completa, 'w', zipfile.ZIP_DEFLATED) as zipf:
            zipf.write(DB_PATH, arcname="db.sqlite3")
        print(f"[SUCCES] Backup creat cu succes: {nume_arhiva}")
    except Exception as e:
        print(f"[EROARE] Nu s-a putut crea backup-ul: {e}")
        return

    # --- CURĂȚENIE AUTOMATĂ (Ștergem fișierele mai vechi de 30 de zile) ---
    limita_timp = datetime.now() - timedelta(days=ZILE_RETINERE)
    
    for fisier in os.listdir(BACKUP_DIR):
        cale_fisier = os.path.join(BACKUP_DIR, fisier)
        if os.path.isfile(cale_fisier):
            timp_creare = datetime.fromtimestamp(os.path.getmtime(cale_fisier))
            if timp_creare < limita_timp:
                try:
                    os.remove(cale_fisier)
                    print(f"[CURĂȚENIE] S-a șters backup-ul vechi: {fisier}")
                except Exception as e:
                    print(f"[EROARE] Nu s-a putut șterge fișierul vechi {fisier}: {e}")

if __name__ == "__main__":
    ruleaza_backup()