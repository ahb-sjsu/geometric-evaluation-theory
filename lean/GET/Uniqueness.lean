/-
Uniqueness.lean. Theorem 4 of the GET paper (uniqueness), the one-dimensional core.

Two evaluations on a line, each a positive multiple of the squared distance to its own ideal
plus a constant, that induce the same weak order on the whole line have the same ideal. The
proof is that the ideal is the unique minimizer of each cost and a common order has a common
minimizer. The scale is free in one dimension, which is the "up to a positive scale" clause of
the theorem. The general case, in which the metric is identified up to scale and the ideal up
to the metric's kernel from the order on an open set, is stated in the paper and is the next
target of gate G1.
-/
import Mathlib

namespace GET.Uniqueness

/-- A one-dimensional quadratic evaluation with scale `a`, ideal `t`, and offset `b`. -/
def quad (a t b x : ℝ) : ℝ := a * (x - t) ^ 2 + b

/-- The ideal minimizes its own evaluation. -/
theorem quad_min (a t b : ℝ) (ha : 0 ≤ a) (x : ℝ) : quad a t b t ≤ quad a t b x := by
  unfold quad
  nlinarith [sq_nonneg (x - t)]

/-- **Uniqueness of the ideal on a line.** Two positive quadratic evaluations that induce the
same weak order on `ℝ` have the same ideal. -/
theorem ideal_unique (a₁ a₂ b₁ b₂ t₁ t₂ : ℝ) (ha₁ : 0 < a₁) (ha₂ : 0 < a₂)
    (hsame : ∀ x y : ℝ, quad a₁ t₁ b₁ x ≤ quad a₁ t₁ b₁ y ↔ quad a₂ t₂ b₂ x ≤ quad a₂ t₂ b₂ y) :
    t₁ = t₂ := by
  have h := (hsame t₁ t₂).mp (quad_min a₁ t₁ b₁ ha₁.le t₂)
  unfold quad at h
  have h' : a₂ * (t₁ - t₂) ^ 2 ≤ a₂ * 0 := by
    have : (t₂ - t₂) ^ 2 = 0 := by ring
    rw [this] at h
    linarith
  have hsq : (t₁ - t₂) ^ 2 ≤ 0 := le_of_mul_le_mul_left h' ha₂
  have h0 : (t₁ - t₂) ^ 2 = 0 := le_antisymm hsq (sq_nonneg _)
  have := (pow_eq_zero_iff two_ne_zero).mp h0
  linarith

/-- **Any positive scale induces the same order.** The scale is not identified in one
dimension, which is the "up to a positive scale" clause. -/
theorem scale_free (a₁ a₂ b₁ b₂ t : ℝ) (ha₁ : 0 < a₁) (ha₂ : 0 < a₂) (x y : ℝ) :
    quad a₁ t b₁ x ≤ quad a₁ t b₁ y ↔ quad a₂ t b₂ x ≤ quad a₂ t b₂ y := by
  unfold quad
  constructor
  · intro h
    have : (x - t) ^ 2 ≤ (y - t) ^ 2 := le_of_mul_le_mul_left (by linarith) ha₁
    nlinarith
  · intro h
    have : (x - t) ^ 2 ≤ (y - t) ^ 2 := le_of_mul_le_mul_left (by linarith) ha₂
    nlinarith

end GET.Uniqueness
