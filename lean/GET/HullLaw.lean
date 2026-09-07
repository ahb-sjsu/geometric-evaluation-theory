/-
HullLaw.lean. Theorem 3(b) of the GET paper (the hull law).

An evaluation whose cost is a convex function of the consequence cannot rank an action below
every action whose consequences surround it. If a consequence is a convex combination of
finitely many others, the cost at that consequence is at most the largest cost among them,
so the surrounded action is weakly preferred to at least one of the surrounding actions. The
proof is Jensen's inequality followed by a bound by the maximum. The quadratic cost of the
paper is convex because its metric is positive semidefinite, and the law needs only convexity.
-/
import Mathlib

namespace GET.HullLaw

open Finset

variable {E : Type*} [AddCommGroup E] [Module ℝ E]

/-- **The hull law.** For a convex cost `f`, a consequence that is a convex combination of the
consequences `p i`, `i ∈ s`, has cost at most the cost of some `p j`, `j ∈ s`. -/
theorem hull_law {f : E → ℝ} (hf : ConvexOn ℝ Set.univ f)
    {ι : Type*} (s : Finset ι) (hs : s.Nonempty) (w : ι → ℝ) (p : ι → E)
    (hw : ∀ i ∈ s, 0 ≤ w i) (hw1 : ∑ i ∈ s, w i = 1) :
    ∃ j ∈ s, f (∑ i ∈ s, w i • p i) ≤ f (p j) := by
  obtain ⟨j, hj, hmax⟩ := s.exists_max_image (fun i => f (p i)) hs
  refine ⟨j, hj, ?_⟩
  calc f (∑ i ∈ s, w i • p i)
      ≤ ∑ i ∈ s, w i • f (p i) := hf.map_sum_le hw hw1 (fun i _ => Set.mem_univ _)
    _ ≤ ∑ i ∈ s, w i • f (p j) :=
        Finset.sum_le_sum fun i hi => smul_le_smul_of_nonneg_left (hmax i hi) (hw i hi)
    _ = f (p j) := by rw [← Finset.sum_smul, hw1, one_smul]

/-- **The hull law for a preference.** With cost `f` convex and consequence map `C`, an action
`a` whose consequence is a convex combination of the consequences of the actions in `s` is
weakly preferred (has cost at most) to some action in `s`. -/
theorem hull_law_pref {A : Type*} {f : E → ℝ} (hf : ConvexOn ℝ Set.univ f) (C : A → E)
    (s : Finset A) (hs : s.Nonempty) (w : A → ℝ) (hw : ∀ i ∈ s, 0 ≤ w i)
    (hw1 : ∑ i ∈ s, w i = 1) (a : A) (ha : C a = ∑ i ∈ s, w i • C i) :
    ∃ j ∈ s, f (C a) ≤ f (C j) := by
  rw [ha]
  exact hull_law hf s hs w C hw hw1

end GET.HullLaw
