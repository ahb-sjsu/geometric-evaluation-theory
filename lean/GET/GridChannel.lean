/-
GridChannel.lean. Proposition 1(a) of the GET paper (the grid channel).

An evaluator that compares two distances only through a quantizer obeys, for each single
comparison, the rule of Definition 2 with a tolerance it does not know: the distance from the
lower distance up to the next quantizer boundary. That tolerance depends on the lower distance,
so the relation a quantizer induces on a whole set of options is NOT the fixed-threshold
semiorder of Definition 2. On a set it is a weak order over the reports, the case eps = 0 of
Theorem 2(a) applied to the quantized distance. With unit bins the distances 0.1, 0.9, 1.1 show
why: the first two share a report and the last two do not, so one tolerance would have to be at
least 0.8 and below 0.2 at once. What is proved here is the per-comparison statement, which is
the bridge between a grid and a length budget and is all the paper claims.

Boundaries at `b + k * h` for integers `k` give the quantizer `x ↦ ⌊(x - b)/h⌋`. Any
nondecreasing `ρ` constant between consecutive boundaries induces the same ordering, so the
floor is the general case and not a special one; truncation to a grid of step `h` is `b = 0`
and rounding to nearest is `b = h/2`, whose boundaries are the cell midpoints.

`grid_threshold` is the statement that the pair is ordered correctly exactly when the gap
reaches the tolerance, and `tolerance_mem_Ioc` is that the tolerance lies in `(0, h]`. Part (b)
of the paper's proposition, that a uniform position makes the tolerance uniform on `(0, h]`, is
measure-theoretic and is not formalized here; the paper says so.
-/
import Mathlib

namespace GET.GridChannel

variable {h b d₁ d₂ : ℝ}

/-- The tolerance a quantizer of step `h` with boundaries at `b + k * h` imposes at `d₁`:
the distance from `d₁` up to the next boundary above it. -/
noncomputable def tolerance (h b d₁ : ℝ) : ℝ := h * (1 - Int.fract ((d₁ - b) / h))

/-- **The tolerance is positive and at most the step.** -/
theorem tolerance_mem_Ioc (hh : 0 < h) : tolerance h b d₁ ∈ Set.Ioc 0 h := by
  have h0 := Int.fract_nonneg ((d₁ - b) / h)
  have h1 := Int.fract_lt_one ((d₁ - b) / h)
  have hprod : 0 ≤ h * Int.fract ((d₁ - b) / h) := mul_nonneg hh.le h0
  refine Set.mem_Ioc.mpr ⟨?_, ?_⟩
  · have : 0 < 1 - Int.fract ((d₁ - b) / h) := by linarith
    exact mul_pos hh this
  · have : tolerance h b d₁ = h - h * Int.fract ((d₁ - b) / h) := by
      unfold tolerance; ring
    rw [this]; linarith

/-- **One comparison under a quantizer obeys Definition 2 with an unknown tolerance.**
The quantizer separates `d₁` from `d₂` exactly when the gap `d₂ - d₁` reaches the tolerance
at `d₁`. This is the rule of Definition 2 applied to that comparison with threshold
`tolerance h b d₁`, the two differing only in the boundary case where the gap equals the
tolerance. The threshold is a function of `d₁`, so this does not say that the quantizer induces
a single-threshold semiorder on a set of options, and it does not. -/
theorem grid_threshold (hh : 0 < h) :
    ⌊(d₁ - b) / h⌋ < ⌊(d₂ - b) / h⌋ ↔ tolerance h b d₁ ≤ d₂ - d₁ := by
  have hne : h ≠ 0 := ne_of_gt hh
  have key : (d₂ - b) / h = (d₁ - b) / h + (d₂ - d₁) / h := by
    field_simp; ring
  have hfl : ((⌊(d₁ - b) / h⌋ : ℤ) : ℝ) = (d₁ - b) / h - Int.fract ((d₁ - b) / h) :=
    (Int.self_sub_fract _).symm
  rw [key, Int.lt_iff_add_one_le, Int.le_floor]
  push_cast
  rw [hfl]
  unfold tolerance
  constructor
  · intro H
    exact (le_div_iff₀' hh).mp (by linarith)
  · intro H
    have h2 : 1 - Int.fract ((d₁ - b) / h) ≤ (d₂ - d₁) / h := (le_div_iff₀' hh).mpr H
    linarith

/-- **Truncation to a grid of step `h`** is the case `b = 0`. -/
theorem truncation (hh : 0 < h) :
    ⌊d₁ / h⌋ < ⌊d₂ / h⌋ ↔ tolerance h 0 d₁ ≤ d₂ - d₁ := by
  simpa using grid_threshold (h := h) (b := 0) (d₁ := d₁) (d₂ := d₂) hh

/-- **Rounding to the nearest grid point** is the case `b = h/2`, since its boundaries are the
cell midpoints. -/
theorem rounding (hh : 0 < h) :
    ⌊(d₁ - h / 2) / h⌋ < ⌊(d₂ - h / 2) / h⌋ ↔ tolerance h (h / 2) d₁ ≤ d₂ - d₁ :=
  grid_threshold hh

end GET.GridChannel
