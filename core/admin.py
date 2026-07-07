from django.contrib import admin
from .models import User, Task, Mesaj

# Inregistram tabelele pentru a le vedea in panoul de Superadmin
admin.site.register(User)
admin.site.register(Task)
admin.site.register(Mesaj)