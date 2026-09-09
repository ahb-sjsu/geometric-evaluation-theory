/-
Observability and identifiability at a budget.
Companion to `articles/2026-09-09-identifiability-at-a-budget.md` (Theorems 1 and 2) and gate D0
of the OD track of observation-theory-campaigns.

A consumer is abstracted as a linear map `M : Matrix (Fin m) (Fin n) ℝ` (the Jacobian, or the
window map of a linear system whose read operator is the observability Gramian), with an output
metric `G` positive semidefinite on `Fin m`. The read operator is `P = Mᵀ G M`. A perturbation `δ`
is distinguishable at budget `B` when its quadratic form exceeds `B ^ 2`.
-/
import Mathlib

namespace GET

open Matrix

variable {m n : ℕ}

/-- The read operator of a linear consumer `M` with output metric `G`. -/
def readOperator (M : Matrix (Fin m) (Fin n) ℝ) (G : Matrix (Fin m) (Fin m) ℝ) :
    Matrix (Fin n) (Fin n) ℝ :=
  Mᵀ * G * M

/-- The observational squared length of a perturbation under a read operator. -/
def obsForm (P : Matrix (Fin n) (Fin n) ℝ) (δ : Fin n → ℝ) : ℝ :=
  δ ⬝ᵥ P.mulVec δ

/-- Distinguishable at budget `B`: the observational length exceeds the budget. -/
def Distinguishable (P : Matrix (Fin n) (Fin n) ℝ) (B : ℝ) (δ : Fin n → ℝ) : Prop :=
  B ^ 2 < obsForm P δ

/-- The read operator of a linear consumer is positive semidefinite when the output metric is. -/
theorem readOperator_posSemidef (M : Matrix (Fin m) (Fin n) ℝ) (G : Matrix (Fin m) (Fin m) ℝ)
    (hG : G.PosSemidef) : (readOperator M G).PosSemidef := by
  unfold readOperator
  simpa [Matrix.mul_assoc] using hG.conjTranspose_mul_mul_same M

/-- The observational form of the read operator is the output metric's form of the image:
`δᵀ (Mᵀ G M) δ = (M δ)ᵀ G (M δ)`. -/
theorem obsForm_readOperator (M : Matrix (Fin m) (Fin n) ℝ) (G : Matrix (Fin m) (Fin m) ℝ)
    (δ : Fin n → ℝ) : obsForm (readOperator M G) δ = (M.mulVec δ) ⬝ᵥ G.mulVec (M.mulVec δ) := by
  unfold obsForm readOperator
  rw [← Matrix.mulVec_mulVec, ← Matrix.mulVec_mulVec, Matrix.dotProduct_mulVec,
    Matrix.vecMul_transpose]

/-- Theorem 1(c): a perturbation in the kernel of the read operator is never distinguishable, at
any budget. -/
theorem kernel_not_distinguishable (P : Matrix (Fin n) (Fin n) ℝ) (B : ℝ) (δ : Fin n → ℝ)
    (h : P.mulVec δ = 0) : ¬ Distinguishable P B δ := by
  unfold Distinguishable obsForm
  rw [h, dotProduct_zero]
  exact not_lt.mpr (sq_nonneg B)

/-- Theorem 1(b), budget zero: for a positive definite output metric a perturbation is
distinguishable at budget zero exactly when the consumer maps it to a nonzero output, so the
consumer is injective (classically observable) iff every nonzero perturbation is distinguishable
at budget zero. -/
theorem distinguishable_zero_iff (M : Matrix (Fin m) (Fin n) ℝ) (G : Matrix (Fin m) (Fin m) ℝ)
    (hG : G.PosDef) (δ : Fin n → ℝ) :
    Distinguishable (readOperator M G) 0 δ ↔ M.mulVec δ ≠ 0 := by
  unfold Distinguishable
  rw [obsForm_readOperator]
  constructor
  · intro h hz
    rw [hz, Matrix.mulVec_zero, dotProduct_zero] at h
    simp at h
  · intro hz
    have hpos : 0 < star (M.mulVec δ) ⬝ᵥ G.mulVec (M.mulVec δ) :=
      (Matrix.posDef_iff_dotProduct_mulVec.1 hG).2 hz
    simpa using hpos

/-- Theorem 2(b): a perturbation of size `ρ > 0` along `v` is distinguishable at budget `B`
exactly when the form of `v` exceeds `B ^ 2 / ρ ^ 2`. -/
theorem distinguishable_scaled_iff (P : Matrix (Fin n) (Fin n) ℝ) (B ρ : ℝ) (hρ : 0 < ρ)
    (v : Fin n → ℝ) : Distinguishable P B (ρ • v) ↔ B ^ 2 / ρ ^ 2 < obsForm P v := by
  unfold Distinguishable obsForm
  rw [Matrix.mulVec_smul, smul_dotProduct, dotProduct_smul, smul_eq_mul, smul_eq_mul]
  have hρ2 : 0 < ρ ^ 2 := by positivity
  rw [div_lt_iff₀ hρ2]
  have hid : ρ * (ρ * (v ⬝ᵥ P.mulVec v)) = (v ⬝ᵥ P.mulVec v) * ρ ^ 2 := by ring
  rw [hid]

/-- Distinguishability is antitone in the budget: coarsening never creates a distinction. -/
theorem distinguishable_antitone (P : Matrix (Fin n) (Fin n) ℝ) {B₁ B₂ : ℝ} (h0 : 0 ≤ B₁)
    (h : B₁ ≤ B₂) (δ : Fin n → ℝ) : Distinguishable P B₂ δ → Distinguishable P B₁ δ := by
  unfold Distinguishable
  intro hd
  have : B₁ ^ 2 ≤ B₂ ^ 2 := by nlinarith
  linarith

/-- The number of directions of a spectrum `λ` that clear the budget threshold, `d_obs(B, ρ)`. -/
noncomputable def dObs (lam : Fin n → ℝ) (B ρ : ℝ) : ℕ :=
  (Finset.univ.filter fun i => B ^ 2 / ρ ^ 2 < lam i).card

/-- Theorem 2(c): `d_obs` is non-increasing in the budget. -/
theorem dObs_antitone (lam : Fin n → ℝ) {B₁ B₂ ρ : ℝ} (hρ : 0 < ρ) (h0 : 0 ≤ B₁) (h : B₁ ≤ B₂) :
    dObs lam B₂ ρ ≤ dObs lam B₁ ρ := by
  unfold dObs
  apply Finset.card_le_card
  intro i hi
  simp only [Finset.mem_filter, Finset.mem_univ, true_and] at hi ⊢
  have hρ2 : 0 < ρ ^ 2 := by positivity
  have : B₁ ^ 2 ≤ B₂ ^ 2 := by nlinarith
  calc B₁ ^ 2 / ρ ^ 2 ≤ B₂ ^ 2 / ρ ^ 2 := by gcongr
    _ < lam i := hi

/-- Theorem 2(c) at budget zero: `d_obs(0, ρ)` counts the positive eigenvalues, the rank of a
positive semidefinite operator. -/
theorem dObs_zero (lam : Fin n → ℝ) (ρ : ℝ) :
    dObs lam 0 ρ = (Finset.univ.filter fun i => 0 < lam i).card := by
  unfold dObs
  congr 1
  ext i
  simp

/-- Theorem 2(c): once the budget reaches `ρ √λ_max`, no direction clears it. -/
theorem dObs_eq_zero_of_large_budget (lam : Fin n → ℝ) (B ρ : ℝ) (hρ : 0 < ρ)
    (hB : ∀ i, lam i * ρ ^ 2 ≤ B ^ 2) : dObs lam B ρ = 0 := by
  unfold dObs
  rw [Finset.card_eq_zero, Finset.filter_eq_empty_iff]
  intro i _
  have hρ2 : 0 < ρ ^ 2 := by positivity
  rw [not_lt, le_div_iff₀ hρ2]
  exact hB i

end GET
