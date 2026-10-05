# Architecture

**Stack:** {{STACK}}. Accepted decisions: [decisions/README.md](decisions/README.md). The stack above counts as
decided: if it has no ADR yet, the first task records it as ADR-0001, as chosen, without deciding it again.

**Current state:** as found at setup and described in `tasks/000-setup/setup.md` (folders, commands, test baseline).
The doc-keeper replaces this paragraph with a short description of the system as it is now once the first task <!-- if:full -->
changes the code, and keeps it current after every task. <!-- if:full -->
Replace this paragraph with a short description of the system as it is now once the first change lands, and keep <!-- if:lite -->
it current after every change. <!-- if:lite -->

## Principles
A starting point: keep, change or delete each one; a change is an ADR the user approves. Each names what enforces it.
1. **Folders say what they are.** The top level holds deployable parts; inside them, folders are named after the layer
   or the domain concept. No `utils2/`, `misc/` or `helpers/` dumping grounds. Enforced by: review of every change.
2. **Business rules live in one place,** free of frameworks, databases, HTTP clients and model SDKs, and are
   unit-tested without I/O. Enforced by: review of every change, until the stack has an import-boundary linter.
3. **Dependencies point inward:** entry points and adapters depend on use cases, use cases on business rules, never
   the reverse. Adapters (storage, external services, models) are replaceable details behind interfaces.
4. **Numbers come from data and deterministic rules,** never from a language model's output.
5. **Tests mirror the layers:** unit tests for the rules, integration tests for adapters, end-to-end tests for the
   user journeys.
6. **Where there is a user interface,** it renders and collects input only: no business rules, and one client module
   for talking to the backend.

## Topic documents
One per area (for example data, API, UI, AI, deployment), created when the first ADR in that area is accepted, and
listed here.

| Area | Document | ADRs |
|---|---|---|

## Project structure
[PROJECT_STRUCTURE.md](PROJECT_STRUCTURE.md): one row per directory with its purpose.
