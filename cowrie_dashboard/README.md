# 🛡️ Cowrie Threat Dashboard — Guía Operativa

> Guía personal de comandos para levantar y administrar el sistema.
> ⚠️ **USO INTERNO — NO subir a GitHub público** (contiene IP, puertos y rutas de la infraestructura).

---

## 📐 Arquitectura del sistema

```
Atacantes (internet)
    │  puerto 22 (IP pública Oracle)
    ▼
[ VM Oracle Cloud — Ubuntu 24.04 ]
    │  iptables redirige 22 → 2223
    ▼
[ Cowrie 3.0.1 ]  (servicio systemd · usuario 'cowrie' · puerto 2223)
    │  escribe cowrie.json
    ▼
[ cron cada 5 min ]  →  import_cowrie  →  SQLite
    │
    ▼
[ Dashboard Django ]  (usuario 'ubuntu' · puerto 8000 · solo local)
    │  túnel SSH (puerto 2222)
    ▼
[ Navegador Windows ]  →  http://localhost:8000
```

---

## 🔑 Datos de conexión

| Dato | Valor |
|------|-------|
| IP pública VM | `129.151.111.28` (efímera, verificar si la VM reinicia) |
| Mi acceso SSH | puerto `2222`, usuario `ubuntu`, con llave |
| Honeypot Cowrie | puerto `22` externo → `2223` interno |
| Dashboard | puerto `8000` (solo local + túnel) |
| Llave SSH | `ssh-key-2026-06-03.key` (en Windows) |

---

## 1️⃣ Conectarse a la VM (administrar)

Desde Git Bash en Windows, en la carpeta del proyecto:

```bash
cd /d/Python/Poyectos-Django/cowrie-dashboard
ssh -i ssh-key-2026-06-03.key -p 2222 ubuntu@129.151.111.28
```

---

## 2️⃣ Ver el dashboard (túnel SSH + servidor)

El dashboard NO está expuesto a internet. Para verlo se usa un túnel SSH.

### Paso A — Abrir el túnel (desde Windows)
Una ventana de Git Bash en Windows. El túnel reenvía el 8000 local al 8000 de la VM:

```bash
cd /d/Python/Poyectos-Django/cowrie-dashboard
ssh -i ssh-key-2026-06-03.key -p 2222 -L 8000:127.0.0.1:8000 ubuntu@129.151.111.28
```

> Esta misma sesión queda dentro de la VM y sirve también para el paso B.

### Paso B — Arrancar el servidor Django (dentro de la VM)
En la sesión de la VM (la del túnel, u otra sesión SSH):

```bash
cd ~/cowrie-dashboard
source venv/bin/activate
cd cowrie_dashboard
python manage.py runserver 127.0.0.1:8000
```
## pkill -f runserver <---- si esta corriendo
### Paso C — Abrir en el navegador (Windows)
```
http://localhost:8000
```

> Si dice "That port is already in use", el servidor ya está corriendo.
> Para reiniciarlo limpio: `pkill -f runserver` y volver a levantarlo.

---

## 3️⃣ Importar logs manualmente (normalmente NO hace falta)

El cron lo hace solo cada 5 minutos. Si se quiere forzar:

```bash
cd ~/cowrie-dashboard
source venv/bin/activate
cd cowrie_dashboard
python manage.py import_cowrie
```

---

## 4️⃣ Administrar el honeypot Cowrie (systemd)

```bash
sudo systemctl status cowrie      # ver si está corriendo
sudo systemctl restart cowrie     # reiniciar
sudo systemctl stop cowrie        # detener
sudo systemctl start cowrie       # iniciar
sudo journalctl -u cowrie -n 30   # últimas 30 líneas de log del servicio
```

- Cowrie arranca solo al reiniciar la VM (`enable` activo).
- Se reinicia solo si crashea (`Restart=on-failure`).

---

## 5️⃣ Revisar la actividad / ataques

```bash
# Log de importación del cron (cuántos ataques se importan)
cat /home/ubuntu/cowrie-import.log

# Log crudo del honeypot en tiempo real
sudo tail -f /home/cowrie/cowrie/var/log/cowrie/cowrie.json

# Ver la tarea cron programada
crontab -l
```

---

## 6️⃣ Verificar el firewall (si algo falla)

```bash
# Reglas de entrada (deben permitir 22, 2222, 2223 antes del REJECT)
sudo iptables -L INPUT -n --line-numbers

# Regla de redirección 22 → 2223
sudo iptables -t nat -L PREROUTING -n --line-numbers

# Confirmar qué escucha en cada puerto
sudo ss -tlnp | grep -E '22|2223|8000'
```

---

## 🧱 Stack técnico

- **Honeypot:** Cowrie 3.0.1 (SSH honeypot)
- **Backend:** Django 6.0.5 + SQLite
- **Infra:** Oracle Cloud Free Tier (Ubuntu 24.04, región Santiago)
- **Visualización:** Chart.js (gráficos) + Leaflet.js (mapa) + CARTO dark tiles
- **Geolocalización:** ip-api.com (cacheada en BD)
- **Automatización:** systemd (Cowrie) + cron (import cada 5 min)
- **Seguridad:** SSH en puerto no estándar, doble firewall (Oracle + iptables)

---

## 📊 Funcionalidades del dashboard

- Stats en tiempo real (conexiones, IPs únicas, logins éxito/fallo)
- Mapa mundial de IPs atacantes (geolocalizadas)
- Tabla de últimos ataques (IP, usuario, contraseña, país, resultado)
- Top 10 contraseñas y usuarios más intentados
- Gráfico de ataques por hora
- Auto-refresh cada 30 segundos
- Herencia de plantillas Django (base.html)

---

## ⚠️ Recordatorios de seguridad

1. **NUNCA** subir a git: la llave `.key`, el `.env`, la IP pública, `db.sqlite3`.
2. Mi acceso SSH es por el **2222** (el 22 es la trampa del honeypot).
3. La IP pública es **efímera** — si la VM reinicia, verificar en la consola de Oracle.
4. Este README es interno; la versión pública del README NO debe incluir IP, puertos reales ni llaves.