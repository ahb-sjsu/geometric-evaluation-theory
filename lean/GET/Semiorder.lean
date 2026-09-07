/-
Semiorder.lean. Theorem 2 of the GET paper (preference from geometry).

A distance `d` to the ideal and a threshold `ε` induce strict preference `a ≻ b` when
`d a + ε < d b` and indifference when `|d a - d b| ≤ ε`. This file checks that the strict
relation is irreflexive, transitive when the threshold is nonnegative, and satisfies the two
semiorder axioms of Luce, so that `(≻, ∼)` is a semiorder whose threshold is the budget. At
threshold zero the relation is the strict part of the weak order represented by `-d`.
-/
import Mathlib

namespace GET.Semiorder

variable {A : Type*}

/-- Strict preference induced by distance `d` and threshold `ε`. -/
def pref (d : A → ℝ) (ε : ℝ) (a b : A) : Prop := d a + ε < d b

/-- Indifference induced by distance `d` and threshold `ε`. -/
def indiff (d : A → ℝ) (ε : ℝ) (a b : A) : Prop := |d a - d b| ≤ ε

/-- Strict preference is irreflexive for a nonnegative threshold. -/
theorem pref_irrefl (d : A → ℝ) {ε : ℝ} (hε : 0 ≤ ε) (a : A) : ¬ pref d ε a a := by
  unfold pref
  linarith

/-- Strict preference is transitive for a nonnegative threshold. -/
theorem pref_trans (d : A → ℝ) {ε : ℝ} (hε : 0 ≤ ε) {a b c : A}
    (hab : pref d ε a b) (hbc : pref d ε b c) : pref d ε a c := by
  unfold pref at *
  linarith

/-- **Semiorder axiom 1.** If `a ≻ b` and `c ≻ e` then `a ≻ e` or `c ≻ b`. -/
theorem pref_axiom1 (d : A → ℝ) (ε : ℝ) {a b c e : A}
    (h1 : pref d ε a b) (h2 : pref d ε c e) : pref d ε a e ∨ pref d ε c b := by
  unfold pref at *
  by_contra h
  have h3 := not_lt.mp (fun hh => h (Or.inl hh))
  have h4 := not_lt.mp (fun hh => h (Or.inr hh))
  linarith

/-- **Semiorder axiom 2.** If `a ≻ b ≻ c` then for every `e`, `a ≻ e` or `e ≻ c`. -/
theorem pref_axiom2 (d : A → ℝ) (ε : ℝ) {a b c : A}
    (h1 : pref d ε a b) (h2 : pref d ε b c) (e : A) : pref d ε a e ∨ pref d ε e c := by
  unfold pref at *
  by_contra h
  have h3 := not_lt.mp (fun hh => h (Or.inl hh))
  have h4 := not_lt.mp (fun hh => h (Or.inr hh))
  linarith

/-- Indifference is reflexive for a nonnegative threshold. -/
theorem indiff_refl (d : A → ℝ) {ε : ℝ} (hε : 0 ≤ ε) (a : A) : indiff d ε a a := by
  unfold indiff
  simpa using hε

/-- Indifference is symmetric. -/
theorem indiff_symm (d : A → ℝ) (ε : ℝ) {a b : A} (h : indiff d ε a b) : indiff d ε b a := by
  unfold indiff at *
  rwa [abs_sub_comm]

/-- **Completeness.** Two actions are strictly ordered one way, the other way, or indifferent. -/
theorem trichotomy (d : A → ℝ) (ε : ℝ) (a b : A) :
    pref d ε a b ∨ pref d ε b a ∨ indiff d ε a b := by
  unfold pref indiff
  by_cases h : d a + ε < d b
  · exact Or.inl h
  by_cases h' : d b + ε < d a
  · exact Or.inr (Or.inl h')
  · right; right
    have h1 := not_lt.mp h
    have h2 := not_lt.mp h'
    rw [abs_le]
    constructor <;> linarith

/-- **Threshold zero is a weak order.** At `ε = 0` strict preference is exactly `d a < d b`,
which is the strict part of the order represented by the utility `-d`. -/
theorem pref_zero_iff (d : A → ℝ) (a b : A) : pref d 0 a b ↔ -d b < -d a := by
  unfold pref
  constructor <;> intro h <;> linarith

end GET.Semiorder
