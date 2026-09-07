/-
Incompatibility.lean. Theorem 7 of the GET paper (incompatibility of coupled geometries).

Ky Fan's maximum principle is not in Mathlib. Following the campaign rule for gate G1, this
file takes it as named hypotheses rather than as an axiom: a function `topk` on matrices and a
set `S` of admissible representations (the rank-`k` orthogonal projectors in the paper) such
that every `Q ∈ S` satisfies `trace (Q * M) ≤ topk M` and some `Q ∈ S` attains it. Everything
else in the theorem is then checked: regret is nonnegative, the weighted total regret of any
shared representation is at least the deficiency of the summed geometry, that bound is attained,
and the total regret is zero exactly when every evaluator's regret is zero. The identification
of the attaining projectors with top-`k` eigenspaces is Ky Fan's equality case and is part of
the hypotheses, not a claim of this file.
-/
import Mathlib

namespace GET.Incompatibility

open Matrix Finset

variable {n : ℕ} {N : ℕ}

/-- Regret of evaluator with geometry `P` under the shared representation `Q`, in units of the
source variance. -/
def regret (topk : Matrix (Fin n) (Fin n) ℝ → ℝ) (P Q : Matrix (Fin n) (Fin n) ℝ) : ℝ :=
  topk P - trace (Q * P)

/-- **Ky Fan, first half.** Every admissible representation is at most the bound. -/
def KyFanBound (topk : Matrix (Fin n) (Fin n) ℝ → ℝ) (S : Set (Matrix (Fin n) (Fin n) ℝ)) :
    Prop := ∀ Q ∈ S, ∀ M, trace (Q * M) ≤ topk M

/-- **Ky Fan, second half.** The bound is attained by some admissible representation. -/
def KyFanAttained (topk : Matrix (Fin n) (Fin n) ℝ → ℝ) (S : Set (Matrix (Fin n) (Fin n) ℝ)) :
    Prop := ∀ M, ∃ Q ∈ S, trace (Q * M) = topk M

/-- Regret is nonnegative. -/
theorem regret_nonneg {topk : Matrix (Fin n) (Fin n) ℝ → ℝ} {S : Set (Matrix (Fin n) (Fin n) ℝ)}
    (hb : KyFanBound topk S) (P : Matrix (Fin n) (Fin n) ℝ) {Q : Matrix (Fin n) (Fin n) ℝ}
    (hQ : Q ∈ S) : 0 ≤ regret topk P Q := by
  unfold regret
  linarith [hb Q hQ P]

/-- The trace of a product against a weighted sum is the weighted sum of traces. -/
theorem trace_mul_weighted_sum (Q : Matrix (Fin n) (Fin n) ℝ) (w : Fin N → ℝ)
    (P : Fin N → Matrix (Fin n) (Fin n) ℝ) :
    trace (Q * ∑ i, w i • P i) = ∑ i, w i * trace (Q * P i) := by
  rw [Matrix.mul_sum, trace_sum]
  refine Finset.sum_congr rfl fun i _ => ?_
  rw [Matrix.mul_smul, trace_smul, smul_eq_mul]

/-- **Lower bound on the weighted total regret.** For any admissible `Q`, the weighted total
regret is at least the Ky Fan deficiency of the weighted sum of the geometries. -/
theorem total_regret_ge {topk : Matrix (Fin n) (Fin n) ℝ → ℝ} {S : Set (Matrix (Fin n) (Fin n) ℝ)}
    (hb : KyFanBound topk S) (w : Fin N → ℝ) (P : Fin N → Matrix (Fin n) (Fin n) ℝ)
    {Q : Matrix (Fin n) (Fin n) ℝ} (hQ : Q ∈ S) :
    (∑ i, w i * topk (P i)) - topk (∑ i, w i • P i) ≤ ∑ i, w i * regret topk (P i) Q := by
  have h := hb Q hQ (∑ i, w i • P i)
  rw [trace_mul_weighted_sum] at h
  unfold regret
  simp only [mul_sub, Finset.sum_sub_distrib]
  linarith

/-- **The bound is attained** at a representation attaining Ky Fan's bound for the weighted sum. -/
theorem total_regret_attained {topk : Matrix (Fin n) (Fin n) ℝ → ℝ}
    {S : Set (Matrix (Fin n) (Fin n) ℝ)} (ha : KyFanAttained topk S) (w : Fin N → ℝ)
    (P : Fin N → Matrix (Fin n) (Fin n) ℝ) :
    ∃ Q ∈ S, ∑ i, w i * regret topk (P i) Q
      = (∑ i, w i * topk (P i)) - topk (∑ i, w i • P i) := by
  obtain ⟨Q, hQ, hQeq⟩ := ha (∑ i, w i • P i)
  refine ⟨Q, hQ, ?_⟩
  rw [← hQeq, trace_mul_weighted_sum]
  unfold regret
  simp only [mul_sub, Finset.sum_sub_distrib]

/-- **Zero total regret means zero regret for everyone.** With positive weights the weighted
total regret vanishes exactly when each evaluator's regret does. -/
theorem total_regret_zero_iff {topk : Matrix (Fin n) (Fin n) ℝ → ℝ}
    {S : Set (Matrix (Fin n) (Fin n) ℝ)} (hb : KyFanBound topk S) (w : Fin N → ℝ)
    (hw : ∀ i, 0 < w i) (P : Fin N → Matrix (Fin n) (Fin n) ℝ)
    {Q : Matrix (Fin n) (Fin n) ℝ} (hQ : Q ∈ S) :
    ∑ i, w i * regret topk (P i) Q = 0 ↔ ∀ i, regret topk (P i) Q = 0 := by
  have hnn : ∀ i ∈ (Finset.univ : Finset (Fin N)), 0 ≤ w i * regret topk (P i) Q :=
    fun i _ => mul_nonneg (hw i).le (regret_nonneg hb (P i) hQ)
  rw [Finset.sum_eq_zero_iff_of_nonneg hnn]
  constructor
  · intro h i
    have := h i (Finset.mem_univ i)
    rcases mul_eq_zero.mp this with h0 | h0
    · exact absurd h0 (hw i).ne'
    · exact h0
  · intro h i _
    rw [h i, mul_zero]

/-- **Strict positivity.** The least weighted total regret is strictly positive exactly when no
admissible representation is regret-free for every evaluator. -/
theorem deficiency_pos_iff {topk : Matrix (Fin n) (Fin n) ℝ → ℝ}
    {S : Set (Matrix (Fin n) (Fin n) ℝ)} (hb : KyFanBound topk S) (ha : KyFanAttained topk S)
    (w : Fin N → ℝ) (hw : ∀ i, 0 < w i) (P : Fin N → Matrix (Fin n) (Fin n) ℝ) :
    0 < (∑ i, w i * topk (P i)) - topk (∑ i, w i • P i)
      ↔ ¬ ∃ Q ∈ S, ∀ i, regret topk (P i) Q = 0 := by
  constructor
  · rintro hpos ⟨Q, hQ, hzero⟩
    have h := total_regret_ge hb w P hQ
    have hsum : ∑ i, w i * regret topk (P i) Q = 0 := by
      simp [hzero]
    linarith
  · intro hno
    obtain ⟨Q, hQ, heq⟩ := total_regret_attained ha w P
    have hnn : 0 ≤ ∑ i, w i * regret topk (P i) Q :=
      Finset.sum_nonneg fun i _ => mul_nonneg (hw i).le (regret_nonneg hb (P i) hQ)
    rcases hnn.lt_or_eq with hlt | hzero
    · linarith
    · exfalso
      apply hno
      exact ⟨Q, hQ, (total_regret_zero_iff hb w hw P hQ).mp hzero.symm⟩

end GET.Incompatibility
