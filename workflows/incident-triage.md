# Workflow: Incident Triage (síntoma -> causa raíz)

Entrada para cuando el operador reporta un **síntoma** (no "haceme un audit", sino
"el sitio da 502", "el disco se llenó", "un contenedor se reinicia solo"). El objetivo
es llegar a la **causa raíz** y una **remediación**, no listar todo el inventario.

Data-driven: este workflow lee `lib/diagnosis.yaml` (mapa síntoma -> hipótesis -> evidencia
-> skills) y ejecuta **solo** los skills que ese síntoma requiere. No hay lógica hardcodeada:
agregar un síntoma nuevo es editar `diagnosis.yaml`.

## Entrada mínima

| Variable | Requerido | Descripción |
|----------|-----------|-------------|
| `SYMPTOM` | si | El síntoma reportado (p.ej. "502 en descubrisannicolas.com.ar") |
| `SSH_TARGET` | si | `user@host` o alias configurado |

## Loop

```
1. NORMALIZAR el síntoma -> mapear a un id de diagnosis.yaml
     (502 -> http_5xx/502_bad_gateway, cert -> cert_error, etc.)
     |
     v
2. LEER diagnosis.yaml: obtener la lista ordenada de hipótesis para ese id.
     |
     v
3. POR CADA hipótesis (en orden de probabilidad):
     - mirar qué evidence necesita y qué skills la producen
     - si la evidencia ya existe en reportes/<run-id>/, usarla; si no, correr el skill
     - correr la prueba confirmatoria NO destructiva ("confirm")
     - si se confirma -> causa raíz encontrada; salir
     - si se descarta -> pasar a la siguiente hipótesis
     |
     v
4. VERIFICAR con una segunda fuente (anti-falso-positivo):
     evidencia + contexto + exposición + impacto (lib/severity.md)
     |
     v
5. GENERAR el finding (FACT/OBSERVATION/HYPOTHESIS/RISK) + severidad + confianza
     |
     v
6. GENERAR la remediación (WHAT/WHY/HOW/RISK/PRIORITY/VALIDATION/ROLLBACK)
     - si requiere Level 3 -> STOP, DOCUMENTAR, PEDIR APROBACIÓN
     |
     v
7. REPORTAR: causa raíz + evidencia + remediación (resumen en consola)
```

## Reglas duras

1. **Read-only hasta el final.** El diagnóstico NUNCA arregla solo. Si la confirmación
   o la remediación es Level 3, se documenta y se pide aprobación (SAFETY.md).
2. **Evidencia primero.** Ninguna hipótesis se da por confirmada sin un registro de
   evidencia almacenado.
3. **Anti-falso-positivo.** Una hipótesis es una *hipótesis* hasta que la prueba
   confirmatoria (no destructiva) la valida. 1 snapshot no es tendencia.
4. **Skills, no código.** Cada "how" de `diagnosis.yaml` referencia skills existentes;
   si un síntoma necesita un skill que no existe, generarlo (WORKFLOW.md paso 6).
5. **No asumir arquitectura.** El 502 puede ser Apache, nginx, o un ingress de K8s;
   dejar que `web_server_analysis` / `ingress_nginx_analysis` lo descubran.

## Ejemplo: "502 en el sitio"

```
síntoma -> http_5xx
hipótesis 1: upstream caído
  -> correr web_server_analysis (proxy map + upstream health)
  -> confirm: curl al upstream -> 000 (refused)
  -> verificar: docker ps -a + curl al container-IP -> nada escuchando
  -> causa raíz: contenedor 'up' pero proceso Rails muerto (sin swap -> OOM)
  -> remediación: reiniciar contenedor + habilitar swap (Level 3 -> pedir aprobación)
```

## Directorio de reportes

Igual que el audit: evidencia en `reportes/<run-id>/evidencia/`, hallazgos en
`reportes/<run-id>/findings.yaml`. Reutiliza el mismo `run-id` si ya existía una corrida.
