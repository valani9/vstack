# Per-Pattern Starter Templates

This directory contains the smallest runnable demo per pattern — one
file per pattern, each showing:

1. How to import the pattern's analyzer + schema.
2. How to construct the minimal trace shape.
3. How to call the analyzer with `StubClient`.
4. How to print or render the result.

Use these as starter templates when you want to integrate a single
pattern. For end-to-end multi-pattern recipes that chain analyzers,
see `examples/cookbook/`. For pattern-specific deep-dive demos with
full schemas and real-world traces, see each pattern's own
`module-N-X/NN-name/demo/` directory.

Every file in this directory runs without an API key.

## Index

| File                                | Pattern (#NN)                       |
|-------------------------------------|-------------------------------------|
| `01_lewin.py`                       | Lewin Attribution                    |
| `02_goleman_ei.py`                  | Goleman EI Audit                     |
| `03_johari.py`                      | Johari Window                        |
| `04_danva.py`                       | DANVA Emotion Reader                 |
| `05_reappraisal.py`                 | Cognitive Reappraisal                |
| `06_yerkes_dodson.py`               | Yerkes-Dodson Workload               |
| `07_hexaco.py`                      | HEXACO Personality                   |
| `08_grant.py`                       | Grant Strengths-as-Weaknesses        |
| `09_motivation_traps.py`            | Motivation Traps                     |
| `10_sdt.py`                         | SDT Intrinsic Reward                 |
| `11_mcgregor.py`                    | McGregor Orchestrator Mode           |
| `12_vroom.py`                       | Vroom Expectancy                     |
| `13_grpi.py`                        | GRPI Working Agreement               |
| `14_process_gain_loss.py`           | Process Gain/Loss                    |
| `15_social_loafing.py`              | Social Loafing                       |
| `16_heffernan.py`                   | Heffernan Superflocks                |
| `17_lencioni.py`                    | Lencioni 5 Dysfunctions              |
| `18_trust_triangle.py`              | Trust Triangle                       |
| `19_mcallister.py`                  | McAllister Trust Dimensions          |
| `20_edmondson.py`                   | Edmondson Psych Safety               |
| `21_glaser.py`                      | Glaser Conversation Steering         |
| `22_stone_heen.py`                  | Stone-Heen Triggers                  |
| `23_plus_delta.py`                  | Plus-Delta Feedback                  |
| `24_smart_goal.py`                  | SMART Goal Generator                 |
| `25_group_decision.py`              | Group Decision Models                |
| `26_group_pathology.py`             | Group Pathology                      |
| `27_bias_stack.py`                  | Bias Stack                           |
| `28_devils_advocate.py`             | Devil's Advocate Separator           |
| `29_thomas_kilmann.py`              | Thomas-Kilmann                       |
| `30_aar.py`                         | AAR Generator                        |
| `31_schein.py`                      | Schein Iceberg                       |
| `32_robbins_judge.py`               | Robbins-Judge 7-Culture              |
| `33_org_structure.py`               | Org Structure Matrix                 |
| `34_span_of_control.py`             | Span of Control                      |
