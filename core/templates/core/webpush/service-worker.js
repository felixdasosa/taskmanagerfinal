self.addEventListener('push', function(event) {
  let data = {};

  if (event.data) {
    try {
      // 1. Încearcă să extragă datele ca JSON (așa cum le trimite corect Django)
      data = event.data.json();
    } catch (e) {
      // 2. Dacă eșuează (e text simplu de la butonul "Test Push"), construim noi un obiect
      data = {
        head: "Test din Browser",
        body: event.data.text(),
        icon: "",
        url: self.location.origin
      };
    }
  } else {
    // 3. Dacă nu primește nimic
    data = { 
        head: "Notificare nouă", 
        body: "Fără detalii suplimentare.", 
        icon: "", 
        url: self.location.origin 
    };
  }

  // Setăm opțiunile de afișare
  const head = data.head || "Notificare";
  const options = {
    body: data.body || "Ai un mesaj nou.",
    icon: data.icon || "https://i.postimg.cc/c15115Nm/taskmanager-icon-1.png",
    data: { url: data.url || self.location.origin }
  };

  // Afișăm notificarea pe ecran
  event.waitUntil(
    self.registration.showNotification(head, options)
  );
});

self.addEventListener('notificationclick', function(event) {
  // Închidem chenarul notificării
  event.notification.close();
  
  // Deschidem link-ul
  event.waitUntil(
    clients.openWindow(event.notification.data.url)
  );
});