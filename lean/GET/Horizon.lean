/-
The window bound of the observational Lyapunov exponent.
Companion to Proposition 1 (positive definite case) of
`articles/2026-09-09-identifiability-at-a-budget.md` and to bar E1 of gate D3 of the OD track.

If the observational squared length `q = δ ⬝ᵥ P δ` is pinched between `a` and `b` times the
Euclidean squared length `x = δ ⬝ᵥ δ` at both ends of a window, then the observational and the
classical log-growths differ by at most `log (b / a) / 2`, and the window exponents by at most
`log (b / a) / (2 T)`.
-/
import Mathlib
import GET.Identifiability

namespace GET

open Matrix

variable {n : ℕ}

/-- Scalar form: two squared lengths pinched by the same factors at both ends of a window. -/
theorem window_bound_scalar {a b x₀ x₁ q₀ q₁ : ℝ} (ha : 0 < a) (hx₀ : 0 < x₀) (hx₁ : 0 < x₁)
    (h₀ : a * x₀ ≤ q₀ ∧ q₀ ≤ b * x₀) (h₁ : a * x₁ ≤ q₁ ∧ q₁ ≤ b * x₁) :
    |(Real.log q₁ - Real.log q₀) / 2 - (Real.log x₁ - Real.log x₀) / 2|
      ≤ Real.log (b / a) / 2 := by
  have hab : a ≤ b := le_of_mul_le_mul_right (h₀.1.trans h₀.2) hx₀
  have hb : 0 < b := lt_of_lt_of_le ha hab
  have hq₀ : 0 < q₀ := lt_of_lt_of_le (mul_pos ha hx₀) h₀.1
  have hq₁ : 0 < q₁ := lt_of_lt_of_le (mul_pos ha hx₁) h₁.1
  have key : ∀ {x q : ℝ}, 0 < x → 0 < q → a * x ≤ q → q ≤ b * x →
      Real.log a ≤ Real.log q - Real.log x ∧ Real.log q - Real.log x ≤ Real.log b := by
    intro x q hx hq hl hu
    constructor
    · have := Real.log_le_log (mul_pos ha hx) hl
      rw [Real.log_mul ha.ne' hx.ne'] at this
      linarith
    · have := Real.log_le_log hq hu
      rw [Real.log_mul hb.ne' hx.ne'] at this
      linarith
  obtain ⟨l₀, u₀⟩ := key hx₀ hq₀ h₀.1 h₀.2
  obtain ⟨l₁, u₁⟩ := key hx₁ hq₁ h₁.1 h₁.2
  rw [Real.log_div hb.ne' ha.ne', abs_le]
  constructor <;> linarith

/-- The window bound for a read operator whose form is pinched between `a` and `b` times the
Euclidean form: the observational and classical log-growths over a window differ by at most
`log (b / a) / 2`. -/
theorem window_bound (P : Matrix (Fin n) (Fin n) ℝ) {a b : ℝ} (ha : 0 < a)
    (hP : ∀ v : Fin n → ℝ, a * (v ⬝ᵥ v) ≤ obsForm P v ∧ obsForm P v ≤ b * (v ⬝ᵥ v))
    (δ₀ δ₁ : Fin n → ℝ) (h₀ : 0 < δ₀ ⬝ᵥ δ₀) (h₁ : 0 < δ₁ ⬝ᵥ δ₁) :
    |(Real.log (obsForm P δ₁) - Real.log (obsForm P δ₀)) / 2
      - (Real.log (δ₁ ⬝ᵥ δ₁) - Real.log (δ₀ ⬝ᵥ δ₀)) / 2| ≤ Real.log (b / a) / 2 :=
  window_bound_scalar ha h₀ h₁ (hP δ₀) (hP δ₁)

/-- The window exponents (log-growth of length over a window of length `T`) differ by at most
`log (b / a) / (2 T)`, bar E1 of gate D3. -/
theorem window_exponent_bound (P : Matrix (Fin n) (Fin n) ℝ) {a b T : ℝ} (ha : 0 < a)
    (hT : 0 < T)
    (hP : ∀ v : Fin n → ℝ, a * (v ⬝ᵥ v) ≤ obsForm P v ∧ obsForm P v ≤ b * (v ⬝ᵥ v))
    (δ₀ δ₁ : Fin n → ℝ) (h₀ : 0 < δ₀ ⬝ᵥ δ₀) (h₁ : 0 < δ₁ ⬝ᵥ δ₁) :
    |((Real.log (obsForm P δ₁) - Real.log (obsForm P δ₀)) / 2) / T
      - ((Real.log (δ₁ ⬝ᵥ δ₁) - Real.log (δ₀ ⬝ᵥ δ₀)) / 2) / T|
      ≤ Real.log (b / a) / (2 * T) := by
  have h := window_bound P ha hP δ₀ δ₁ h₀ h₁
  rw [← sub_div, abs_div, abs_of_pos hT,
    show Real.log (b / a) / (2 * T) = (Real.log (b / a) / 2) / T by ring]
  exact div_le_div_of_nonneg_right h hT.le

/-- A projection reads no more than the Euclidean length: if the form is bounded by the
Euclidean form then the observational horizon set is contained in the Euclidean one, so the
horizon is never earlier. -/
theorem horizon_subset_of_le (d e : ℝ → ℝ) (hde : ∀ t, d t ≤ e t) (B : ℝ) :
    {t | B < d t} ⊆ {t | B < e t} := by
  intro t ht
  exact lt_of_lt_of_le ht (hde t)

/-- The horizon set shrinks as the budget grows, so the horizon is non-decreasing in `B`. -/
theorem horizon_subset_of_budget (d : ℝ → ℝ) {B₁ B₂ : ℝ} (h : B₁ ≤ B₂) :
    {t | B₂ < d t} ⊆ {t | B₁ < d t} := by
  intro t ht
  exact lt_of_le_of_lt h ht

end GET
