# 📋 ESTADO DEL PROYECTO — Cowrie Threat Dashboard

> Documento de handoff para continuar en un chat nuevo sin perder contexto.
> **Cómo usarlo:** Pegale este documento completo al inicio del nuevo chat con Claude.
> **Última actualización:** 02 de junio de 2026

---

## 👤 Quién soy

**Hans Soto** — Estudiante de Ingeniería en Ciberseguridad (2° año).
Enfoque: **Blue Team / SOC**.

- 🌐 Portafolio: https://hsoto.pythonanywhere.com
- 💻 GitHub: https://github.com/hanssoto-cyber
- 📧 Email: hans.soto.g@gmail.com
- 🔗 LinkedIn: https://www.linkedin.com/in/hans-soto-gonzalez-a142b8170/

---

## 🎯 Proyecto actual: Cowrie Threat Dashboard

Dashboard web en Django que lee los logs del honeypot Cowrie y los visualiza
como un SOC real: stats, mapa mundial de atacantes, tablas de intentos,
top contraseñas/usuarios y gráficos por hora. Auto-refresh cada 30s.

**Repo en GitHub:** `cowrie-dashboard`
(https://github.com/hanssoto-cyber/cowrie-dashboard)

**Estado:** ⚙️ EN DESARROLLO — funcionando en local con datos de prueba.
Pipeline completo validado. Falta conectar logs reales y deploy.

---

## 🧱 Stack técnico

- Python + Django **6.0.5** (ojo: versión muy nueva, instalada hoy)
- SQLite (base de datos)
- python-decouple (variables de entorno vía `.env`)
- requests (geolocalización de IPs)
- Chart.js (gráficos)
- Leaflet.js + CARTO dark tiles (mapa de atacantes)
- ip-api.com (geolocalización gratuita, 45 req/min)
- JetBrains Mono + paleta terminal hacker (misma identidad que el portafolio)

---

## 📁 Estructura del proyecto

Se respetó el flujo del profesor: **todo dentro de una carpeta contenedora.**

```
cowrie-dashboard/                  ← raíz del repo (aquí está .git y .gitignore)
├── cowrie_dashboard/              ← carpeta contenedora
│   ├── config/                    ← settings, urls, wsgi, asgi
│   ├── dashboard/                 ← app principal
│   │   ├── models.py              ← Connection, LoginAttempt, IPGeolocation
│   │   ├── views.py               ← vistas con ORM (_build_stats)
│   │   ├── admin.py               ← los 3 modelos registrados
│   │   ├── urls.py                ← rutas de la app (app_name='dashboard')
│   │   ├── utils.py               ← ⚠️ OBSOLETO, borrar (ya no se usa)
│   │   └── management/commands/
│   │       ├── import_cowrie.py   ← ingiere log JSON → BD
│   │       └── seed_demo.py       ← genera datos de prueba
│   ├── templates/
│   │   ├── base.html              ← plantilla madre (herencia)
│   │   └── dashboard/
│   │       ├── index.html         ← dashboard principal + mapa + gráfico
│   │       ├── attacks.html       ← tabla completa de ataques
│   │       └── stats.html         ← top pass/users + gráfico líneas
│   ├── static/
│   │   ├── css/style.css          ← estilo terminal hacker
│   │   └── js/main.js             ← auto-refresh AJAX cada 30s
│   ├── logs/cowrie.json           ← log local (IGNORADO en git)
│   ├── .env                       ← SECRET_KEY, DEBUG, COWRIE_LOG_PATH (IGNORADO)
│   ├── db.sqlite3                 ← BD (IGNORADO, se regenera)
│   └── manage.py
├── venv/                          ← entorno virtual (IGNORADO)
├── .gitignore
├── README.md
└── requirements.txt

Ruta local en Windows:
D:\Python\Poyectos-Django\cowrie-dashboard\
```

---

## 🗃️ Modelos (dashboard/models.py)

- **IPGeolocation** — geo cacheada por IP (ip, country, city, lat, lon).
  Cada IP se geolocaliza UNA sola vez.
- **Connection** — cada `cowrie.session.connect` (src_ip, session único, timestamp).
- **LoginAttempt** — cada login éxito/fallo (src_ip, username, password, success,
  session, timestamp, FK a IPGeolocation). Constraint único para no duplicar.

---

## ⚙️ Comandos del proyecto

```bash
# Activar entorno (Git Bash en Windows)
cd /d/Python/Poyectos-Django/cowrie-dashboard
source venv/Scripts/activate
cd cowrie_dashboard

# Importar logs reales de Cowrie a la BD
python manage.py import_cowrie
python manage.py import_cowrie --path logs/cowrie.json   # ruta manual

# Generar datos de prueba (DEMO)
python manage.py seed_demo --count 200

# Correr servidor
python manage.py runserver
# → http://127.0.0.1:8000        (dashboard)
# → http://127.0.0.1:8000/stats/    (estadísticas)
# → http://127.0.0.1:8000/attacks/  (tabla completa)
```

---

## 🔐 Configuración del .env (NO se sube a git)

```
SECRET_KEY=django-insecure-cowrie-dashboard-dev-key-2026
DEBUG=True
ALLOWED_HOSTS=127.0.0.1,localhost
COWRIE_LOG_PATH=D:/Python/Poyectos-Django/cowrie-dashboard/cowrie_dashboard/logs/cowrie.json
```

> Nota: usar barras `/` aunque sea Windows. Si falta `COWRIE_LOG_PATH`,
> settings.py cae al default que apunta a la ruta de la VM Ubuntu.

---

## 🐝 Honeypot Cowrie (la fuente de datos)

**VM:** Ubuntu en VMware. Hostname `elk`. Usuario admin: `rickthor`.
**Cowrie:** corre bajo usuario `cowrie`, puerto **2222**, hostname falso `webserver01`.
**Log:** `/home/cowrie/cowrie/var/log/cowrie/cowrie.json`

**Iniciar Cowrie:**
```bash
sudo su - cowrie
cd ~/cowrie
source cowrie-env/bin/activate
twistd -n cowrie
```

**Exposición a internet — RESUELTO con Ngrok:**
- El router (Echolife GP8818A del ISP) NO tiene port forwarding.
- Cloudflare Tunnel requería dominio propio (descartado).
- playit.gg requería premium para TCP (descartado).
- **Ngrok** funcionó tras agregar tarjeta (verificación, no cobran).

```bash
ngrok tcp 2222
# → expone en tcp://0.tcp.sa.ngrok.io:PUERTO (aleatorio, cambia al reiniciar)
```

> ⚠️ Con Ngrok gratis la dirección es aleatoria y cambia cada reinicio.
> Los bots tardan más en encontrarla que un puerto directo.

---

## ✅ Lo que se logró hoy

- Cowrie corriendo y expuesto a internet vía Ngrok (verificado con login de prueba).
- Proyecto Django creado en carpeta contenedora (flujo del profesor).
- 3 modelos con ORM + admin registrado + migraciones aplicadas.
- `import_cowrie`: pipeline log JSON → SQLite validado (1 conexión, 1 login).
- `seed_demo`: 200 ataques de prueba en 10 IPs de 9 países.
- Dashboard funcionando: stats, mapa Leaflet, gráficos Chart.js, auto-refresh.
- Herencia de plantillas (base.html → index/attacks/stats).
- Commit y push a GitHub (26 archivos, 1512 líneas).

---

## 🗺️ Pendientes (para retomar)

### Prioridad ALTA
- [ ] **Borrar `dashboard/utils.py`** — quedó obsoleto al migrar al ORM.
- [ ] **Conectar logs reales VM → Windows.** Opciones:
      (a) correr `import_cowrie` directamente en la VM,
      (b) carpeta compartida VMware,
      (c) scp/rsync periódico.
- [ ] **Dejar Cowrie + Ngrok corriendo** para acumular ataques reales.

### Prioridad MEDIA
- [ ] Limpiar datos demo antes de cargar reales (o separar entornos).
- [ ] Programar `import_cowrie` automático (cron en la VM / tarea programada).
- [ ] Deploy del dashboard (PythonAnywhere u otro).
- [ ] Botón/indicador de "última actualización" en el dashboard.

### Prioridad BAJA
- [ ] Filtros por país / rango de fechas en la tabla de ataques.
- [ ] Correlación con MITRE ATT&CK.
- [ ] Exportar reporte (CSV/PDF) de ataques.
- [ ] Extensión Django en VS Code (silencia falsos positivos del linter).

---

## 💬 Estilo de trabajo

- Nuevo en Django/desarrollo web (este es el 2° proyecto).
- Python básico. Windows + VS Code + Git Bash (MINGW64).
- Me gusta entender el "por qué" de cada cosa.
- Prefiero pasos pequeños verificables, de a uno.
- Respeto el flujo del profesor: todo dentro de carpeta contenedora.
- Vivo en Santiago, Chile.

## ⚠️ Cosas importantes

1. El `.env`, `db.sqlite3`, `logs/` y `venv/` NO se suben a git (verificado).
2. El `.git` está en la carpeta padre `cowrie-dashboard/`, no en `cowrie_dashboard/`.
   Para commits hay que subir un nivel: `cd /d/Python/Poyectos-Django/cowrie-dashboard`.
3. Los timestamps del dashboard se convierten a hora de Santiago.
4. `127.0.0.1` no se geolocaliza (es localhost) — normal que no aparezca en el mapa.
5. Django 6.0.5 es muy reciente — si algo raro pasa, considerar la versión.

---
**Fin del documento. Pegar al inicio del nuevo chat para retomar sin perder contexto.**
