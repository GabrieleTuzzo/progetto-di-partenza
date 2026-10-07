---
name: review-findings
description: Definisce il formato comune dei rilievi per le review in sola lettura di LipariBank.
---
# Formato comune dei rilievi

Restituisci esclusivamente un array JSON valido, senza testo introduttivo o blocchi
Markdown. Usa un elemento per ogni problema concreto supportato da evidenze nel
codice.

Ogni elemento deve contenere:

- `severity`: uno tra `CRITICAL`, `HIGH`, `MEDIUM`, `LOW`;
- `file`: percorso del file interessato, relativo alla radice del repository;
- `line`: numero di riga intero in cui si trova il problema;
- `finding`: descrizione concisa del problema e della sua conseguenza;
- `proposed_fix`: correzione suggerita, senza applicarla.

Non riportare supposizioni come difetti accertati. Se non ci sono rilievi
concreti, restituisci `[]`.
