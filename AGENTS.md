# Regola di instradamento

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

Se un diff contiene modifiche indipendenti appartenenti a più perimetri, richiedi review separate e mirate sullo stesso diff, una per reviewer. Ogni singola richiesta deve avere un solo ambito; non chiedere a un reviewer di coprire anche quello degli altri.
