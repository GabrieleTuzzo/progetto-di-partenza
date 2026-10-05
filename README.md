# LipariBank — il progetto su cui lavori

Backend REST Spring Boot 3.3 su Java 21, con i tre concetti minimi di una banca: `Customer`, `Account`, `Movement`. Gira, ha un database vero e un'autenticazione vera, ed è la codebase che i tuoi agent leggeranno, recensiranno e interrogheranno per tre giorni.

Il bootcamp **non insegna Spring e non ti chiede di scrivere Java**. Questo progetto è il bersaglio: quello che scrivi tu sta in `.claude/`, in `.opencode/` e negli script che orchestrano gli agent. Il LipariBank è ciò su cui li fai lavorare.

Se arrivi dal Bootcamp Microservizi del catalogo Lipari e hai il tuo LipariBank Multi-Service, usa quello: è più ricco e va benissimo. Questo serve a chi arriva senza un progetto banking in mano, e nessuna giornata dà per scontato che tu abbia l'uno o l'altro.

---

## Farlo partire

Serve Docker. Maven no: il progetto porta il **wrapper**, che al primo uso scarica da sé la versione giusta.

```bash
docker compose up -d          # MySQL 8 sulla 3306, con volume persistente
./mvnw spring-boot:run           # l'applicazione sulla 8080
```

Liquibase crea lo schema e i dati di esempio al primo avvio: due clienti, due conti con saldo, due utenti.

Verifica che risponda:

```bash
curl -s localhost:8080/actuator/health
# → {"status":"UP"}
```

### Autenticarsi e fare un bonifico

Tutto ciò che non è `/api/auth/**` o `/actuator/**` vuole un token.

```bash
TOKEN=$(curl -s -X POST localhost:8080/api/auth/login \
  -H 'Content-Type: application/json' \
  -d '{"username":"alice","password":"alice123"}' \
  | sed -E 's/.*"token":"([^"]+)".*/\1/')

curl -s -X POST localhost:8080/api/movements/transfer \
  -H "Authorization: Bearer $TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{"fromAccountId":1,"toAccountId":2,"amount":100.00,"description":"prova"}'
```

Il secondo utente è `bob` / `bob123`, e i due conti di partenza hanno 1000,00 e 500,00 euro.

### Gli endpoint, tutti quelli che ci sono

| Metodo e percorso | Cosa fa | Token |
| --- | --- | :-: |
| `POST /api/auth/login` | restituisce un JWT dato username e password | no |
| `POST /api/movements/transfer` | trasferisce fra due conti e registra i movimenti | sì |
| `GET /api/movements?accountId=1` | i movimenti di un conto, dal più recente | sì |
| `GET /api/accounts/{id}` | un conto | sì |
| `GET /api/accounts/with-movements` | tutti i conti, ciascuno con i suoi movimenti | sì |
| `GET /actuator/health` | stato dell'applicazione | no |

---

## Com'è fatto

```
progetto-di-partenza/
├── pom.xml
├── Dockerfile
├── docker-compose.yml
├── .gitignore
└── src/
    ├── main/
    │   ├── java/com/lipari/bank/
    │   │   ├── LipariBankApplication.java
    │   │   ├── common/
    │   │   │   ├── CorrelationIdFilter.java      un id di correlazione nell'MDC dei log
    │   │   │   └── GlobalExceptionHandler.java   @RestControllerAdvice
    │   │   ├── customer/       Customer, CustomerRepository
    │   │   ├── account/        Account (saldo in BigDecimal), Repository, Controller
    │   │   ├── movement/       Movement, Repository, Service, Controller, dto/
    │   │   ├── security/       SecurityConfig, JwtFilter, JwtService
    │   │   └── web/            AuthController
    │   └── resources/
    │       ├── application.yml
    │       └── db/changelog/   lo schema e i dati di esempio, in Liquibase
    └── test/
        └── java/com/lipari/bank/TransferIT.java  il caso felice del bonifico
```

Diciannove classi Java, due changeset Liquibase. Il cuore è `MovementService.transfer()`: è il metodo transazionale che sposta il denaro, ed è il posto da cui conviene partire a leggere.

---

## Il repository git

Il progetto arriva come cartella, non come repository, e il `.gitignore` c'è già. Inizializzalo prima di cominciare, perché ogni giornata ti chiede di lavorare per commit:

```bash
git init
git add -A
git commit -m "LipariBank: punto di partenza del bootcamp"
```

---

## Cosa non è

Non è un sistema production-grade, e non pretende di esserlo: non ha circuit breaker, né retry, né audit trail completo, né multi-valuta. Non è multi-servizio: c'è un solo Spring service, che non parla con nessun altro. E non è pronto per un cluster: niente profili per ambiente, niente telemetria, niente probe pensate per la produzione.

Soprattutto: **non è un'architettura modello.** È un backend scritto come lo scrive una squadra sotto scadenza, con le scorciatoie che una squadra sotto scadenza prende. È esattamente per questo che serve: i tuoi reviewer avranno qualcosa di vero da trovare, e quello che troveranno non te l'ha suggerito nessuno.

Per la stessa ragione, se lo riusi fuori dal bootcamp trattalo come codice da recensire, non come codice da mostrare.

## Claude Code Assets

Gli asset di review si trovano in `.claude/`:

`.claude/agents/movement-reviewer.md` | Atomicita', saldi e persistenza dei trasferimenti
`.claude/agents/aml-compliance-reviewer.md` | Soglie, PEP, watchlist, audit e operazioni sospette
`.claude/agents/api-contract-reviewer.md` | Route, DTO, validazione, status e comportamento visibile ai client
`.claude/skills/review-findings/SKILL.md` | Schema JSON uniforme dei rilievi
`.claude/skills/compliance-aml-check/SKILL.md` | Regole AML applicate dal reviewer di compliance
`.claude/settings.json` | Hook preventivo sulle operazioni di modifica

### Regola di instradamento

Il reviewer si sceglie in base alla responsabilita' primaria della modifica, non solo
al nome del file: la logica interna di saldi e trasferimenti compete al reviewer dei
movimenti; una regola AML o normativa al reviewer AML; il comportamento osservabile
dal client al reviewer API.

Nel caso ambiguo di `MovementController.java`, route, request, response, validazione
e codici HTTP competono al reviewer API. Se la modifica implementa una soglia o un
controllo AML, prevale il reviewer AML; la logica transazionale resta al reviewer
dei movimenti. La richiesta deve chiarire quale comportamento e' in revisione.

Esempi: "Rivedi l'atomicita' del trasferimento in `MovementService`" (movimenti);
"Verifica la soglia AML di segnalazione" (AML); "Rivedi la validazione e gli status
HTTP dell'endpoint" (API).

### Sola lettura e verifica

I tre reviewer dichiarano solo `Read`, `Grep` e `Glob`. In `.claude/settings.json`,
un hook `PreToolUse` intercetta `Edit`, `Write` e `NotebookEdit` e termina con codice
2 per rifiutare l'azione; il matcher non include gli strumenti di lettura.

### Modifiche all'impianto ereditato

- Il reviewer generico e' stato sostituito da tre reviewer specializzati, perche'
  combinava perimetri diversi e disponeva di strumenti troppo ampi.
- L'hook `PostToolUse` e lo script di logging sono stati sostituiti da un blocco
  `PreToolUse`.
- La skill AML e' stata limitata agli strumenti di lettura e usa la skill condivisa
  del formato, cosi' non puo' modificare il codice e restituisce findings uniformi.
