# Label Mapping & Taxonomy Documentation

This document specifies the exact mapping between SemEval-2013 Task 7 (SciEntsBank) 5-way labels and AutoRubric's deterministic 4-way evaluation taxonomy.

## 1. Taxonomic Mapping

| SciEntsBank 5-way Label | AutoRubric 4-way Label | Credit Multiplier ($g$) | Operational Definition |
|---|---|:---:|---|
| **`correct`** | `FULL_CREDIT` | `1.0` | Student proposition completely and accurately states the criterion key assertion. |
| **`partially_correct_incomplete`** | `PARTIAL_CREDIT` | `0.5` | Proposition demonstrates partial knowledge or correct reasoning but lacks a necessary mechanism or detail. |
| **`contradictory`** | `MISCONCEPTION` | `0.0` (or penalty) | Proposition asserts an affirmative scientific error or directly contradicts the accepted scientific mechanism. |
| **`irrelevant`** | `NO_CREDIT` | `0.0` | Proposition discusses information that is factually coherent but outside the scope of the rubric criterion. |
| **`non_domain`** | `NO_CREDIT` | `0.0` | Non-responsive text, expressions of confusion (e.g. "I do not know"), or meaningless tokens. |

---

## 2. Key Caveats & Nuances

1. **Contradictory as a Misconception Proxy:**
   - In SciEntsBank, `contradictory` marks statements that directly oppose the reference answer. In educational theory, a *misconception* is a persistent cognitive error rather than a simple negation.
   - We map `contradictory` $\rightarrow$ `MISCONCEPTION` with the caveat that it acts as an operational proxy for false affirmative beliefs.

2. **Negative Marks vs Non-Credit:**
   - In the deterministic scorer (P1), `MISCONCEPTION` defaults to `0.0` credit (or negative credit if configured in `CreditMap`).
   - The annotator draws red bounding boxes around `MISCONCEPTION` evidence to highlight critical learning deficiencies.

3. **Proposition vs Full-Answer Domain Gap:**
   - SciEntsBank contains full student answers (often 1-3 sentences).
   - AutoRubric segments answers into atomic propositions (single assertions).
   - Therefore, propositions sent to the classifier are more focused and shorter than original SciEntsBank responses, significantly reducing model length bias.
