# Technical Specification: Scale Law Verification
#
# Author: Vasiliy Zdanovskiy
# email: vasilyvz@gmail.com

## 1. Purpose

This specification defines a project for verifying the Scale Law against a source article while staying inside the current Theta-theory canon.

The project must test whether the article data are consistent with the canonical chain

\[
\omega_n = \omega_0 q^{-n},
\qquad
t_n \sim \omega_n^{-1},
\qquad
L_n \sim \frac{c_{\Theta,n}}{\omega_n},
\]

and must explicitly separate:

- canonical theory statements;
- article-derived observables;
- reduced assumptions used only for testing.

## 2. Scope

In scope:

- ingest article data and article metadata;
- classify article objects into level-compatible and excluded rows;
- build a verification-ready passport table;
- test frequency, time, and scale relations;
- produce a final validation report.

Out of scope:

- synthetic augmentation of the article dataset;
- testing objects that remain ontologically undefined;
- mixing level-defects and ensembles into one undifferentiated fit;
- introducing classical models unless separately approved by the user.

## 3. Canonical Basis

The project is anchored to the following theory blocks:

- `7d-60`: size-time-phase-speed relation;
- `7d-103`: ladder form `\omega_k = \omega_0 / q^k`;
- `7d-104`: scale similarity and stationary balance;
- `7d-105`: `level != scale`, level criterion, clasp window;
- `7d-107`: minimal independent parameters and derived `Q`;
- `7d-108`: canonical level passport `{ \omega, c_\Theta, \kappa, L }`;
- `7d-112`: threshold and state-vector logic;
- `7d-113`: synthesis window and symmetric aggregation ladder.

The companion theory file `docs/scale_law_validation/THEORY_SCALE_LAW.md` is the authoritative explanatory layer for this specification.

## 4. Source Policy

The source article is the only observational authority for this project unless the user adds another explicit dataset.

Allowed inputs:

- the article itself;
- tables extracted from the article;
- figures digitized from the article if the extraction path is documented;
- user-supplied supplemental files tied to the same article.

Forbidden inputs:

- invented rows;
- literature averages not present in the article;
- hidden fill values for missing observables;
- merging unrelated datasets without explicit user approval.

## 5. Ontology Filter

Before any regression or ladder fit, each article object must be assigned one of the following statuses:

- `level_candidate`
- `ensemble_excluded`
- `transient_excluded`
- `insufficient_data`

The assignment must follow the canonical rule from `7d-105`:

\[
\varepsilon_L \ll 1,
\qquad
\tau_{\text{coh}} \gg \tau_{\text{ext}}.
\]

If the article does not directly provide these quantities, the project may use declared proxies, but every proxy must be named and justified in the report.

Rows that cannot be justified as level-compatible must not enter the primary Scale Law fit.

## 6. Required Inputs

The project input set must contain:

1. `article_source`
   Full citation or file reference to the article.

2. `article_objects`
   Row-level object list extracted from the article.

3. `observable_map`
   A declared mapping from article columns to project observables.

4. `unit_map`
   Units and normalization rules for every imported field.

5. `provenance_manifest`
   Source, page, figure, table, extraction method, and timestamp for each imported block.

## 7. Verification Passport

The core output row is the verification passport:

\[
\mathcal P_n^{\text{verify}}
=
\{
\text{object\_id},
\text{ontology\_status},
\omega,
t,
L,
c_\Theta^{\text{proxy}},
\kappa^{\text{proxy}},
\Gamma^{\text{proxy}},
Q,
n,
q^{\text{local}},
\text{source\_ref}
\}.
\]

### 7.1. Primary fields

Required whenever available:

- `omega`
- `t`
- `L`
- `source_ref`
- `ontology_status`

### 7.2. Derived fields

Computed when inputs are sufficient:

\[
t_{\text{derived}} = \omega^{-1},
\qquad
Q = \frac{\omega}{2\Gamma},
\qquad
c_{\Theta}^{\text{derived}} = \omega L,
\qquad
q_{i \to j} = \frac{\omega_i}{\omega_j}.
\]

### 7.3. Missingness rule

Missing fields must stay missing.
No derived field may be emitted if one of its parents is absent.

## 8. Verification Hypotheses

The project must test the hypotheses in the following order.

### H1. Frequency ladder

\[
\omega_n = \omega_0 q^{-n}.
\]

Operational check:

- linearity of `\log \omega_n` versus level index `n`;
- stability of estimated `q`;
- residual report per row.

### H2. Time-frequency closure

\[
t_n \sim \omega_n^{-1}.
\]

Operational check:

- consistency between article time observable and inverse frequency;
- multiplicative residuals in linear and log space.

### H3. Full scale relation

\[
L_n \sim \frac{c_{\Theta,n}}{\omega_n}.
\]

Operational check:

- estimate `c_{\Theta,n}^{\text{derived}} = \omega_n L_n`;
- test whether the derived values stay structured rather than random;
- report whether a single-family approximation is admissible.

### H4. Reduced constant-phase-speed form

This hypothesis is tested only after `H3`:

\[
c_{\Theta,n+1} \approx c_{\Theta,n}
\quad \Longrightarrow \quad
L_n \propto q^n.
\]

This must be reported as a reduced approximation, not as the base theorem.

## 9. Processing Stages

The project must execute the following stages.

### Stage 1. Source intake

- register the article;
- extract tables, figures, and metadata;
- write provenance manifest.

### Stage 2. Normalization

- standardize units;
- standardize identifiers;
- keep page, figure, and table references.

### Stage 3. Ontology assignment

- assign `level_candidate` or exclusion status;
- record the reason for every exclusion.

### Stage 4. Passport construction

- build the verification passport;
- compute only justified derived fields;
- preserve missingness.

### Stage 5. Law verification

- test `H1`, `H2`, `H3`, and optionally `H4`;
- emit row-level residuals and aggregate diagnostics.

### Stage 6. Final report

- produce a human-readable report;
- produce machine-readable tables;
- state whether the article supports, partially supports, or does not support the Scale Law.

## 10. Required Outputs

The project must produce the following outputs in a dedicated run directory:

- `source_manifest.csv`
- `article_objects_normalized.csv`
- `scale_law_verification_passports.csv`
- `scale_law_fit_summary.csv`
- `scale_law_residuals.csv`
- `scale_law_validation_report.md`

## 11. Report Contract

The markdown report must contain:

1. article identity and provenance;
2. theory blocks used;
3. ontology filter summary;
4. count of included and excluded rows;
5. tested hypotheses;
6. fit diagnostics and residual summaries;
7. statement about full-law support;
8. statement about reduced-law support;
9. explicit list of theory gaps or article gaps.

## 12. Non-Negotiable Rules

- No synthetic data.
- No hidden interpolation.
- No ontology mixing in the primary fit.
- No replacement of missing `c_\Theta` with the speed of light or any unrelated constant.
- No use of `Q` as a primary passport parameter.
- No statement of confirmation unless supported by emitted diagnostics.

## 13. Acceptance Criteria

The implementation is acceptable only if all points below are true.

1. Every included row has source provenance.
2. Every excluded row has an explicit exclusion reason.
3. Every derived field has its parent fields present.
4. The report distinguishes full-law support from reduced-law support.
5. The report distinguishes theory-backed claims from test-only approximations.
6. The final dataset contains no synthetic or silently filled values.

## 14. Failure Conditions

The run must be considered failed if any of the following occurs:

- article provenance is incomplete;
- ontology status is missing for any normalized row;
- reduced-law claims are reported as canonical facts;
- derived fields are emitted from absent parents;
- included rows cannot be traced back to article evidence.
