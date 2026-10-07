# Contratto API LipariBank usato dagli strumenti di review

Fonte locale: `README.md`, `AccountController`, `MovementController` e `TransferRequest`.

- `GET /api/accounts/{id}` restituisce il conto, compresi saldo (`balance`), valuta (`currency`) e stato (`status`).
- `GET /api/movements?accountId={id}` restituisce i movimenti del conto in ordine dal più recente; l'API attuale non accetta un parametro di paginazione.
- Le API sopra richiedono un bearer token JWT ottenuto da `POST /api/auth/login`.
- La richiesta di trasferimento del backend usa `fromAccountId`, `toAccountId`, `amount` e `description`. Il server MCP di review non chiama l'endpoint di trasferimento.

Gli strumenti MCP selezionano solo i campi necessari. `get_recent_movements` restituisce al massimo 10 record anche se il backend restituisce una lista più lunga. La lista viene troncata prima di essere restituita al client MCP; per paginare anche il traffico tra MCP e backend occorre aggiungere la paginazione all'API LipariBank.
