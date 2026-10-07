---
name: compliance-aml-check
description: Verifica compliance AML di un cambiamento di codice del LipariBank
---
# Compliance AML Check — LipariBank

Verifica i cinque controlli antiriciclaggio su ogni cambiamento in revisione:

1. **Soglie operative** — movimenti sopra 10.000 EUR segnalati, sopra 5.000 EUR
   registrati nell'audit
2. **PEP screening** — flag `isPep` e alert sui movimenti sopra 1.000 EUR
3. **Watchlist screening** — `watchlistService.screen(fiscalCode)` alla creazione
   di un cliente
4. **Audit trail** — `correlationId`, `userId`, `ipAddress` ed `executedAt`
   obbligatori
5. **Pattern di operazioni sospette** — smurfing, giri circolari, conti dormienti,
   incoerenza geografica

Usa la skill `review-findings` per il formato dell'output. Non modificare il codice:
riporta le correzioni proposte senza applicarle.
