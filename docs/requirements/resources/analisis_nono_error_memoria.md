
# Análisis de Nono sobre error de memoria

Fecha de incorporación al repositorio: 2026-08-25

Diagnóstico claro: tienes razón, ya no lo trataría como puntual. El problema es que nono-sports-garmin-sync.service trabaja demasiado cerca del límite de memoria real de la máquina.

Hechos observados:

• La ejecución diaria normal de Garmin consume de forma repetida unos 1.1-1.2 GB de pico de memoria.
• La máquina tiene 1.8 GiB de RAM.
• El swap es de 4.0 GiB y ahora mismo está prácticamente lleno: unos 3.9 GiB usados.
• No hay un MemoryMax explícito en el servicio de systemd: el límite no parece impuesto por la unidad, sino por la presión real de memoria del sistema.
• Fallos por OOM en Garmin:
  • 15/08/2026 20:53 UTC: OOM tras 1h 03m, pico 1.2 GB.
  • 16/08/2026 19:53 UTC: OOM tras 2m 48s, pico 1.0 GB.
  • 23/08/2026 19:50 UTC: OOM tras 32s, pico 1.1 GB.
• Entre medias hubo ejecuciones correctas del 17 al 22 de agosto, pero siempre muy al límite: 1.1 GB de memoria y entre 825 MB y 1 GB de swap.

Problema técnico probable:

• El flujo de Garmin no solo descarga lo nuevo: después reconstruye normalizado y consolidado completo.
• En código, la normalización carga en memoria listas completas de activities, streams, laps, splits, etc.
• El fichero más pesado es garmin_connect/normalizado/streams.jsonl, con unos 248 MB; al leerlo como objetos Python puede multiplicar varias veces su tamaño en RAM.
• Además el consolidado vuelve a cargar entradas normalizadas de varias fuentes y genera listas completas de actividades, enlaces, índices y duplicados.

Posibles causas contribuyentes:

• Dataset creciente: ahora hay unas 924 actividades Garmin y 1176 actividades consolidadas.
• Diseño batch: se reescriben datasets completos cada noche aunque haya 0 o 1 actividad nueva.
• Presión de memoria ajena a Garmin: hay varios procesos de OpenClaw vivos consumiendo memoria y el swap está saturado.
• I/O sobre Drive/rclone: el fallo del 15/08 duró más de una hora con poco CPU, lo que sugiere posible bloqueo o lentitud de I/O; con memoria retenida durante mucho tiempo aumenta la probabilidad de OOM.
• El horario no parece el problema principal, aunque los domingos hay más automatizaciones deportivas cerca. El OOM también ocurrió en sábado y domingo.

Acciones de mejora que propongo, por orden:

1. Optimización principal en nono-sport: hacer la normalización/consolidación incremental o por streaming, evitando cargar streams.jsonl completo en memoria cuando no hay cambios. Esta es la solución estructural.
2. Separar fases: fetch Garmin, normalización, consolidación y validación en procesos distintos para liberar memoria entre fases.
3. Añadir un preflight de memoria antes del sync: si RAM/swap están demasiado justos, retrasar la ejecución en vez de arrancar y morir por OOM.
4. Reducir presión del runtime: revisar por qué hay varios procesos OpenClaw/MCP vivos y limpiar sesiones/procesos sobrantes antes de la ventana de Garmin.
5. Añadir TimeoutStartSec razonable y mejor logging por fase para distinguir bloqueo de Drive/rclone frente a pico de memoria puro.
6. Como mitigación de infraestructura, subir swap o RAM. Esto ayuda, pero no sustituye la optimización: ahora mismo el job ya opera demasiado cerca del borde.

Mi recomendación: primero instrumentar y optimizar nono-sport para no cargar streams completos si no hay cambios; en paralelo, revisar la acumulación de procesos OpenClaw. No tocaría el horario como primera medida.
