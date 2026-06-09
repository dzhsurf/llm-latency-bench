from __future__ import annotations

from tools.seeds.types import Seed

MATH_NORMAL_INSTRUCTIONS = [
    (
        "Solve the primary focus problem in depth. Your response MUST include: "
        "(1) Given — restate all givens with quotes from the problem; "
        "(2) Approach — explain your strategy with reasoning before computing; "
        "(3) Step-by-Step Solution — every algebraic/calculus step with justification; "
        "(4) Verification — substitute answer back or use alternative method; "
        "(5) Reflection — what makes this problem interesting or tricky. "
        "Write a complete, publication-quality solution. Skim other problems for context only."
    ),
    (
        "Solve the primary focus problem with rigorous proof-style reasoning. "
        "For each step: state what you are doing, show the work, quote the relevant "
        "given condition, and explain WHY this step is valid. "
        "Include at least one alternative approach discussion and a verification section. "
        "Primary focus only; others are background context."
    ),
    (
        "Solve the primary focus problem as if grading a student's exam. "
        "Provide: detailed setup with quoted givens, numbered solution steps each with "
        "reasoning and formula justification, common mistakes to avoid, "
        "and a final answer box with units. Be exhaustive."
    ),
    (
        "Solve the primary focus problem with emphasis on geometric/graphical intuition. "
        "Include: verbal description of the setup, quoted constraints, "
        "algebraic steps with reasoning, graphical interpretation where applicable, "
        "and numerical verification. Complete solution required."
    ),
    (
        "Solve the primary focus problem and its extension (if present). "
        "Structure: Problem Restatement (quote givens) → Method Selection (with reasoning) → "
        "Full Derivation (every step justified) → Answer → Verification → "
        "Extension Analysis. Write thoroughly."
    ),
]

MATH_STRUCTURED_INSTRUCTIONS = [
    (
        "Return ONLY valid JSON for the primary focus problem: "
        "{given (array of quoted conditions), approach (string with reasoning), "
        "steps (array of {step_number, expression, justification, source_quote}), "
        "final_answer (string with units), verification (string), "
        "common_mistakes (array of strings)}. No markdown fences."
    ),
    (
        "Return ONLY valid JSON for the primary focus problem: "
        "{problem_restatement (string), method (string), "
        "derivation (array of {step, work, rule_applied, reasoning}), "
        "alternative_approach (string), final_answer (string), "
        "verification (array of {method, result, passes})}. No markdown fences."
    ),
    (
        "Return ONLY valid JSON for the primary focus problem: "
        "{setup (object with quoted_givens, unknowns, constraints), "
        "solution_steps (array of {step, expression, explanation, formula_used}), "
        "answer (object with value, units, interpretation), "
        "edge_cases (array of {case, result, reasoning})}. No markdown fences."
    ),
    (
        "Return ONLY valid JSON for the primary focus problem: "
        "{visualization (string describing graph/geometry), "
        "algebraic_solution (array of {step, expression, justification}), "
        "numerical_check (object with substituted_values, computed_result, matches}), "
        "final_answer (string), insights (array of strings)}. No markdown fences."
    ),
    (
        "Return ONLY valid JSON for the primary focus problem AND its extension: "
        "{primary (object with given, approach, steps (array of {step, expression, justification}), "
        "final_answer, verification}), "
        "extension (object with given, approach, steps, final_answer, verification}), "
        "comparison (string explaining relationship between primary and extension)}. "
        "No markdown fences."
    ),
]

MATH_SEEDS: list[Seed] = [
    Seed(
        "algebra_quadratic",
        "Quadratic Equation with Verification",
        """Problem A (Algebra):
Solve for all real roots of 3x^2 - 11x + 6 = 0.

Workspace:
1) Attempt factoring by splitting the middle term.
2) If factoring is awkward, apply the quadratic formula and simplify the discriminant.
3) Verify each root by substitution into the original equation.
4) State whether the parabola opens upward or downward and relate roots to x-intercepts.

Follow-up: For what values of k does x^2 + kx + 9 = 0 have exactly one real root? Explain using the discriminant.""",
    ),
    Seed(
        "calculus_integral",
        "Definite Integral and Area Interpretation",
        """Problem B (Calculus):
Evaluate I = integral from 0 to 2 of (x^3 + 2x) dx.

Workspace:
1) Find the antiderivative term by term.
2) Apply the Fundamental Theorem of Calculus with bounds 0 and 2.
3) Interpret the result as the signed area under y = x^3 + 2x on [0,2].
4) Check whether the integrand is nonnegative on the interval and discuss whether signed area equals total area.

Extension: Without computing, determine whether I is positive or negative and justify using symmetry/monotonicity arguments.""",
    ),
    Seed(
        "combinatorics_committee",
        "Committee Selection with Constraints",
        """Problem C (Combinatorics):
A committee of 4 people must be chosen from 9 engineers and 5 designers.
How many committees contain at least 2 engineers?

Workspace:
1) Count total committees of size 4 with no restriction.
2) Use complement counting: committees with 0 or 1 engineers.
3) Alternatively use casework on exactly 2, 3, or 4 engineers.
4) Show both methods agree.

Extension: If one engineer must serve as chair, recount committees with at least 2 engineers including the chair constraint.""",
    ),
    Seed(
        "number_theory_gcd",
        "Extended Euclidean Algorithm",
        """Problem D (Number Theory):
Find integers a, b such that 84a + 126b = gcd(84, 126).

Workspace:
1) Run the Euclidean algorithm to compute gcd(84,126).
2) Back-substitute to express gcd as a linear combination.
3) Verify the pair (a,b) satisfies the equation.
4) Explain why infinitely many solutions exist once one solution is found.

Challenge: Find the smallest positive a such that 84a + 126b is divisible by 42 for some integer b.""",
    ),
    Seed(
        "probability_cards",
        "Conditional Probability with Cards",
        """Problem E (Probability):
From a standard 52-card deck, two cards are drawn without replacement.
Compute P(both hearts | first card is red).

Workspace:
1) Define events H1, H2, R1 clearly.
2) Use conditional probability formula P(H1 and H2 | R1).
3) Count favorable outcomes carefully avoiding double counting.
4) Provide an intuitive explanation of why the probability differs from P(both hearts).

Extension: How does the answer change if draws are with replacement?""",
    ),
    Seed(
        "geometry_triangle",
        "Triangle Area via Two Methods",
        """Problem F (Geometry):
Vertices A(1,2), B(7,2), C(4,8). Compute the area of triangle ABC.

Workspace:
1) Apply the shoelace formula with coordinates listed in order.
2) Use base AB and height relative to horizontal base.
3) Confirm both methods match.
4) Compute the perimeter and classify the triangle by side lengths.

Extension: Find the equation of the altitude from C to AB.""",
    ),
    Seed(
        "linear_system",
        "3x3 Linear System",
        """Problem G (Linear Algebra):
Solve:
  2x + y - z = 3
  x - y + 2z = 4
  3x + 2y + z = 10

Workspace:
1) Use Gaussian elimination with clear row operations.
2) State whether the system has unique, infinite, or no solutions.
3) If unique, verify by plugging into all equations.
4) Interpret the solution geometrically as intersection of three planes.""",
    ),
    Seed(
        "sequences_series",
        "Arithmetic Series Sum",
        """Problem H (Sequences):
Find the sum of the first 40 terms of a_n = 5 + 3(n-1).

Workspace:
1) Identify first term and common difference.
2) Derive S_n = n/2 * (2a1 + (n-1)d).
3) Substitute n=40 and compute exactly.
4) Check with a small partial sum manually for n=3 as sanity check.

Extension: Determine the smallest n such that S_n > 10,000.""",
    ),
    Seed(
        "optimization_word",
        "Fence Optimization Against a Wall",
        """Problem I (Optimization):
A farmer has 200 m of fencing for a rectangular pen against a straight barn wall (wall forms one side; no fence needed on that side). What dimensions maximize enclosed area?

Workspace:
1) Express area A in terms of single variable with perimeter constraint.
2) Differentiate and find critical points OR complete the square.
3) Confirm maximum using second derivative or endpoint reasoning.
4) State optimal width and length clearly.

Extension: If the barn wall is only 80 m long, how does the optimum change?""",
    ),
    Seed(
        "logic_proof",
        "Irrationality of sqrt(2)",
        """Problem J (Proof):
Prove that sqrt(2) is irrational.

Workspace:
1) Assume sqrt(2) = p/q in lowest terms.
2) Square both sides and argue about parity of p and q.
3) Derive contradiction explicitly stating which assumption fails.
4) Reflect on why the argument does not work for sqrt(4).

Write the proof in complete sentences suitable for a discrete mathematics homework submission.""",
    ),
]
