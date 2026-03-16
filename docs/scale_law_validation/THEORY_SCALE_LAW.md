# Theory of the Scale Law
#
# Author: Vasiliy Zdanovskiy
# email: vasilyvz@gmail.com

## Status

This document is the theory-facing basis for verifying the Scale Law in this project.
It is written strictly from the current Theta-theory corpus and separates:

- canonical statements present in the corpus;
- derived project formulas that follow from those statements;
- reduced testing assumptions that may be checked against an article dataset.

## Theory blocks used

- `7d-60`: global phase-connectivity and the relation between size, time, and phase-transfer speed.
- `7d-103`: frequency ladder of macro modes, `\omega_k = \omega_0 / q^k`.
- `7d-104`: scale similarity, lifetime estimates, and dynamic scale balance through boundary fluxes.
- `7d-105`: the canonical correction `level != scale`; level criterion and clasp window.
- `7d-107`: minimal independent parameters and the status of `Q` as a derived quantity.
- `7d-108`: canonical passport of a level through `{ \omega, c_\Theta, \kappa, L }`.
- `7d-112`: state vector and threshold formulation for transitions between regimes.
- `7d-113`: symmetric ladder of aggregation and the synthesis window for level formation.

## 1. Canonical ontology

The corpus fixes the first non-negotiable statement:

\[
\text{level} \neq \text{scale}.
\]

Scale is a derived observable. Ontological status is determined by the Theta-passport and by the Sigma-ladder regime, not by size alone.

A physical object belongs to the Scale Law only if it is a level-defect rather than an ensemble. From `7d-105`, a level exists only when a clasp window is realized:

\[
\exists \, \Delta t_*:
\quad
\Sigma \to \Sigma^*,
\quad
\nu_{\mathcal Q}\downarrow,
\quad
Q\uparrow,
\quad
N_{\text{mode}}\to 1.
\]

The same corpus also gives the operational level criterion:

\[
\varepsilon_L \ll 1,
\qquad
\tau_{\text{coh}} \gg \tau_{\text{ext}}.
\]

Therefore, the Scale Law is not checked on arbitrary collections of objects. It is checked only on objects that satisfy the level criterion, or on carefully declared proxies of such objects.

## 2. Canonical passport variables

From `7d-108`, the minimal passport of a level is

\[
\mathcal P_n
=
\left\{
\omega_n,\;
c_{\Theta,n},\;
\kappa_n,\;
L_n
\right\}.
\]

From `7d-107`, this minimum may be extended for applied calculations by loss and background terms:

\[
\mathcal P_n^{\text{app}}
=
\left\{
\omega_n,\;
c_{\Theta,n},\;
\kappa_n,\;
L_n,\;
\chi_n'',\;
E_{\text{bg},n}
\right\}.
\]

The same source states that quality factor is not primary. It is derived:

\[
Q_n = \frac{\omega_n}{2\Gamma_n},
\]

where `\Gamma_n` is the effective loss or leakage rate for the mode.

This gives the first strict conclusion for verification:

- the Scale Law must be formulated on primary passport variables first;
- `Q_n` may be used as a coherence diagnostic, but not as the independent generator of the scale ladder.

## 3. Frequency-time-length chain

From `7d-60`, phase propagation over a characteristic size `L` with phase-transfer speed `c_\Theta` gives a characteristic time

\[
t_\Theta \sim \frac{L}{c_\Theta}.
\]

For a resonant mode with carrier `\omega`, the characteristic period obeys

\[
t_\omega \sim \omega^{-1}.
\]

For a stationary level, consistency of these two characteristic times yields the passport relation

\[
L_n \sim \frac{c_{\Theta,n}}{\omega_n}.
\]

This is the project form of the scale relation. It is not an arbitrary dimensional guess: it is the direct closure of the canonical pair

\[
t \sim \frac{L}{c_\Theta},
\qquad
t \sim \omega^{-1}.
\]

Hence the three core observables are tied by

\[
\omega_n L_n \sim c_{\Theta,n}.
\]

When `c_{\Theta,n}` is approximately stable across a selected family, the reduced test form becomes

\[
L_n \propto \omega_n^{-1},
\qquad
t_n \propto \omega_n^{-1}.
\]

This reduced form is admissible only as a testing hypothesis, not as the full canonical law.

## 4. Ladder form of the Scale Law

From `7d-103` and `7d-104`, the corpus explicitly uses a frequency ladder

\[
\omega_{n+1} = \frac{\omega_n}{q},
\qquad q > 1.
\]

Therefore,

\[
\omega_n = \omega_0 q^{-n}.
\]

Using the chain above, the characteristic time ladder is

\[
t_n \sim \omega_n^{-1}
\sim t_0 q^n.
\]

For the length scale:

\[
L_n \sim \frac{c_{\Theta,n}}{\omega_n}
=
\frac{c_{\Theta,n}}{\omega_0} q^n.
\]

If a family admits the reduced approximation

\[
c_{\Theta,n+1} \approx c_{\Theta,n},
\]

then

\[
L_{n+1} \approx q L_n.
\]

In logarithmic form, the verification-ready relations are

\[
\log \omega_n = \log \omega_0 - n\log q,
\]

\[
\log t_n = \log t_0 + n\log q,
\]

\[
\log L_n = \log c_{\Theta,n} - \log \omega_0 + n\log q.
\]

If `c_{\Theta,n}` is approximately constant inside the tested family:

\[
\log L_n = \log L_0 + n\log q.
\]

## 5. Dynamic admissibility of a scale

From `7d-104`, scale dynamics is not free growth. It is controlled by boundary flux balance:

\[
\delta S_\Sigma = 0
\quad \Longrightarrow \quad
\Phi_{\text{in}} - \Phi_{\text{out}} = 0
\]

for a stationary regime, with non-stationary regimes split into expansion, saturation, contraction, or dissolution scenarios.

Therefore, a measured scale may be included in the law only if the article data are compatible with a quasi-stationary regime. If the object is in a transient restructuring phase, it is not a valid anchor for the stationary Scale Law.

## 6. Why ensembles are excluded

From `7d-105`, `7d-106`, `7d-112`, and `7d-113`, ensembles live inside a carrier cell and are described by regime variables such as

\[
\mathrm{PhaseState}
=
(\{\sigma\}, \Pi, Q, \Sigma\text{-class}, \nu_{\mathcal Q}),
\]

not by the minimal level passport alone.

Hence a direct fit of a single geometric ladder across mixed entities such as:

- level-defects,
- ensembles,
- transient cells,
- threshold states,

would violate the corpus.

The Scale Law is meaningful only after ontology filtering:

1. identify whether the article object is a level or an ensemble;
2. keep only level-compatible rows for the primary law;
3. report excluded rows explicitly.

## 7. Verification consequences for an article

The article-based check must therefore answer four questions in order:

1. Does each tested object qualify as a level under the corpus criterion?
2. Can a primary passport be built for it: `\omega`, `c_\Theta` or its proxy, `\kappa` or its proxy, and `L`?
3. Do the article data support a frequency ladder `\omega_n = \omega_0 q^{-n}`?
4. Do the article data support the closure `L_n \sim c_{\Theta,n}/\omega_n`, or at least its reduced constant-`c_\Theta` form?

## 8. Strictly canonical conclusions

The following statements are canonical in the current corpus:

- scale is derived, not ontological;
- only level-defects are valid carriers of the Scale Law;
- the primary passport contains `\omega`, `c_\Theta`, `\kappa`, and `L`;
- `Q` is derived from loss and frequency;
- a ladder form `\omega_n = \omega_0 / q^n` is admissible inside the theory;
- time and length scales follow from the pair `t \sim \omega^{-1}` and `t \sim L / c_\Theta`.

The following statement is a reduced testing hypothesis rather than a standalone theorem:

- `L_n \propto q^n` across a family, which requires approximately stable `c_{\Theta,n}` inside that family.

## 9. Project formula set for validation

The project uses the following formula set for checking the article:

\[
\omega_n = \omega_0 q^{-n},
\qquad
t_n \sim \omega_n^{-1},
\qquad
L_n \sim \frac{c_{\Theta,n}}{\omega_n},
\qquad
Q_n = \frac{\omega_n}{2\Gamma_n}.
\]

Under the reduced constant-`c_\Theta` approximation:

\[
L_n \propto q^n,
\qquad
t_n \propto q^n,
\qquad
\omega_n \propto q^{-n}.
\]

These are the formulas that the new technical specification must test against article data.
