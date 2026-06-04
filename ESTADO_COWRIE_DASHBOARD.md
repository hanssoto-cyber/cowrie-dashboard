# 📋 ESTADO DEL PROYECTO — Cowrie Threat Dashboard

> Documento de handoff para continuar en un chat nuevo sin perder contexto.
> **Cómo usarlo:** Pegale este documento completo al inicio del nuevo chat con Claude.
> **Última actualización:** 03 de junio de 2026 (honeypot desplegado en Oracle Cloud)

---

## 👤 Quién soy

**Hans Soto** — Estudiante de Ingeniería en Ciberseguridad (2° año).
Enfoque: **Blue Team / SOC**.

- 🌐 Portafolio: https://hsoto.pythonanywhere.com
- 💻 GitHub: https://github.com/hanssoto-cyber
- 📧 Email: hans.soto.g@gmail.com
- 🔗 LinkedIn: https://www.linkedin.com/in/hans-soto-gonzalez-a142b8170/

---

## 🎯 Proyecto: Cowrie Threat Dashboard

Honeypot SSH (Cowrie) desplegado en un VPS cloud con IP pública real, que
captura ataques de internet 24/7. Un dashboard Django lee los logs y los
visualiza como un SOC: stats, mapa mundial de atacantes, tablas de intentos,
top contraseñas/usuarios y gráficos por hora. Auto-refresh cada 30s.

**Repo GitHub:** `cowrie-dashboard` (https://github.com/hanssoto-cyber/cowrie-dashboard)

**Estado:** ✅ SISTEMA COMPLETO Y AUTÓNOMO, corriendo en Oracle Cloud.
Dejándolo 24-48h acumulando ataques reales antes de documentar en GitHub.

---

## 🏗️ Arquitectura completa

```
Atacantes (internet)
    │
    ▼  puerto 22 (IP pública Oracle)
[ VM Oracle Cloud — Ubuntu 24.04 ]
    │  iptables redirige 22 → 2223
    ▼
[ Cowrie 3.0.1 ] (servicio systemd, usuario 'cowrie', puerto 2223)
    │  escribe cowrie.json
    ▼
[ cron cada 5 min ] → import_cowrie → SQLite
    │
    ▼
[ Dashboard Django ] (usuario 'ubuntu', puerto 8000, solo local)
    │
    ▼  túnel SSH (puerto 2222)
[ Mi navegador Windows ] → http://localhost:8000
```

---

## ☁️ Infraestructura Oracle Cloud

- **Cuenta:** Oracle Cloud Free Tier (Always Free), región **Chile Central (Santiago)**.
- **VM:** `cowriw-honeypot`, Ubuntu 24.04, shape VM.Standard.E2.1.Micro (Always Free).
- **Compartment:** hanssotog (root).
- **IP pública:** efímera (ANOTAR aparte, NO publicar). Guardada en archivo local
  `129.151.111.28 ip publica.txt` (ignorado en git).
- **Llave SSH privada:** `ssh-key-2026-06-03.key` (en Windows, IGNORADA en git, NUNCA subir).

### Puertos y firewall
| Puerto | Uso | Quién entra |
|--------|-----|-------------|
| 22 | Honeypot (redirige a 2223) | Bots/atacantes |
| 2222 | SSH REAL (mi acceso) | Solo yo, con llave |
| 2223 | Cowrie escucha aquí | (interno, vía redirect) |
| 8000 | Dashboard Django | Solo local + túnel SSH |

**Doble firewall (ambos persistentes):**
- Oracle Security List: ingress abierto en 22, 2222 (regla "SSH real").
- iptables interno: ACCEPT 22, 2222, 2223 antes del REJECT final.
- Redirección NAT: `PREROUTING tcp --dport 22 REDIRECT --to-port 2223`.
- Persistencia: `netfilter-persistent save` (paquete iptables-persistent).

### Cambios de seguridad hechos en la VM
- SSH movido del 22 al 2222 (editado `/etc/ssh/sshd_config` + desactivado `ssh.socket`,
  activado `ssh.service`). Verificado que solo escucha en 2222.
- Usuario `cowrie` sin privilegios corre el honeypot.
- Usuario `ubuntu` agregado al grupo `cowrie` + permisos de lectura en
  `/home/cowrie/cowrie/var/log/cowrie/` para que el dashboard lea el log.

---

## 🔑 Cómo reconectarme a la VM

Desde Git Bash en Windows, en la carpeta del proyecto (donde está la llave):

```bash
cd /d/Python/Poyectos-Django/cowrie-dashboard

# Conexión normal (administrar la VM)
ssh -i ssh-key-2026-06-03.key -p 2222 ubuntu@<IP_PUBLICA>

# Con túnel para ver el dashboard
ssh -i ssh-key-2026-06-03.key -p 2222 -L 8000:127.0.0.1:8000 ubuntu@<IP_PUBLICA>
```

> Si la VM se reinició, la IP pública efímera PUEDE cambiar. Verificar en la
> consola de Oracle (Instancia → Networking → Public IPv4).

---

## 🖥️ Cómo ver el dashboard (cada vez)

1. Abrir túnel SSH (comando de arriba con `-L 8000:...`).
2. En la VM: activar venv y correr el servidor:
   ```bash
   cd ~/cowrie-dashboard
   source venv/bin/activate
   cd cowrie_dashboard
   python manage.py runserver 127.0.0.1:8000
   ```
3. En el navegador de Windows: `http://localhost:8000`

---

## ⚙️ Servicios y automatización (ya configurados)

**Cowrie (systemd):**
```bash
sudo systemctl status cowrie     # ver estado
sudo systemctl restart cowrie    # reiniciar
sudo journalctl -u cowrie -n 30  # logs del servicio
```
- Archivo: `/etc/systemd/system/cowrie.service`
- `enable` activo → arranca solo al reiniciar la VM, Restart=on-failure.

**Cron (import automático cada 5 min):**
```
*/5 * * * * cd /home/ubuntu/cowrie-dashboard/cowrie_dashboard && \
  /home/ubuntu/cowrie-dashboard/venv/bin/python manage.py import_cowrie \
  >> /home/ubuntu/cowrie-import.log 2>&1
```
- Ver log de importación: `cat /home/ubuntu/cowrie-import.log`
- `crontab -l` para ver, `crontab -e` para editar.

**Iniciar Cowrie manual (si hiciera falta, normalmente NO):**
```bash
sudo su - cowrie
cd ~/cowrie && source cowrie-env/bin/activate && twistd -n cowrie
```

---

## 🧱 Stack del dashboard

- Python + Django **6.0.5** (ojo: versión muy nueva)
- SQLite, python-decouple (.env), requests (geo), Chart.js, Leaflet.js + CARTO dark
- ip-api.com para geolocalización (45 req/min, cacheada en BD)
- JetBrains Mono + paleta terminal hacker

### Estructura (carpeta contenedora, flujo del profesor)
```
cowrie-dashboard/                  ← raíz repo (.git, .gitignore)
├── cowrie_dashboard/
│   ├── config/                    ← settings, urls, wsgi
│   ├── dashboard/
│   │   ├── models.py              ← Connection, LoginAttempt, IPGeolocation
│   │   ├── views.py               ← ORM (_build_stats)
│   │   ├── admin.py, urls.py
│   │   ├── utils.py               ← ⚠️ OBSOLETO, borrar
│   │   └── management/commands/
│   │       ├── import_cowrie.py   ← log JSON → BD
│   │       └── seed_demo.py       ← datos de prueba
│   ├── templates/ (base.html + dashboard/index,attacks,stats)
│   ├── static/ (css/style.css, js/main.js)
│   ├── logs/                      ← local, IGNORADO
│   ├── .env                       ← IGNORADO (crear a mano en cada entorno)
│   ├── db.sqlite3                 ← IGNORADO
│   └── manage.py
├── venv/                          ← IGNORADO
└── requirements.txt
```

### .env en la VM Oracle
```
SECRET_KEY=django-insecure-cowrie-dashboard-prod-oracle-2026
DEBUG=True
ALLOWED_HOSTS=127.0.0.1,localhost
COWRIE_LOG_PATH=/home/cowrie/cowrie/var/log/cowrie/cowrie.json
```

---

## ✅ Lo logrado (sesiones 02-03 jun)

- Honeypot Cowrie 3.0.1 en Oracle Cloud con IP pública, servicio systemd 24/7.
- Hardening de red: SSH movido a 2222, honeypot en 22→2223, doble firewall persistente.
- Dashboard Django desplegado en la misma VM, leyendo logs reales.
- Pipeline automatizado: cron importa cada 5 min sin intervención.
- Acceso seguro por túnel SSH (dashboard NO expuesto a internet).
- Primeros ataques reales empezando a llegar.
- Repo limpio en GitHub: llaves SSH, .env, IP y db protegidos en .gitignore.

---

## 🗺️ Pendientes (retomar en 24-48h)

### Prioridad ALTA
- [ ] Revisar ataques acumulados (`cat cowrie-import.log`, ver dashboard lleno).
- [ ] Documentar el proyecto en GitHub (README pro) CON los datos ricos.
      ⚠️ NO publicar: IP pública, llaves, puerto 2222, .env.
- [ ] **Borrar `dashboard/utils.py`** (obsoleto desde el ORM).

### Prioridad MEDIA
- [ ] Análisis de ataques: países, top credenciales, patrones.
- [ ] Correlación con MITRE ATT&CK.
- [ ] Capturas del dashboard con datos reales para el README y LinkedIn.
- [ ] Considerar dejar el dashboard como servicio systemd también.

### Prioridad BAJA
- [ ] Filtros por país / fecha en la tabla.
- [ ] Exportar reporte (CSV/PDF).
- [ ] ¿Exponer el dashboard públicamente para el portafolio? (con cuidado).

---

## 💬 Estilo de trabajo

- Nuevo en Django/web (2° proyecto). Python básico.
- Windows + VS Code + Git Bash (MINGW64).
- Me gusta entender el "por qué". Pasos pequeños verificables, de a uno.
- Respeto el flujo del profesor: todo en carpeta contenedora.
- Santiago, Chile.

## ⚠️ Cosas críticas

1. **NUNCA** subir a git: `ssh-key-2026-06-03.key`, `.env`, IP pública, `db.sqlite3`.
2. Mi acceso SSH es por el puerto **2222** (NO el 22, ese es el honeypot).
3. El `.git` está en la raíz `cowrie-dashboard/`; para commits subir un nivel.
4. La IP pública es efímera: si la VM reinicia, verificar en consola Oracle.
5. Cowrie y cron ya son automáticos — normalmente no hay que tocar nada.
6. La VM local de VMware y Ngrok quedaron OBSOLETOS (todo está en Oracle ahora).

---
**Fin del documento. Pegar al inicio del nuevo chat para retomar sin perder contexto.**
