# 🔍 Cómo funciona el proyecto — Explicación detallada

> Cowrie Threat Dashboard: honeypot SSH + dashboard de análisis.
> Documento para entender y poder explicar cada pieza del sistema.

---

## 1. La idea en una frase

Pusimos un **servidor trampa** (honeypot) en internet que finge ser un servidor
SSH vulnerable. Los atacantes automatizados de todo el mundo lo encuentran, "entran",
y todo lo que hacen queda registrado. Un **dashboard** lee esos registros y los
muestra como una consola de análisis (mapa, estadísticas, comandos, malware).

---

## 2. El recorrido completo de un ataque (de principio a fin)

Esta es la cadena que sigue cada ataque. Entender esto es entender el proyecto:

```
1. Un bot escanea internet y encuentra tu IP con el puerto 22 abierto
        ↓
2. Intenta entrar por SSH (prueba usuario/contraseña)
        ↓
3. El firewall redirige ese tráfico del puerto 22 al 2223 (donde escucha Cowrie)
        ↓
4. Cowrie finge ser un servidor real: acepta el login y simula una terminal Linux
        ↓
5. El atacante ejecuta comandos / descarga malware, creyendo que es real
        ↓
6. Cowrie registra TODO en un archivo de log (cowrie.json)
        ↓
7. Cada 5 minutos, un proceso lee ese log y lo guarda en la base de datos
        ↓
8. El dashboard consulta la base de datos y lo muestra en pantalla
        ↓
9. Tú lo ves desde tu PC a través de un túnel SSH seguro
```

---

## 3. Las piezas del sistema (y qué hace cada una)

### 3.1 El servidor (Oracle Cloud)
Una máquina virtual gratuita con Ubuntu 24.04 e **IP pública**. La IP pública es
lo esencial: sin ella, los atacantes no podrían llegar. Es una máquina desechable
y aislada, separada de tu PC personal — si algo sale mal, no afecta tus equipos.

### 3.2 Cowrie (el honeypot)
Es el corazón de la trampa. Cowrie es un **honeypot SSH de media interacción**:
- "Media interacción" = emula un sistema Linux falso. El atacante puede escribir
  comandos y recibe respuestas creíbles, pero **nunca toca el sistema real**.
- Acepta casi cualquier usuario/contraseña a propósito (para dejar entrar al
  atacante y observar qué hace).
- Cada evento (conexión, login, comando, descarga) lo escribe como una línea
  JSON en `cowrie.json`.
- Corre como un **servicio systemd**: arranca solo al encender la VM y se
  reinicia si se cae. Por eso captura 24/7 sin que toques nada.

### 3.3 El firewall y los puertos (la parte de redes)
Hay un juego de puertos clave para que esto funcione de forma segura:

| Puerto | Para qué |
|--------|----------|
| 22 (externo) | La **trampa**: aquí llegan los atacantes |
| 2223 (interno) | Donde **escucha Cowrie** realmente |
| 2222 | Tu **SSH de administración** (el de verdad, el tuyo) |
| 8000 | El dashboard (solo local, se ve por túnel) |

El truco: el firewall (iptables) **redirige** el tráfico del puerto 22 al 2223.
Así los atacantes pegan en el 22 (creyendo que es SSH normal) y caen en Cowrie.
Mientras, tú entras por el 2222, separado y seguro. Esto se llama **redirección
de puertos (NAT)** y es un concepto de redes.

### 3.4 El dashboard (Django)
La aplicación web que construiste. Tiene varias partes:

- **Modelos** (`models.py`): definen las tablas de la base de datos
  (Connection, LoginAttempt, Command, FileDownload, Session). Cada uno guarda
  un tipo de evento.
- **El comando de importación** (`import_cowrie.py`): lee el `cowrie.json`,
  interpreta cada línea y la guarda en la tabla correspondiente.
- **Vistas** (`views.py`): consultan la base de datos y preparan los datos.
- **Templates** (HTML): muestran los datos como páginas (dashboard, ataques,
  estadísticas, forense).
- **El admin de Django**: panel automático para ver los datos crudos.

---

## 4. Cómo entran los datos a la base (el pipeline)

Esta es la parte más importante de entender técnicamente.

### Paso 1 — Cowrie escribe el log
Cada ataque genera líneas como esta (simplificada):
```json
{"eventid":"cowrie.login.success","username":"root","password":"123456","src_ip":"1.2.3.4"}
```

### Paso 2 — El comando import_cowrie lo procesa
El comando abre el archivo y lee **línea por línea**. Por cada línea:
1. La convierte de texto JSON a un objeto Python (`json.loads`).
2. Mira el campo `eventid` para saber qué tipo de evento es.
3. Según el tipo, lo guarda en la tabla correcta:
   - `cowrie.session.connect` → tabla **Connection**
   - `cowrie.login.success/failed` → tabla **LoginAttempt**
   - `cowrie.command.input` → tabla **Command**
   - `cowrie.session.file_download` → tabla **FileDownload**
   - `cowrie.client.version/kex` → tabla **Session**

### Paso 3 — El truco para no duplicar (get_or_create)
El comando re-lee el archivo **completo** cada vez que corre. ¿Por qué no se
duplican los datos? Porque usa `get_or_create` con una **restricción única**:
"si este evento exacto ya existe en la base, no lo insertes de nuevo". Así puedes
correr el import mil veces y solo entran los eventos nuevos.

### Paso 4 — La automatización (cron)
Un **cron** (tarea programada de Linux) ejecuta el import **cada 5 minutos**:
```
*/5 * * * * ... python manage.py import_cowrie
```
Por eso los datos se actualizan solos, sin que toques nada.

---

## 5. Cómo se muestra todo (la actualización "casi en tiempo real")

Hay DOS mecanismos de actualización trabajando juntos:

1. **El cron (datos)**: cada 5 minutos mete los ataques nuevos a la base.
2. **El auto-refresh (pantalla)**: el dashboard tiene JavaScript que cada 30
   segundos vuelve a pedir los datos a un endpoint (`/api/stats/`) y refresca la
   pantalla sin recargar la página.

Por eso decimos "casi en tiempo real": no es instantáneo (eso sería WebSockets),
pero los ataques aparecen con pocos minutos de retraso, automáticamente.

```
Ataque → cowrie.json (al instante)
       → import vía cron (hasta 5 min después)
       → base de datos
       → dashboard se refresca solo (cada 30 seg)
```

---

## 6. Funciones extra del dashboard

### 6.1 Geolocalización del mapa
Cuando llega una IP nueva, el sistema consulta una API gratuita (ip-api.com) que
devuelve el país y las coordenadas de esa IP. El resultado se **guarda en la base**
(se cachea) para no consultar la misma IP dos veces. El mapa (Leaflet.js) dibuja
un punto por cada IP geolocalizada.

### 6.2 Análisis forense
La vista forense muestra lo más valioso: los **comandos** que ejecutaron los
atacantes, los **archivos que descargaron** (con su hash SHA256, que son IOCs) y
el **fingerprint** del cliente SSH que usaron.

### 6.3 Análisis de malware (VirusTotal)
Un script aparte toma los hashes de los archivos descargados y los consulta en
VirusTotal, que dice si son malware conocido y de qué familia. Así identificamos
muestras como RedTail (criptominero) o el discord-exploit.

---

## 7. Cómo lo ves tú de forma segura (el túnel SSH)

El dashboard NO está expuesto a internet (sería peligroso). Corre solo en el
puerto 8000 **local de la VM**. Para verlo desde tu PC usas un **túnel SSH**:

```
ssh -L 8000:127.0.0.1:8000 ...
```

Esto crea un "tubo cifrado" entre el puerto 8000 de tu PC y el 8000 de la VM.
Cuando abres `http://localhost:8000` en tu navegador, el tráfico viaja por ese
tubo seguro hasta el dashboard. Nadie más puede acceder.

Necesitas dos cosas activas a la vez:
- Una terminal con el **servidor corriendo** (en la VM).
- Otra terminal con el **túnel abierto**.

---

## 8. Resumen para explicarlo en 30 segundos

> "Monté un honeypot: un servidor falso en internet que finge ser vulnerable.
> Los atacantes entran y Cowrie graba todo lo que hacen en un log. Un proceso
> automático lee ese log cada 5 minutos y lo guarda en una base de datos. Un
> dashboard en Django consulta esa base y muestra los ataques en un mapa, con
> estadísticas y un módulo forense que revela los comandos y el malware que
> usaron. Yo lo veo de forma segura por un túnel SSH. En dos semanas capturó
> más de 25.000 ataques reales."

---

## 9. Tecnologías y qué aporta cada una

| Tecnología | Rol en el proyecto |
|------------|--------------------|
| **Cowrie** | El honeypot que captura los ataques |
| **Oracle Cloud** | El servidor con IP pública (la trampa) |
| **iptables** | Redirige puertos y protege (firewall) |
| **systemd** | Mantiene Cowrie corriendo 24/7 |
| **cron** | Importa los logs cada 5 minutos |
| **Django** | El framework del dashboard (modelos, vistas, admin) |
| **SQLite** | La base de datos donde se guardan los ataques |
| **Leaflet.js** | El mapa de atacantes |
| **Chart.js** | Los gráficos de estadísticas |
| **ip-api.com** | Geolocalización de las IPs |
| **VirusTotal** | Identificación del malware capturado |
| **MITRE ATT&CK** | Marco para clasificar las técnicas de ataque |

---

## 10. Por qué cada decisión tiene sentido (para defenderlo)

- **¿Por qué Django y no FastAPI?** Porque es una app web con páginas, admin y
  base de datos — territorio natural de Django. FastAPI es para APIs puras.
- **¿Por qué guardar en base de datos y no leer el log directo?** Por velocidad y
  para poder filtrar, contar y geolocalizar sin reprocesar todo cada vez.
- **¿Por qué en la nube y no en casa?** Por seguridad (aislamiento) y porque
  necesitaba IP pública, que el router doméstico no daba.
- **¿Por qué Cowrie acepta cualquier login?** Es su diseño: dejar entrar al
  atacante para observar su comportamiento, no rechazarlo.
