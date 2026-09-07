/-
Reversal.lean. Theorem 5 of the GET paper (resolution reversal).

The example of the paper. Two actions with consequences `(1, 0)` and `(0.9, 2)`, an ideal at
the origin, and the identity metric. An evaluator resolving only the first coordinate has
distances `1` and `0.9` and prefers the second action. An evaluator resolving both has
distances `1` and `√4.81` and prefers the first. No single real function represents both
orders. The file checks the two inequalities and the impossibility.
-/
import Mathlib

namespace GET.Reversal

/-- The budgeted distances of the example. At rank one, `0.9 < 1`. -/
theorem rank_one_prefers_b : (0.9 : ℝ) < 1 := by norm_num

/-- At rank two, `1 < √(0.81 + 4)`. -/
theorem rank_two_prefers_a : (1 : ℝ) < Real.sqrt (0.81 + 4) := by
  rw [Real.lt_sqrt (by norm_num)]
  norm_num

/-- **No common utility.** No function on the actions represents an order in which `b` beats
`a` and also an order in which `a` beats `b`. -/
theorem no_common_utility {A : Type*} (a b : A) :
    ¬ ∃ u : A → ℝ, u a < u b ∧ u b < u a := by
  rintro ⟨u, h1, h2⟩
  linarith

end GET.Reversal
