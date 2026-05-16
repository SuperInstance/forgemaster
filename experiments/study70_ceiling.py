#!/usr/bin/env python3
"""
Study 70: Translation Ceiling — Is there a point where no amount of translation helps?

20 problems × 5 difficulty levels × 3 models × 3 conditions = 180 queries
"""
import json
import os
import re
import sys
import time
import math
import requests

KEY_PATH = os.path.expanduser("~/.openclaw/workspace/.credentials/deepinfra-api-key.txt")
with open(KEY_PATH) as f:
    API_KEY = f.read().strip()

ENDPOINT = "https://api.deepinfra.com/v1/openai/chat/completions"

MODELS = [
    "ByteDance/Seed-2.0-mini",      # Tier 1 (Stage 4)
    "NousResearch/Hermes-3-Llama-3.1-70B",  # Tier 2 (Stage 3)
    "Qwen/Qwen3.6-35B-A3B",          # Tier 2 (Stage 3)
]

# 5 levels × 4 problems each = 20 problems
PROBLEMS = [
    # Level 1: Simple arithmetic (always works)
    {
        "level": 1, "name": "simple_arith",
        "raw": "Compute: 347 × 28",
        "translated": "Please multiply 347 by 28. Show your work step by step: first multiply 347 by 8, then multiply 347 by 20, then add the two results together.",
        "over_translated": "Let me walk you through this very carefully. We need to find the product of three hundred and forty-seven multiplied by twenty-eight. This is a basic multiplication problem. Step 1: Take the number 347. Step 2: Multiply it by 28. Step 3: First, let's multiply 347 by just the ones digit, which is 8. So we compute 347 times 8. That gives us 2776. Step 4: Next, let's multiply 347 by the tens digit, which is 2, but since it's in the tens place, we're really multiplying by 20. So 347 times 20 equals 6940. Step 5: Finally, we add those two partial results: 2776 plus 6940 equals our final answer. What is 2776 + 6940?",
        "answer": 9716,
        "check": lambda r: "9716" in r,
    },
    {
        "level": 1, "name": "simple_div",
        "raw": "Compute: 1512 ÷ 7",
        "translated": "Please divide 1512 by 7. Step by step: how many times does 7 go into 1512?",
        "over_translated": "We are dividing one thousand five hundred and twelve by seven. Think of it as: if you have 1512 items and split them into 7 equal groups, how many are in each group? Start by dividing 15 by 7, which goes 2 times with remainder 1. Then bring down the 1 to get 11. Divide 11 by 7, which goes 1 time with remainder 4. Bring down the 2 to get 42. Divide 42 by 7, which goes exactly 6 times. So what is our answer?",
        "answer": 216,
        "check": lambda r: "216" in r and "1216" not in r and "2160" not in r,
    },
    {
        "level": 1, "name": "simple_add_big",
        "raw": "Compute: 4583 + 2947",
        "translated": "Add 4583 and 2947 together. Step by step: add the ones (3+7=10, carry 1), tens (8+4+1=13, carry 1), hundreds (5+9+1=15, carry 1), thousands (4+2+1=7).",
        "over_translated": "Let's carefully add four thousand five hundred eighty-three plus two thousand nine hundred forty-seven. We'll add column by column from right to left. Ones column: 3 plus 7 equals 10, write 0 carry 1. Tens column: 8 plus 4 plus the carried 1 equals 13, write 3 carry 1. Hundreds column: 5 plus 9 plus the carried 1 equals 15, write 5 carry 1. Thousands column: 4 plus 2 plus the carried 1 equals 7. So the final sum is what number?",
        "answer": 7530,
        "check": lambda r: "7530" in r,
    },
    {
        "level": 1, "name": "simple_mod",
        "raw": "Compute: 234 mod 17",
        "translated": "Find the remainder when 234 is divided by 17. Step by step: 17 × 10 = 170, 234 - 170 = 64. Then 17 × 3 = 51, 64 - 51 = 13. So the remainder is 13.",
        "over_translated": "We need to find what remains after dividing two hundred thirty-four by seventeen. Think of it as: how many whole groups of 17 can we make from 234, and what's left over? First, 17 times 10 is 170. Subtract from 234 to get 64. Then 17 times 3 is 51. Subtract from 64 to get the remainder. What is that remainder?",
        "answer": 13,
        "check": lambda r: "13" in r and "134" not in r.split("13")[0].split()[-1] if "13" in r else False,
    },
    # Level 2: Algebra with notation (works with translation)
    {
        "level": 2, "name": "quad_formula",
        "raw": "Solve x² − 5x + 6 = 0",
        "translated": "Solve the quadratic equation: x squared minus 5 times x plus 6 equals zero. Factor it: find two numbers that multiply to 6 and add to -5. Those numbers are -2 and -3. So x = 2 or x = 3.",
        "over_translated": "We have a quadratic equation to solve. The equation is x squared minus five times x plus six equals zero. A quadratic equation has the general form ax squared plus bx plus c equals zero. Here a=1, b=-5, c=6. We can factor this by finding two numbers that multiply to give us c (which is 6) and add to give us b (which is -5). What two numbers multiply to 6 and add to -5? Think about pairs: 1 and 6 (multiply to 6, add to 7), 2 and 3 (multiply to 6, add to 5), -2 and -3 (multiply to 6, add to -5). So we can write the equation as (x minus 2) times (x minus 3) equals zero. Setting each factor to zero: x minus 2 equals 0 gives x equals 2, and x minus 3 equals 0 gives x equals 3. What are the solutions?",
        "answer": "2,3",
        "check": lambda r: ("2" in r and "3" in r) and ("x=" in r.lower() or "x =" in r.lower() or "equals" in r.lower() or "is" in r.lower() or "solution" in r.lower()),
    },
    {
        "level": 2, "name": "matrix_det",
        "raw": "det([[3,1],[2,4]])",
        "translated": "Find the determinant of the 2 by 2 matrix with first row [3, 1] and second row [2, 4]. The determinant equals 3 times 4 minus 1 times 2, which equals 12 minus 2 equals 10.",
        "over_translated": "We need to find the determinant of a small matrix. The matrix has two rows and two columns. The first row contains the numbers 3 and 1. The second row contains the numbers 2 and 4. For a 2 by 2 matrix, the determinant formula is: take the top-left entry times the bottom-right entry, then subtract the top-right entry times the bottom-left entry. So we compute: 3 times 4 minus 1 times 2. First, 3 times 4 is 12. Then 1 times 2 is 2. Finally, 12 minus 2 gives us the determinant. What is it?",
        "answer": 10,
        "check": lambda r: "10" in r,
    },
    {
        "level": 2, "name": "log_solve",
        "raw": "Solve: log₂(x) = 5",
        "translated": "Solve for x: log base 2 of x equals 5. This means 2 to the power of 5 equals x. Compute 2^5 = 32. So x = 32.",
        "over_translated": "We need to solve a logarithmic equation. The equation says log base 2 of x equals 5. A logarithm log base 2 of x asks the question: 2 raised to what power gives us x? Since log base 2 of x equals 5, that means 2 raised to the 5th power equals x. Let's compute 2 to the 5th power: 2 times 2 equals 4, times 2 equals 8, times 2 equals 16, times 2 equals 32. So x equals what number?",
        "answer": 32,
        "check": lambda r: "32" in r and "325" not in r,
    },
    {
        "level": 2, "name": "system_eq",
        "raw": "Solve: 2x + 3y = 12, x − y = 1",
        "translated": "Solve the system of two equations: 2 times x plus 3 times y equals 12, and x minus y equals 1. From the second equation, x equals y plus 1. Substitute into the first: 2(y+1) + 3y = 12, so 2y + 2 + 3y = 12, so 5y = 10, y = 2, x = 3.",
        "over_translated": "We have two equations with two unknowns, x and y. Equation 1: two times x plus three times y equals twelve. Equation 2: x minus y equals one. We can solve by substitution. From Equation 2, we can express x in terms of y: x equals y plus one. Now substitute this into Equation 1: two times (y plus one) plus three times y equals twelve. Expand: two y plus two plus three y equals twelve. Combine like terms: five y plus two equals twelve. Subtract two: five y equals ten. Divide by five: y equals two. And since x equals y plus one, x equals three. What are x and y?",
        "answer": "x=3,y=2",
        "check": lambda r: ("3" in r and "2" in r),
    },
    # Level 3: Multi-step calculus (translation helps sometimes)
    {
        "level": 3, "name": "deriv_chain",
        "raw": "d/dx [sin(3x² + 1)]",
        "translated": "Find the derivative of sin(3x squared plus 1) with respect to x. Use the chain rule: derivative equals cos(3x² + 1) times the derivative of (3x² + 1), which is 6x. So the answer is 6x cos(3x² + 1).",
        "over_translated": "We need to differentiate a composite function using the chain rule. The function is the sine of (3 times x squared plus 1). The chain rule says: take the derivative of the outer function, evaluated at the inner function, times the derivative of the inner function. The outer function is sine, whose derivative is cosine. So we get cosine of (3x squared plus 1). The inner function is 3x squared plus 1, whose derivative is 6x. Multiplying these together: cosine of (3x squared plus 1) times 6x, which we can write as 6x cosine of (3x squared plus 1). What is the derivative?",
        "answer": "6x*cos(3x^2+1)",
        "check": lambda r: ("6x" in r or "6*x" in r) and ("cos" in r),
    },
    {
        "level": 3, "name": "integral_basic",
        "raw": "∫(2x³ + 3x) dx from 0 to 2",
        "translated": "Evaluate the definite integral from 0 to 2 of (2x cubed plus 3x) dx. First find the antiderivative: 2 times (x to the 4th divided by 4) plus 3 times (x squared divided by 2), which equals x⁴/2 + 3x²/2. Evaluate at x=2: 16/2 + 12/2 = 8 + 6 = 14. At x=0: 0. So the integral equals 14.",
        "over_translated": "We are computing a definite integral. The function we are integrating is 2x cubed plus 3x, and we integrate from x equals 0 to x equals 2. Step 1: Find the antiderivative. The antiderivative of 2x cubed is 2 times x to the 4th divided by 4, which simplifies to x to the 4th divided by 2. The antiderivative of 3x is 3 times x squared divided by 2. So the full antiderivative is x to the 4th over 2 plus 3 times x squared over 2. Step 2: Evaluate at the upper limit x equals 2. Two to the 4th is 16, divided by 2 is 8. Three times 4 is 12, divided by 2 is 6. So 8 plus 6 equals 14. Step 3: Evaluate at the lower limit x equals 0. Both terms are 0. Step 4: Subtract: 14 minus 0 equals the answer. What is it?",
        "answer": 14,
        "check": lambda r: "14" in r,
    },
    {
        "level": 3, "name": "taylor_exp",
        "raw": "Maclaurin series of e^x to 3rd order",
        "translated": "Find the Maclaurin series (Taylor series at x=0) of e to the power x, up to the third order term. The nth derivative of e to the x is always e to the x, evaluated at 0 gives 1. So the series is: 1 + x + x squared over 2 factorial + x cubed over 3 factorial, which simplifies to 1 + x + x²/2 + x³/6.",
        "over_translated": "The Maclaurin series is a special Taylor series centered at x equals zero. We want to expand e to the power x around zero, keeping terms up to third order. The general formula is: f of zero plus f prime of zero times x plus f double prime of zero times x squared over 2 factorial plus f triple prime of zero times x cubed over 3 factorial. For f of x equals e to the x, every derivative of e to the x is also e to the x. When we evaluate at x equals zero, e to the zero equals 1. So every coefficient is 1. The series becomes: 1 plus 1 times x plus 1 times x squared over 2 plus 1 times x cubed over 6. Simplifying: 1 plus x plus x squared over 2 plus x cubed over 6. What is the Maclaurin series up to third order?",
        "answer": "1+x+x^2/2+x^3/6",
        "check": lambda r: ("1" in r and "x" in r) and ("2" in r or "6" in r),
    },
    {
        "level": 3, "name": "multivar_deriv",
        "raw": "∂/∂x [x²y + y³] evaluated at (x,y) = (2,1)",
        "translated": "Find the partial derivative with respect to x of (x squared times y plus y cubed), then evaluate at x equals 2, y equals 1. The partial derivative treats y as a constant, so we get 2xy. Evaluating at x=2, y=1: 2 times 2 times 1 equals 4.",
        "over_translated": "A partial derivative with respect to x means we treat all other variables as constants and differentiate only with respect to x. Our function is x squared times y plus y cubed. When we take the partial derivative with respect to x, the term y cubed is treated as a constant (it has no x in it), so its derivative is zero. For x squared times y, we treat y as a constant multiplier. The derivative of x squared is 2x, so we get 2x times y. Therefore the partial derivative is 2xy. Now we evaluate this at x equals 2 and y equals 1: 2 times 2 times 1 equals 4. What is the value?",
        "answer": 4,
        "check": lambda r: "4" in r and "4x" not in r,
    },
    # Level 4: Novel proof/reasoning problems (translation may not help)
    {
        "level": 4, "name": "prove_irrational",
        "raw": "Prove √2 is irrational by contradiction.",
        "translated": "Prove that the square root of 2 is irrational. Use proof by contradiction. Assume √2 = p/q where p,q are integers with no common factors. Then p² = 2q², so p² is even, meaning p is even. Write p = 2k. Then 4k² = 2q², so q² = 2k², meaning q² is even and q is even. But then p and q share factor 2, contradicting our assumption. Therefore √2 is irrational.",
        "over_translated": "We want to prove that the square root of 2 cannot be written as a fraction of two integers. We will use proof by contradiction. This means we assume the opposite of what we want to prove, and show that this leads to a logical impossibility. Step 1: Assume, for the sake of contradiction, that the square root of 2 IS rational. This means there exist two integers p and q (with q not zero) such that square root of 2 equals p divided by q, AND p and q have no common factors (the fraction is in lowest terms). Step 2: Square both sides to get 2 equals p squared divided by q squared, which means p squared equals 2 times q squared. Step 3: Since p squared equals 2 times something, p squared must be an even number. Step 4: If p squared is even, then p itself must be even (the square of an odd number is odd). Step 5: Since p is even, we can write p as 2 times some integer k. Step 6: Substitute back: 2 times q squared equals p squared equals (2k) squared equals 4 times k squared. Step 7: Divide both sides by 2: q squared equals 2 times k squared. Step 8: By the same reasoning as before, q squared is even, so q is even. Step 9: Now both p and q are even, meaning they share the common factor 2. Step 10: But we assumed p and q have NO common factors! This is a contradiction. Therefore our assumption was wrong, and the square root of 2 is irrational. Does this proof work?",
        "answer": "contradiction",
        "check": lambda r: ("contradict" in r.lower() or "even" in r.lower()) and ("irrational" in r.lower() or "prove" in r.lower()),
    },
    {
        "level": 4, "name": "pigeonhole",
        "raw": "Prove: Among any 13 integers, at least two have the same remainder mod 12.",
        "translated": "Use the pigeonhole principle to prove: among any 13 integers, at least two have the same remainder when divided by 12. There are only 12 possible remainders (0 through 11). With 13 integers and only 12 possible remainders, by the pigeonhole principle, at least two integers must map to the same remainder class.",
        "over_translated": "This is an application of the pigeonhole principle, which states that if you put more items into fewer containers, at least one container must hold more than one item. Here, our 'items' are the 13 integers and our 'containers' are the possible remainders when dividing by 12. When you divide any integer by 12, the possible remainders are 0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, and 11. That's exactly 12 possible remainders. We have 13 integers, each producing one of these 12 remainders. Since 13 is greater than 12, by the pigeonhole principle, at least two of the 13 integers must produce the same remainder. Is this proof valid?",
        "answer": "pigeonhole",
        "check": lambda r: ("pigeonhole" in r.lower() or "pigeon hole" in r.lower() or ("same remainder" in r.lower()) or ("13" in r and "12" in r)),
    },
    {
        "level": 4, "name": "induction_sum",
        "raw": "Prove by induction: 1+2+...+n = n(n+1)/2 for all n≥1",
        "translated": "Prove by mathematical induction that the sum 1 plus 2 plus dot dot dot plus n equals n times (n plus 1) divided by 2, for all positive integers n. Base case n=1: left side is 1, right side is 1 times 2 divided by 2 equals 1. Check. Inductive step: assume true for k. Then for k+1: sum from 1 to k+1 equals k(k+1)/2 plus (k+1) equals (k+1)(k/2 + 1) equals (k+1)(k+2)/2. This matches the formula with n replaced by k+1. QED.",
        "over_translated": "Mathematical induction works in two steps. First we verify the base case, then we show that if the statement holds for some value k, it must also hold for k plus 1. Base case: when n equals 1, the left side is just 1. The right side is 1 times (1 plus 1) divided by 2, which is 1 times 2 divided by 2, which equals 1. Both sides match, so the base case works. Inductive hypothesis: assume the formula is true for some positive integer k. That is, assume 1 plus 2 plus dot dot dot plus k equals k times (k plus 1) divided by 2. Inductive step: we need to prove it for k plus 1. The sum from 1 to k plus 1 equals the sum from 1 to k, plus the term k plus 1. By our hypothesis, this equals k times (k plus 1) divided by 2, plus k plus 1. Factor out k plus 1: we get (k plus 1) times (k over 2 plus 1), which equals (k plus 1) times (k plus 2) divided by 2. This is exactly the formula with n replaced by k plus 1. Therefore the formula holds for all positive integers. Does this complete the proof?",
        "answer": "induction",
        "check": lambda r: ("base" in r.lower() or "induct" in r.lower()) and ("k+1" in r or "k plus 1" in r.lower() or "n(n+1)" in r or "(k+1)" in r),
    },
    {
        "level": 4, "name": "euler_path",
        "raw": "Does K₅ have an Euler circuit? Justify.",
        "translated": "Does the complete graph on 5 vertices (called K5) have an Euler circuit? An Euler circuit exists if and only if every vertex has even degree. In K5, each vertex is connected to the other 4 vertices, so every vertex has degree 4, which is even. Therefore yes, K5 does have an Euler circuit.",
        "over_translated": "An Euler circuit is a path through a graph that visits every edge exactly once and returns to the starting vertex. Euler's theorem states that a connected graph has an Euler circuit if and only if every vertex has an even degree (an even number of edges touching it). K5 is the complete graph on 5 vertices, meaning every vertex is connected to every other vertex. Since there are 5 vertices total, each vertex has edges to the other 4 vertices. So every vertex has degree 4. Since 4 is an even number, and every vertex has even degree, by Euler's theorem, K5 does have an Euler circuit. We can construct one explicitly: starting from any vertex, we can trace a path that uses every edge exactly once and returns to start, visiting all 10 edges. Does K5 have an Euler circuit?",
        "answer": "yes",
        "check": lambda r: ("yes" in r.lower() or "true" in r.lower() or "does have" in r.lower() or "has an euler" in r.lower()) and ("4" in r or "even" in r.lower()),
    },
    # Level 5: Research-level math (likely ceiling)
    {
        "level": 5, "name": "eisenstein_norm",
        "raw": "Compute the Eisenstein norm ‖(2,3)‖ = a²−ab+b²",
        "translated": "Using the Eisenstein norm: compute a squared minus a times b plus b squared, where a equals 2 and b equals 3. First, compute a squared: 2 times 2 equals 4. Then compute a times b: 2 times 3 equals 6. Then compute b squared: 3 times 3 equals 9. Finally, 4 minus 6 plus 9 equals 7. The Eisenstein norm is 7.",
        "over_translated": "The Eisenstein norm is a mathematical concept from number theory related to the Eisenstein integers (complex numbers of the form a plus b times omega, where omega is a primitive cube root of unity). The norm function maps each Eisenstein integer to a non-negative integer. For the Eisenstein integer with coordinates a=2 and b=3, the norm is defined as a squared minus a times b plus b squared. Let me walk through every single arithmetic step. We have a equals 2 and b equals 3. Step A: compute a squared. This means 2 times 2, which equals 4. Step B: compute a times b. This means 2 times 3, which equals 6. Step C: compute b squared. This means 3 times 3, which equals 9. Step D: combine using the formula: a squared minus a times b plus b squared. Substitute: 4 minus 6 plus 9. Going left to right: 4 minus 6 equals negative 2. Then negative 2 plus 9 equals 7. So the Eisenstein norm of the point (2, 3) equals 7. What is the final answer?",
        "answer": 7,
        "check": lambda r: "7" in r and "27" not in r,
    },
    {
        "level": 5, "name": "mobius_func",
        "raw": "Compute μ(30) where μ is the Möbius function",
        "translated": "Using the Möbius function: compute mu of 30. First factorize 30: 30 equals 2 times 3 times 5. There are 3 distinct prime factors, none repeated. The Möbius function gives (-1) raised to the number of distinct prime factors. So mu of 30 equals (-1) cubed equals -1.",
        "over_translated": "The Möbius function mu(n) is an important function in number theory used in the Möbius inversion formula. Its definition has three cases. Case 1: if n equals 1, then mu of 1 equals 1. Case 2: if n has a squared prime factor (that is, some prime p where p squared divides n), then mu of n equals 0. Case 3: if n is a product of k distinct prime factors (no repeats), then mu of n equals (-1) to the power k. Now let's compute mu of 30. First, factorize 30 into primes. 30 divided by 2 is 15. 15 divided by 3 is 5. 5 is prime. So 30 equals 2 times 3 times 5. We have 3 distinct prime factors: 2, 3, and 5. None are repeated, so we are in Case 3 with k equals 3. Therefore mu of 30 equals (-1) to the power 3, which equals -1. What is mu of 30?",
        "answer": -1,
        "check": lambda r: "-1" in r or "minus 1" in r.lower() or "negative 1" in r.lower(),
    },
    {
        "level": 5, "name": "legendre_symbol",
        "raw": "Compute the Legendre symbol (7|11)",
        "translated": "Using the Legendre symbol for quadratic residues: compute (7|11), which asks whether 7 is a quadratic residue modulo 11. List all squares mod 11: 1 squared is 1, 2 squared is 4, 3 squared is 9, 4 squared is 16 which is 5 mod 11, 5 squared is 25 which is 3 mod 11. The quadratic residues mod 11 are: 1, 3, 4, 5, 9. Is 7 in this list? No, 7 is not a quadratic residue mod 11. So the Legendre symbol (7|11) equals -1.",
        "over_translated": "The Legendre symbol (a|p) is a function from number theory that tells us whether an integer a is a quadratic residue modulo an odd prime p. It equals 1 if a is a quadratic residue (meaning there exists some x such that x squared is congruent to a modulo p), equals -1 if a is not a quadratic residue, and equals 0 if p divides a. We want to compute the Legendre symbol (7|11), meaning a=7 and p=11. Since 11 is an odd prime and 7 is not divisible by 11, the answer is either 1 or -1. To determine which, we list all quadratic residues modulo 11. Compute x squared mod 11 for x from 1 to 5 (we only need to go to 5 since x and 11-x give the same square mod 11): 1 squared is 1, 2 squared is 4, 3 squared is 9, 4 squared is 16 which reduces to 5 mod 11, 5 squared is 25 which reduces to 3 mod 11. So the set of quadratic residues mod 11 is {1, 3, 4, 5, 9}. Is 7 in this set? Looking through: 1 is not 7, 3 is not 7, 4 is not 7, 5 is not 7, 9 is not 7. Therefore 7 is NOT a quadratic residue mod 11, and the Legendre symbol (7|11) equals -1. What is the value?",
        "answer": -1,
        "check": lambda r: "-1" in r or "minus 1" in r.lower() or "negative 1" in r.lower(),
    },
    {
        "level": 5, "name": "cyclotomic_eval",
        "raw": "Evaluate cyclotomic polynomial Φ₃(2)",
        "translated": "Using the cyclotomic polynomial: evaluate Phi sub 3 at x equals 2. The third cyclotomic polynomial Phi sub 3 of x equals x squared plus x plus 1. Evaluating at x=2: 2 squared plus 2 plus 1 equals 4 plus 2 plus 1 equals 7. So Phi sub 3 of 2 equals 7.",
        "over_translated": "Cyclotomic polynomials are special polynomials whose roots are the primitive nth roots of unity. The nth cyclotomic polynomial Phi sub n of x is the minimal polynomial of a primitive nth root of unity. For n equals 3, we need the primitive cube roots of unity. The cube roots of 1 are 1, and the two complex roots. Phi sub 3 factors out the root at 1, leaving us with the polynomial x squared plus x plus 1. Let's verify: the 3rd cyclotomic polynomial equals x cubed minus 1 divided by x minus 1. Dividing x cubed minus 1 by x minus 1 gives x squared plus x plus 1. Now evaluate this at x equals 2: compute 2 squared which is 4, plus 2 which gives 6, plus 1 which gives 7. So Phi sub 3 of 2 equals 7. What is the value?",
        "answer": 7,
        "check": lambda r: "7" in r and "17" not in r and "27" not in r,
    },
]


def query_model(model: str, prompt: str, max_retries=2) -> dict:
    """Send a single query to a model via DeepInfra."""
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.0,
        "max_tokens": 512,
    }
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json",
    }
    for attempt in range(max_retries + 1):
        try:
            resp = requests.post(ENDPOINT, json=payload, headers=headers, timeout=60)
            resp.raise_for_status()
            data = resp.json()
            content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
            return {"content": content, "error": None}
        except Exception as e:
            if attempt < max_retries:
                time.sleep(3 * (attempt + 1))
            else:
                return {"content": "", "error": str(e)}


def run_experiment():
    import sys
    # Allow resuming from a saved partial results file
    save_path = "/home/phoenix/.openclaw/workspace/experiments/study70_results.json"
    results = []
    if os.path.exists(save_path):
        with open(save_path) as f:
            results = json.load(f)
        print(f"Resuming from {len(results)} existing results")

    # Build set of already-done keys
    done = {(r["problem"], r["model"], r["condition"]) for r in results}

    total = len(PROBLEMS) * len(MODELS) * 3
    count = len(results)

    for problem in PROBLEMS:
        for model in MODELS:
            for condition_name, prompt_key in [("A_raw", "raw"), ("B_translated", "translated"), ("C_over_translated", "over_translated")]:
                key = (problem["name"], model, condition_name)
                if key in done:
                    continue
                count += 1
                prompt = problem[prompt_key]
                print(f"[{count}/{total}] L{problem['level']} | {problem['name'][:16]:16s} | {model.split('/')[-1][:15]:15s} | {condition_name}")
                sys.stdout.flush()

                result = query_model(model, prompt)
                content = result["content"]
                error = result["error"]

                correct = problem["check"](content) if content and not error else False

                results.append({
                    "level": problem["level"],
                    "problem": problem["name"],
                    "model": model,
                    "condition": condition_name,
                    "prompt": prompt[:200],
                    "response": content[:500],
                    "error": error,
                    "correct": correct,
                    "expected_answer": str(problem["answer"]),
                })

                # Save incrementally
                with open(save_path, "w") as f:
                    json.dump(results, f, indent=2, ensure_ascii=False)

                time.sleep(0.3)

    return results


def analyze(results):
    """Compute accuracy by level × model × condition."""
    from collections import defaultdict

    buckets = defaultdict(lambda: {"total": 0, "correct": 0})

    for r in results:
        key = (r["level"], r["model"].split("/")[-1], r["condition"])
        buckets[key]["total"] += 1
        if r["correct"]:
            buckets[key]["correct"] += 1

    # Print matrix
    print("\n" + "=" * 90)
    print("STUDY 70: TRANSLATION CEILING — ACCURACY MATRIX")
    print("=" * 90)

    levels = sorted(set(r["level"] for r in results))
    models_short = sorted(set(r["model"].split("/")[-1] for r in results))
    conditions = ["A_raw", "B_translated", "C_over_translated"]

    for level in levels:
        print(f"\n--- Level {level} ---")
        print(f"{'Model':<25s} | {'Raw':>6s} | {'Translated':>10s} | {'Over-Trans':>10s} | {'Best Cond':>10s}")
        print("-" * 75)
        for model_s in models_short:
            accs = {}
            for cond in conditions:
                key = (level, model_s, cond)
                b = buckets[key]
                accs[cond] = (b["correct"] / b["total"] * 100) if b["total"] > 0 else 0
            best = max(accs, key=accs.get)
            print(f"{model_s:<25s} | {accs['A_raw']:5.0f}% | {accs['B_translated']:9.0f}% | {accs['C_over_translated']:9.0f}% | {best:>10s}")

    # Summary by level (all models combined)
    print("\n" + "=" * 90)
    print("SUMMARY BY LEVEL (all models)")
    print("=" * 90)
    for level in levels:
        accs = {}
        for cond in conditions:
            total = sum(buckets[(level, m, cond)]["total"] for m in models_short)
            correct = sum(buckets[(level, m, cond)]["correct"] for m in models_short)
            accs[cond] = (correct / total * 100) if total > 0 else 0
        print(f"Level {level}: Raw={accs['A_raw']:.0f}%  Translated={accs['B_translated']:.0f}%  Over-Trans={accs['C_over_translated']:.0f}%")

    # Summary by model (all levels combined)
    print("\n" + "=" * 90)
    print("SUMMARY BY MODEL (all levels)")
    print("=" * 90)
    for model_s in models_short:
        accs = {}
        for cond in conditions:
            total = sum(buckets[(l, model_s, cond)]["total"] for l in levels)
            correct = sum(buckets[(l, model_s, cond)]["correct"] for l in levels)
            accs[cond] = (correct / total * 100) if total > 0 else 0
        print(f"{model_s}: Raw={accs['A_raw']:.0f}%  Translated={accs['B_translated']:.0f}%  Over-Trans={accs['C_over_translated']:.0f}%")

    return buckets


if __name__ == "__main__":
    print("Study 70: Translation Ceiling Experiment")
    print(f"Models: {len(MODELS)}")
    print(f"Problems: {len(PROBLEMS)}")
    print(f"Conditions: 3 (raw, translated, over-translated)")
    print(f"Total queries: {len(PROBLEMS) * len(MODELS) * 3}")
    print()

    results = run_experiment()

    # Save raw results
    with open("/home/phoenix/.openclaw/workspace/experiments/study70_results.json", "w") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    print(f"\nSaved {len(results)} results to study70_results.json")

    # Analyze
    buckets = analyze(results)

    # Key findings
    from collections import defaultdict
    conditions = ["A_raw", "B_translated", "C_over_translated"]
    levels = sorted(set(r["level"] for r in results))
    models_short = sorted(set(r["model"].split("/")[-1] for r in results))

    print("\n" + "=" * 90)
    print("KEY FINDINGS")
    print("=" * 90)

    # Where does translation help most?
    for level in levels:
        raw_total = sum(buckets[(level, m, "A_raw")]["correct"] for m in models_short)
        trans_total = sum(buckets[(level, m, "B_translated")]["correct"] for m in models_short)
        over_total = sum(buckets[(level, m, "C_over_translated")]["correct"] for m in models_short)
        raw_n = sum(buckets[(level, m, "A_raw")]["total"] for m in models_short)
        trans_n = sum(buckets[(level, m, "B_translated")]["total"] for m in models_short)
        over_n = sum(buckets[(level, m, "C_over_translated")]["total"] for m in models_short)

        raw_pct = raw_total / raw_n * 100 if raw_n else 0
        trans_pct = trans_total / trans_n * 100 if trans_n else 0
        over_pct = over_total / over_n * 100 if over_n else 0

        delta_trans = trans_pct - raw_pct
        delta_over = over_pct - raw_pct
        print(f"Level {level}: Translation delta = {delta_trans:+.0f}%, Over-translation delta = {delta_over:+.0f}%")

    # Model-specific ceiling
    print("\nModel-specific ceilings:")
    for model_s in models_short:
        for level in levels:
            accs = {}
            for cond in conditions:
                b = buckets[(level, model_s, cond)]
                accs[cond] = (b["correct"] / b["total"] * 100) if b["total"] > 0 else 0
            best_acc = max(accs.values())
            if best_acc < 50:
                print(f"  {model_s}: CEILING at Level {level} (best={best_acc:.0f}%)")
                break
        else:
            print(f"  {model_s}: No ceiling within tested levels (all ≥50%)")
