# Observability and identifiability at a budget

Draft 0.1, 2026-09-09. An article of the Geometric Evaluation Theory repository, bridging
Observation Theory's observer (C, G, B) and GET's evaluator. Everything below is labeled proved,
defined, or posited. Nothing is measured yet; the gate that would measure the finite-sample form
is D1 of the discovery campaign in `observation-theory-campaigns/experiments/DISCOVERY-TRACK.md`.

## 1. The claim in one paragraph

Classical observability asks whether a system's state can be recovered from its outputs, and
answers yes or no. An observer with a finite resolution cannot use that answer, because a state
can be recoverable in principle and unrecoverable at the resolution available. Observation Theory
already carries the object that settles the finer question, the read operator
P_C = J_C^T G J_C, and its budget B. The classical observability Gramian is the read operator of
one particular consumer, the output trajectory over a window, so classical observability is the
budget-zero case. With a positive budget the spectrum of P_C splits the directions of state space
into three kinds, unobservable, observable in principle, and observable at this budget, and the
number of the third kind is an effective observable dimension that falls as the budget coarsens.
GET's identification theorem is the same operator read in the other direction, what an
evaluator's choices reveal about the evaluator, and the two statements meet at the design bound.

## 2. Setting

Definitions carried over from the encyclopedia. A consumer is a map C from a state space X, an
open subset of R^n, to an output space Y = R^m, differentiable with Jacobian J_C(x). An output
metric is a positive semidefinite G on Y. The read operator at x is

    P_C(x) = J_C(x)^T G J_C(x),

positive semidefinite on R^n, and the workload-averaged read operator is its expectation over
the states the consumer meets. A budget B >= 0 is a length in the output metric: two outputs y,
y' are the same to the observer when (y - y')^T G (y - y') <= B^2. The observer is the triple
O = (C, G, B).

Definition 1 (distinguishable at a budget). States x and x' are distinguishable to O when
(C(x) - C(x'))^T G (C(x) - C(x')) > B^2, and indistinguishable otherwise. To first order at x,
with delta = x' - x,

    x' is indistinguishable from x  iff  delta^T P_C(x) delta <= B^2.

The indistinguishability relation is reflexive and symmetric and not in general transitive; it is
the tolerance of GET Theorem 1(c) under a length budget, and it is an equivalence exactly when
B = 0, where it is the relation "same output," whose classes are the fibers of C.

## 3. Classical observability is the budget-zero read operator (proved)

Take the linear time-invariant system dx/dt = A x with output y = H x, and the consumer that
maps an initial state x_0 to its output trajectory on the window [0, T],

    C_T(x_0) = ( t -> H exp(At) x_0 ),   t in [0, T],

with the output metric the L^2 inner product on the window. C_T is linear, so its Jacobian is
itself, and

    P_{C_T} = C_T^T G C_T = int_0^T exp(A^T t) H^T H exp(At) dt = W_T,

the observability Gramian on [0, T].

Theorem 1. For the linear time-invariant system and the window consumer C_T:
(a) the read operator of C_T is the observability Gramian W_T;
(b) the system is observable on [0, T] in the classical sense if and only if P_{C_T} is
positive definite, which is the statement that no two distinct initial states are
indistinguishable at budget zero;
(c) the classically unobservable subspace is the kernel of P_{C_T}, and it does not depend on
the budget.

Proof. (a) is the computation above. (b) Classical observability on [0, T] is the injectivity of
x_0 -> y on the window, which for a linear map is the triviality of its kernel; the kernel of C_T
is the kernel of C_T^T G C_T when G is positive definite on the window, which the L^2 metric is,
so injectivity is P_{C_T} > 0. At budget zero, x and x' are indistinguishable exactly when
C_T x = C_T x', that is when x - x' lies in the kernel. (c) The kernel of P_{C_T} is the set of
delta with delta^T P delta = 0, which at any budget satisfies the indistinguishability
inequality; the kernel is a property of C and G alone. QED.

Remark. Nothing in the proof uses linearity beyond replacing the Jacobian by the map. For a
nonlinear consumer the same statements hold to first order at each state, with P_C(x) in place
of W_T, which is the local observability of the nonlinear control literature. The workload
average P_C is then the operator whose kernel is unread at almost every state, the nuisance of
the encyclopedia.

## 4. Identifiability at a budget (proved)

Let P = P_C(x) have eigenvalues lambda_1 >= ... >= lambda_n >= 0 with orthonormal eigenvectors
v_1, ..., v_n. A direction v of unit length is a candidate parameter or state perturbation.

Definition 2. The direction v is mathematically identifiable at x when v^T P v > 0. It is
observationally identifiable at (B, rho) when a perturbation of size rho along v is
distinguishable from x, that is rho^2 v^T P v > B^2.

Theorem 2 (the three kinds of direction). At a state x with read operator P and a budget B:
(a) the unobservable directions form the kernel of P, and no budget makes them identifiable;
(b) a direction v is observationally identifiable at (B, rho) if and only if
    v^T P v > B^2 / rho^2;
(c) the set of perturbations of size at most rho that are indistinguishable from x is the
    ellipsoid delta^T P delta <= B^2 intersected with the ball of radius rho, and the number of
    orthogonal directions that are observationally identifiable at (B, rho) is
        d_obs(B, rho) = #{ i : lambda_i > B^2 / rho^2 },
    non-increasing in B, equal to the rank of P at B = 0, and zero once B >= rho sqrt(lambda_1);
(d) mathematically identifiable and observationally unidentifiable directions are exactly those
    with 0 < lambda_i <= B^2 / rho^2, and they exist whenever B > 0 and the smallest positive
    eigenvalue is below B^2 / rho^2.

Proof. (a) and (b) restate Definition 1 along v. (c) The indistinguishable set is the sublevel set
of the quadratic form, an ellipsoid with semi-axes B / sqrt(lambda_i) along v_i, infinite along
the kernel. A perturbation of size rho along v_i clears the budget exactly when rho > B /
sqrt(lambda_i), so the count of eigenvalues above B^2 / rho^2 is the number of eigen-directions
identifiable at that size; it is non-increasing in B by monotonicity of the threshold, equals the
rank at B = 0, and is zero when even lambda_1 falls below the threshold. (d) is the difference
between (a) and (b). QED.

Corollary 1 (budgeted observability of a linear system). For the window consumer of Section 3,
d_obs(B, rho) is the number of Gramian eigenvalues above B^2 / rho^2. Two linear systems can be
equally observable classically, both Gramians positive definite, and differ in every d_obs(B,
rho) for B > 0; the classical answer discards the spectrum that the budgeted answer keeps.

Corollary 2 (what coarsening removes first). As B grows at fixed rho, directions leave the
identifiable set in order of increasing eigenvalue. The last direction to go is the leading
eigenvector of P, the read direction of the encyclopedia. The effective rank of P, the
participation ratio, is not d_obs at any budget but bounds the budget at which d_obs falls to
one, since lambda_1 >= tr(P) / n and lambda_1 <= tr(P).

## 5. The two theorems face each other (proved, by citation)

GET Theorem 4 says that an evaluator's order on an open set of consequences identifies its
metric up to a positive scale and its ideal up to the metric's kernel. Theorem 2 above says that
an observer's outputs identify a state's perturbations exactly in the directions where the read
operator clears the budget. The objects are the same kind, a positive semidefinite form and a
kernel, and the ambiguities are the same kind, a scale and a kernel. The finite-sample form of
GET Theorem 4, the design bound that at least m + 1 affinely independent consequences are needed
and that nothing off their span is revealed, was measured in gate G5 of the GET campaign (twelve
of twelve cells). The finite-sample form of Theorem 2, that d_obs(B, rho) is recovered from
outputs at a budget and that the kernel directions are not, has not been measured; that is gate
D1 of the discovery campaign.

## 6. Along a trajectory (defined, with one proposition)

Let x(t) follow a flow and let delta x(t) be a tangent perturbation carried by the flow's
linearization. Classical predictability measures the Euclidean growth of delta x. The observer
measures growth in its own length.

Definition 3. The observational length of a perturbation at time t is
d_C(delta x(t)) = sqrt( delta x(t)^T P_C(x(t)) delta x(t) ). The observational Lyapunov exponent
of the perturbation is

    lambda_O = limsup_{t -> infinity} (1/t) log ( d_C(delta x(t)) / d_C(delta x(0)) ),

when the initial observational length is positive, and the observational predictability horizon
at budget B is T_O(B) = inf { t : d_C(delta x(t)) > B }.

Proposition 1. If P_C(x) has eigenvalues bounded between lambda_min > 0 and lambda_max along
the trajectory, then lambda_O equals the classical Lyapunov exponent of the perturbation. If
P_C has a kernel along the trajectory, lambda_O can be smaller than the classical exponent, and
can be zero for a perturbation whose growth stays in the kernel, and it can exceed the classical
exponent transiently when the perturbation rotates from the kernel into the read subspace.

Proof. With bounded positive spectrum, lambda_min |delta x|^2 <= d_C^2 <= lambda_max |delta x|^2,
so the logarithms differ by a bounded amount and the limsup of (1/t) times the difference is
zero. With a kernel the lower bound fails, and a perturbation confined to the kernel has
d_C = 0 for all t while |delta x| grows; a perturbation leaving the kernel has d_C growing from
zero, so its ratio to d_C(0) is unbounded over any finite time, which is the transient. QED.

Remark. Two trajectories can be far apart in R^n and within B of each other to the observer, or
the reverse, so T_O(B) is a property of the observer as much as of the flow. It is measurable on
Lorenz-scale systems with the same instrument that recovers P_C, and it is gate D3.

## 7. What is posited, and what would falsify it

Posited. That the workload average of P_C(x) along a trajectory is the operator whose d_obs
governs a data-assimilation observer's practical identifiability, which is a claim about how such
observers are used rather than a theorem.

Falsifiers of the measurable statements. An estimator that recovers directions with
lambda_i <= B^2 / rho^2 from outputs at budget B (Theorem 2(b) wrong), or fails to recover
directions above it at a rich enough battery (the finite-sample form wrong); an observational
Lyapunov exponent that differs from the classical one for a positive definite read operator
(Proposition 1 wrong).

## 8. Sources

Observation Theory's observer triple, read operator, nuisance, read direction, effective rank
and budget cliff are the encyclopedia entries of those names. GET Theorem 4 and its design
bound are in `paper/geometric-evaluation-theory.tex` and gate G5 of `CAMPAIGN.md`. The
observability Gramian is Kalman's (1960); local observability of nonlinear systems is Hermann and
Krener (1977); both to be cited with verified records before this article becomes a paper.
