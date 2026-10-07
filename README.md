# LipariBank — il progetto su cui lavori

Backend REST Spring Boot 3.3 su Java 21, con i tre concetti minimi di una banca: `Customer`, `Account`, `Movement`. Gira, ha un database vero e un'autenticazione vera, ed è la codebase che i tuoi agent leggeranno, recensiranno e interrogheranno per tre giorni.

Il bootcamp **non insegna Spring e non ti chiede di scrivere Java**. Questo progetto è il bersaglio: quello che scrivi tu sta in `.opencode/` e negli script che orchestrano gli agent. Il LipariBank è ciò su cui li fai lavorare.

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

## OpenCode Assets

Gli asset di review si trovano in `.opencode/`:

`AGENTS.md` | Regola di instradamento dei reviewer
`.opencode/agents/movement-reviewer.md` | Atomicita', saldi e persistenza dei trasferimenti
`.opencode/agents/aml-compliance-reviewer.md` | Soglie, PEP, watchlist, audit e operazioni sospette
`.opencode/agents/api-contract-reviewer.md` | Route, DTO, validazione, status e comportamento visibile ai client
`.opencode/skills/review-findings/SKILL.md` | Schema JSON uniforme dei rilievi
`.opencode/skills/compliance-aml-check/SKILL.md` | Regole AML applicate dal reviewer di compliance

### Regola di instradamento

Il reviewer si sceglie in base alla responsabilita' primaria della modifica, non solo
al nome del file. La regola completa e gli esempi sono in `AGENTS.md`.

### Sola lettura e verifica

I reviewer sono subagent OpenCode con permessi espliciti: possono leggere e cercare
nel repository e caricare le skill assegnate, ma non possono modificare file,
eseguire comandi o avviare altri agent. Le restrizioni sono applicate a ciascun
reviewer e non bloccano l'agente Build.

### Modifiche all'impianto ereditato

- I tre reviewer specializzati possono essere invocati con `@movement-reviewer`,
  `@aml-compliance-reviewer` e `@api-contract-reviewer`.
- La skill AML richiama la skill condivisa del formato, cosi' i rilievi seguono uno
  schema uniforme.

### Server MCP locale

#### Decisione: Tool, Resource e sicurezza

Espongo come **Tool** la lettura di un saldo, la lettura di una lista limitata di
movimenti e la simulazione di un trasferimento: sono operazioni invocabili che
leggono lo stato live o calcolano una proiezione. Espongo come **Resource** i
riferimenti normativi e il contratto API locale, perché sono contenuti consultivi
in sola lettura. **Non espongo un tool che esegue bonifici**: per test end-to-end
proporrei un backend e un database di test isolati, con conti fittizi e resettable.

Il riferimento normativo locale riassume la Direttiva (UE) 2015/2366 (PSD2),
articolo 64, e rimanda a EUR-Lex; è una fonte citabile, non una valutazione legale.
Non disciplina il calcolo aritmetico del saldo. Le resources sono caricate da file
accanto al server a runtime:

- `finbank://regulations/psd2-payment-authorization`
- `finbank://reference/liparibank-api`

#### Strumenti esposti

- `get_account_balance(account_id)`: restituisce ID, saldo, valuta e stato, senza
  IBAN o identificativi del cliente.
- `get_recent_movements(account_id, limit=5)`: restituisce i movimenti più recenti,
  con limite massimo lato MCP di 10; omette la descrizione.
- `simulate_transfer(source_account_id, target_account_id, amount)`: legge i due
  conti e calcola saldi prima/dopo usando `Decimal`. Non invoca mai l'endpoint POST
  dei trasferimenti e dichiara l'insufficienza fondi senza proiezioni fuorvianti.

L'API di movimenti del backend non è paginata: il server MCP tronca la lista prima
di inviarla al client, ma per limitare anche il traffico backend serve introdurre
paginazione nell'API.

#### Avvio e autenticazione

Le API di conto e movimenti sono protette. Il server ottiene un JWT con il login
usando le credenziali ricevute dall'ambiente; il token resta in memoria ed è
rinnovato una volta se il backend risponde 401. Il server non accetta credenziali
come argomenti dei tool e non le salva nel repository. Per il database demo locale
si possono usare `alice` / `alice123`; questa è un'identità utente dimostrativa,
non una vera utenza di servizio né un'identità read-only. In un ambiente condiviso
va predisposto un utente di servizio dedicato con permessi minimi. In PowerShell:

```powershell
py -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
$env:FINBANK_USERNAME = "alice"
$env:FINBANK_PASSWORD = "alice123"
.\.venv\Scripts\python.exe .\finbank-mcp\server.py
```

Usare un utente con i soli permessi di lettura; il backend di esempio non distingue
ruoli di sola lettura, quindi in questo repository le credenziali dedicate
identificano il servizio ma non introducono da sole un'autorizzazione read-only.
Il confine di sicurezza effettivo è che il server implementa solo richieste GET
alle API di conto e movimenti (oltre al POST di login) e non contiene una chiamata
al percorso di trasferimento.

La configurazione OpenCode è in `.opencode/opencode.json`; `.mcp.json` alla radice
configura lo stesso processo per i client che supportano `mcpServers`. Entrambi
usano STDIO e richiedono che le variabili di ambiente siano presenti nel processo
che avvia il client. L'avvio HTTP alternativo di `run.sh` è vincolato a `127.0.0.1`;
non cambiarlo in `0.0.0.0` senza aggiungere autenticazione in ingresso e controlli
di accesso. Con MCP Inspector si può avviare il comando Python del virtualenv
con `finbank-mcp/server.py`, quindi verificare i tre tool, le due resources e il
prompt `review_movement_change`; invocare `simulate_transfer` non deve cambiare i
saldi. Gli ID di esempio 1 e 2 vanno verificati sul backend effettivamente avviato.

Il reviewer `movement-reviewer` ha in allowlist i tre tool read-only. Il suo prompt
gli richiede di usarli quando la review dipende dallo stato corrente e di leggere
la resource normativa prima di citare una regola. La prova dell'uso effettivo è la
traccia delle invocazioni MCP della review, non il solo testo del finding; in questo
ambiente non è stata eseguita una sessione OpenCode reviewer.

#### Risposta al cliente SaaS multi-tenant

Direzione promettente, ma non esporrei questo server locale così com'è come SaaS.
1. Ogni cliente richiede identità autenticata, scope e isolamento verificato lato server: un account del tenant A non deve essere leggibile dal tenant B.
2. Non esporrei tool con side effect cross-tenant; ogni invocation deve avere audit con tenant, utente e correlation ID.
3. Le versioni dei contratti devono poter coesistere, per esempio `/mcp/v1` e `/mcp/v2`, con semver e migrazione esplicita.
4. Servono anche rate limit, gestione dei segreti, telemetria, disponibilità e test di isolamento.
5. Stimerei 3-6 mesi di lavoro di team prima di dichiararlo SaaS-ready; valuterei l'investimento solo con domanda concreta da almeno 5-10 clienti potenziali.

## Static Analysis cards

Il reviewer ereditato `code-reviewer.md` e' stato sostituito dai tre reviewer specializzati in `.opencode/agents/`.

I reviewer specializzati sono configurati in modalita' di sola lettura tramite i permessi OpenCode.
Le skill OpenCode sono caricabili dai reviewer attraverso i permessi assegnati.
