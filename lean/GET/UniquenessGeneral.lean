/-
UniquenessGeneral.lean. Theorem 4 of the GET paper (uniqueness), general dimension.

Two quadratic evaluations `(y - t)ᵀ G (y - t)` with positive semidefinite metrics that induce
the same weak order on all of `ℝⁿ` have the same ideal up to the metrics' kernels and
proportional metrics. The ideal part uses that an ideal is a minimizer and a common order has
common minimizers. The scale part restricts both evaluations to lines through the ideal, where
each is a constant times the square of the parameter, compares two lines at parameters that
equalize the first evaluation, and recovers a common ratio. Polarization then turns equal
quadratic forms into equal matrices. The paper states the theorem on an open connected set;
this file checks it on the whole space, which is the case the identification protocol uses.
-/
import Mathlib

namespace GET.UniquenessGeneral

open Matrix Finset

variable {n : ℕ}

/-- The quadratic evaluation of `y` with metric `G` and ideal `t`. -/
def quad (G : Matrix (Fin n) (Fin n) ℝ) (t y : Fin n → ℝ) : ℝ := (y - t) ⬝ᵥ (G *ᵥ (y - t))

/-- The quadratic form of `G` along `v`. -/
def qf (G : Matrix (Fin n) (Fin n) ℝ) (v : Fin n → ℝ) : ℝ := v ⬝ᵥ (G *ᵥ v)

theorem quad_self (G : Matrix (Fin n) (Fin n) ℝ) (t : Fin n → ℝ) : quad G t t = 0 := by
  simp [quad]

theorem qf_nonneg {G : Matrix (Fin n) (Fin n) ℝ} (hG : G.PosSemidef) (v : Fin n → ℝ) :
    0 ≤ qf G v := by
  have := hG.dotProduct_mulVec_nonneg v
  simpa [qf] using this

theorem quad_nonneg {G : Matrix (Fin n) (Fin n) ℝ} (hG : G.PosSemidef) (t y : Fin n → ℝ) :
    0 ≤ quad G t y := qf_nonneg hG (y - t)

theorem qf_eq_zero_iff {G : Matrix (Fin n) (Fin n) ℝ} (hG : G.PosSemidef) (v : Fin n → ℝ) :
    qf G v = 0 ↔ G *ᵥ v = 0 := by
  have := hG.dotProduct_mulVec_zero_iff v
  simpa [qf] using this

/-- Real symmetric matrices satisfy `Gᵀ = G`. -/
theorem transpose_eq_of_posSemidef {G : Matrix (Fin n) (Fin n) ℝ} (hG : G.PosSemidef) :
    Gᵀ = G := by
  have h := hG.1
  rw [IsHermitian, conjTranspose_eq_transpose_of_trivial] at h
  exact h

/-- Symmetry of the bilinear form. -/
theorem dot_mulVec_comm {G : Matrix (Fin n) (Fin n) ℝ} (hG : Gᵀ = G) (x y : Fin n → ℝ) :
    x ⬝ᵥ (G *ᵥ y) = y ⬝ᵥ (G *ᵥ x) := by
  rw [dotProduct_mulVec, ← hG, vecMul_transpose, dotProduct_comm, hG]

/-- **The ideal lies in the other metric's kernel.** If two evaluations induce the same weak
order on all of `ℝⁿ`, the first ideal minimizes the second evaluation, so their difference is
in the kernel of the second metric. -/
theorem ideal_in_kernel {G₁ G₂ : Matrix (Fin n) (Fin n) ℝ} (hG₁ : G₁.PosSemidef)
    (hG₂ : G₂.PosSemidef) (t₁ t₂ : Fin n → ℝ)
    (hsame : ∀ x y, quad G₁ t₁ x ≤ quad G₁ t₁ y ↔ quad G₂ t₂ x ≤ quad G₂ t₂ y) :
    G₂ *ᵥ (t₁ - t₂) = 0 := by
  have h : quad G₂ t₂ t₁ ≤ quad G₂ t₂ t₂ :=
    (hsame t₁ t₂).mp (by rw [quad_self]; exact quad_nonneg hG₁ t₁ t₂)
  rw [quad_self] at h
  have h0 : quad G₂ t₂ t₁ = 0 := le_antisymm h (quad_nonneg hG₂ t₂ t₁)
  exact (qf_eq_zero_iff hG₂ (t₁ - t₂)).mp h0

/-- Along the line `t + s • v` the evaluation with ideal `t` is `s² · qf G v`. -/
theorem quad_line (G : Matrix (Fin n) (Fin n) ℝ) (t v : Fin n → ℝ) (s : ℝ) :
    quad G t (t + s • v) = s ^ 2 * qf G v := by
  unfold quad qf
  simp only [add_sub_cancel_left, mulVec_smul, dotProduct_smul, smul_dotProduct, smul_eq_mul]
  ring

/-- Along the line `t₁ + s • v` an evaluation with ideal `t₂ = t₁ + k`, `G k = 0`, is also
`s² · qf G v`, because the kernel direction contributes nothing. -/
theorem quad_line_shift {G : Matrix (Fin n) (Fin n) ℝ} (hG : Gᵀ = G) (t₁ t₂ v : Fin n → ℝ)
    (hk : G *ᵥ (t₁ - t₂) = 0) (s : ℝ) :
    quad G t₂ (t₁ + s • v) = s ^ 2 * qf G v := by
  unfold quad qf
  have e : t₁ + s • v - t₂ = s • v + (t₁ - t₂) := by abel
  rw [e, mulVec_add, hk, add_zero, add_dotProduct, dot_mulVec_comm hG (t₁ - t₂), hk]
  simp only [dotProduct_zero, add_zero, mulVec_smul, dotProduct_smul, smul_dotProduct,
    smul_eq_mul]
  ring

/-- **Proportional quadratic forms.** If the two evaluations induce the same order on all of
`ℝⁿ` and `G₁ ≠ 0`, there is `λ > 0` with `qf G₂ v = λ · qf G₁ v` for every `v`. -/
theorem qf_proportional {G₁ G₂ : Matrix (Fin n) (Fin n) ℝ} (hG₁ : G₁.PosSemidef)
    (hG₂ : G₂.PosSemidef) (hne : G₁ ≠ 0) (t₁ t₂ : Fin n → ℝ)
    (hsame : ∀ x y, quad G₁ t₁ x ≤ quad G₁ t₁ y ↔ quad G₂ t₂ x ≤ quad G₂ t₂ y) :
    ∃ l : ℝ, 0 < l ∧ ∀ v, qf G₂ v = l * qf G₁ v := by
  have hk₂ : G₂ *ᵥ (t₁ - t₂) = 0 := ideal_in_kernel hG₁ hG₂ t₁ t₂ hsame
  have hT₂ := transpose_eq_of_posSemidef hG₂
  -- both evaluations along the line through t₁ in direction v
  have line₁ : ∀ v s, quad G₁ t₁ (t₁ + s • v) = s ^ 2 * qf G₁ v := quad_line G₁ t₁
  have line₂ : ∀ v s, quad G₂ t₂ (t₁ + s • v) = s ^ 2 * qf G₂ v :=
    fun v s => quad_line_shift hT₂ t₁ t₂ v hk₂ s
  -- a direction where the first form is positive
  obtain ⟨v₀, hv₀⟩ : ∃ v₀, 0 < qf G₁ v₀ := by
    by_contra h
    have h : ∀ v, qf G₁ v ≤ 0 := fun v => not_lt.mp (fun hv => h ⟨v, hv⟩)
    apply hne
    ext i j
    have hz : ∀ v, G₁ *ᵥ v = 0 := fun v =>
      (qf_eq_zero_iff hG₁ v).mp (le_antisymm (h v) (qf_nonneg hG₁ v))
    have := congrFun (hz (Pi.single j 1)) i
    simpa [mulVec, dotProduct, Pi.single_apply] using this
  -- the second form is positive there too
  have hb₀ : 0 < qf G₂ v₀ := by
    rcases (qf_nonneg hG₂ v₀).lt_or_eq with h | h
    · exact h
    · exfalso
      have h2 : quad G₂ t₂ (t₁ + (1:ℝ) • v₀) ≤ quad G₂ t₂ (t₁ + (0:ℝ) • v₀) := by
        rw [line₂, line₂, ← h]; simp
      have h1 := (hsame _ _).mpr h2
      rw [line₁, line₁] at h1
      simp at h1
      linarith
  refine ⟨qf G₂ v₀ / qf G₁ v₀, div_pos hb₀ hv₀, fun v => ?_⟩
  rcases (qf_nonneg hG₁ v).lt_or_eq with hv | hv
  · -- equalize the first evaluation at s = √(qf G₁ v₀) along v and s' = √(qf G₁ v) along v₀
    set s := Real.sqrt (qf G₁ v₀)
    set s' := Real.sqrt (qf G₁ v)
    have hs2 : s ^ 2 = qf G₁ v₀ := Real.sq_sqrt hv₀.le
    have hs'2 : s' ^ 2 = qf G₁ v := Real.sq_sqrt hv.le
    have e1 : quad G₁ t₁ (t₁ + s • v) = quad G₁ t₁ (t₁ + s' • v₀) := by
      rw [line₁, line₁, hs2, hs'2]; ring
    have e2 : quad G₂ t₂ (t₁ + s • v) = quad G₂ t₂ (t₁ + s' • v₀) :=
      le_antisymm ((hsame _ _).mp e1.le) ((hsame _ _).mp e1.ge)
    rw [line₂, line₂, hs2, hs'2] at e2
    -- e2 : qf G₁ v₀ * qf G₂ v = qf G₁ v * qf G₂ v₀
    rw [div_mul_eq_mul_div, eq_div_iff hv₀.ne']
    linear_combination e2
  · -- a direction the first metric does not read is not read by the second either
    have h1 : quad G₁ t₁ (t₁ + (1:ℝ) • v) ≤ quad G₁ t₁ (t₁ + (0:ℝ) • v) := by
      rw [line₁, line₁, ← hv]; simp
    have h2 := (hsame _ _).mp h1
    rw [line₂, line₂] at h2
    simp at h2
    have : qf G₂ v = 0 := le_antisymm h2 (qf_nonneg hG₂ v)
    rw [this, ← hv]; ring

/-- **Polarization.** For a symmetric matrix the bilinear form is determined by the quadratic
form. -/
theorem polarization {G : Matrix (Fin n) (Fin n) ℝ} (hG : Gᵀ = G) (x y : Fin n → ℝ) :
    x ⬝ᵥ (G *ᵥ y) = (qf G (x + y) - qf G x - qf G y) / 2 := by
  unfold qf
  rw [mulVec_add, add_dotProduct, dotProduct_add, dotProduct_add, dot_mulVec_comm hG y x]
  ring

/-- **Equal quadratic forms give equal symmetric matrices.** -/
theorem eq_of_qf_eq {G₁ G₂ : Matrix (Fin n) (Fin n) ℝ} (h₁ : G₁ᵀ = G₁) (h₂ : G₂ᵀ = G₂)
    (h : ∀ v, qf G₂ v = qf G₁ v) : G₂ = G₁ := by
  ext i j
  have e : Pi.single i (1:ℝ) ⬝ᵥ (G₂ *ᵥ Pi.single j 1) = Pi.single i (1:ℝ) ⬝ᵥ (G₁ *ᵥ Pi.single j 1) := by
    rw [polarization h₂, polarization h₁, h, h, h]
  simpa [mulVec, dotProduct, Pi.single_apply] using e

/-- **Uniqueness in general dimension.** Two positive semidefinite quadratic evaluations that
induce the same weak order on `ℝⁿ`, the first with a nonzero metric, have proportional metrics
with a positive constant, and each ideal lies in the other's kernel shift. -/
theorem uniqueness {G₁ G₂ : Matrix (Fin n) (Fin n) ℝ} (hG₁ : G₁.PosSemidef)
    (hG₂ : G₂.PosSemidef) (hne : G₁ ≠ 0) (t₁ t₂ : Fin n → ℝ)
    (hsame : ∀ x y, quad G₁ t₁ x ≤ quad G₁ t₁ y ↔ quad G₂ t₂ x ≤ quad G₂ t₂ y) :
    (∃ l : ℝ, 0 < l ∧ G₂ = l • G₁) ∧ G₁ *ᵥ (t₂ - t₁) = 0 ∧ G₂ *ᵥ (t₁ - t₂) = 0 := by
  refine ⟨?_, ?_, ideal_in_kernel hG₁ hG₂ t₁ t₂ hsame⟩
  · obtain ⟨l, hl, hqf⟩ := qf_proportional hG₁ hG₂ hne t₁ t₂ hsame
    refine ⟨l, hl, ?_⟩
    have hT₁ := transpose_eq_of_posSemidef hG₁
    have hT₂ := transpose_eq_of_posSemidef hG₂
    have hTl : (l • G₁)ᵀ = l • G₁ := by rw [transpose_smul, hT₁]
    apply eq_of_qf_eq hTl hT₂
    intro v
    rw [hqf v]
    unfold qf
    rw [smul_mulVec, dotProduct_smul, smul_eq_mul]
  · have hsame' : ∀ x y, quad G₂ t₂ x ≤ quad G₂ t₂ y ↔ quad G₁ t₁ x ≤ quad G₁ t₁ y :=
      fun x y => (hsame x y).symm
    exact ideal_in_kernel hG₂ hG₁ t₂ t₁ hsame'

end GET.UniquenessGeneral
