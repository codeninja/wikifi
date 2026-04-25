## Integrations

Internal and external touchpoints and handoffs.


### Touchpoints

- Main coordinates handoffs between user commands and internal processing stages.
- Aggregation coordinates handoffs between user commands and internal processing stages.
- Cli coordinates handoffs between user commands and internal processing stages.
- Constants coordinates handoffs between user commands and internal processing stages.
- Derivation coordinates handoffs between user commands and internal processing stages.
- Introspection coordinates handoffs between user commands and internal processing stages.
- Orchestrator coordinates handoffs between user commands and internal processing stages.
- Reporting coordinates handoffs between user commands and internal processing stages.
- Text coordinates handoffs between user commands and internal processing stages.
- Workspace coordinates handoffs between user commands and internal processing stages.

### Behavioral Handoff

| Clause | Statement |
| --- | --- |
| Given | A user invokes the command interface. |
| When | The orchestrator receives the request. |
| Then | It delegates work through introspection, extraction, aggregation, and derivation in sequence. |

