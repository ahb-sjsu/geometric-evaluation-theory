/-
Tolerance.lean. Theorem 1(c) of the GET paper (induced distinctions under a length budget).

Indifference at threshold `ε` is a tolerance relation, reflexive and symmetric, and it is not
transitive in general. This file checks both halves of the paper's condition. Three actions
whose distances climb in two steps of at most `ε` but span more than `ε` are a witness to
intransitivity, and when no such chain exists among ordered triples, indifference is
transitive. The second half is proved by cases on the order of the three distances.
-/
import Mathlib
import GET.Semiorder

namespace GET.Tolerance

open GET.Semiorder

variable {A : Type*}

/-- **Intransitivity witness.** Distances `d a ≤ d b ≤ d c` with `d b - d a ≤ ε`,
`d c - d b ≤ ε`, and `ε < d c - d a` give `a ∼ b`, `b ∼ c`, and not `a ∼ c`. -/
theorem not_trans_of_chain (d : A → ℝ) {ε : ℝ} (hε : 0 ≤ ε) {a b c : A}
    (hab : d a ≤ d b) (hbc : d b ≤ d c)
    (h1 : d b - d a ≤ ε) (h2 : d c - d b ≤ ε) (h3 : ε < d c - d a) :
    indiff d ε a b ∧ indiff d ε b c ∧ ¬ indiff d ε a c := by
  unfold indiff
  simp only [abs_le]
  refine ⟨⟨by linarith, by linarith⟩, ⟨by linarith, by linarith⟩, ?_⟩
  intro h
  linarith [h.1]

/-- **Transitivity under the chain condition.** If every ordered triple that is pairwise
indifferent along the chain is indifferent at its ends, then indifference is transitive. The
two cases in which the middle action is an extreme are handled directly. -/
theorem indiff_trans_of_chain (d : A → ℝ) (ε : ℝ)
    (H : ∀ a b c : A, d a ≤ d b → d b ≤ d c →
      indiff d ε a b → indiff d ε b c → indiff d ε a c) :
    ∀ a b c : A, indiff d ε a b → indiff d ε b c → indiff d ε a c := by
  intro a b c hab hbc
  rcases le_total (d a) (d b) with h1 | h1 <;> rcases le_total (d b) (d c) with h2 | h2
  · exact H a b c h1 h2 hab hbc
  · unfold indiff at *
    simp only [abs_le] at *
    constructor <;> linarith [hab.1, hab.2, hbc.1, hbc.2]
  · unfold indiff at *
    simp only [abs_le] at *
    constructor <;> linarith [hab.1, hab.2, hbc.1, hbc.2]
  · exact indiff_symm d ε (H c b a h2 h1 (indiff_symm d ε hbc) (indiff_symm d ε hab))

/-- **Threshold zero is transitive.** At `ε = 0` indifference is equality of distance. -/
theorem indiff_zero_trans (d : A → ℝ) {a b c : A}
    (hab : indiff d 0 a b) (hbc : indiff d 0 b c) : indiff d 0 a c := by
  unfold indiff at *
  simp only [abs_le] at *
  constructor <;> linarith [hab.1, hab.2, hbc.1, hbc.2]

end GET.Tolerance
