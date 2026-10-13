# zebra-taocp

Algorithms from D. E. Knuth, *The Art of Computer Programming*, written in
[Zebra](https://github.com/torial/zebra-language), each checked against a result defined
outside this repository.

```bash
zebra taocp_test.zbr                      # the everyday suite, under a minute
zebra --release taocp_heavy_test.zbr      # the two large pentomino boxes, a few minutes
python tools/mutants.py --zebra <zebra>   # every check seen to fail (~1 min), memory-capped
```

**Memory.** The suites are small: measured with the whole process tree sampled, the everyday
suite peaks near 300 MB including the zig compile (the program itself about 100 MB), the heavy
suite similar, and a cold `--release` build about 1 GB. A mutant is a different matter -- one
that never terminates can allocate without bound. On 2026-10-12 the Algorithm T mutant that
queues a node too early looped and appended for a 900-second timeout; measured afterwards, it
reaches 8.8 GB working set and 16.7 GB committed within a minute, and it slowed the machine for
other work while the harness scored it, correctly but silently, as killed. `tools/mutants.py`
now runs every mutant under `tools/run_capped.py` (a Windows Job Object, 1 GB, 300 s), which
stops that mutant in seconds. The cap is not tight -- the overshoot is about one allocation,
measured up to ~3x -- so read it as "a runaway stops quickly", not "never exceeds 1 GB".

## Why these, and why checked this way

Almost every test of a compiler asserts what its own authors decided was correct. TAOCP
offers the opposite: algorithms with published outputs, worked examples, and counts with
closed forms. A wrong answer here is wrong by Knuth's account, not by ours, which makes the
library a correctness witness for the Zebra compiler as well as a library.

Each algorithm keeps Knuth's step labels (`E1`, `H2`, `Q7`, ...) in comments so it can be
read beside the book. Where the book states a precondition or postcondition, it is a Zebra
contract (`require` / `ensure` / `invariant`): checked in an ordinary build, removed by
`zebra --turbo`.

## Contents and their oracles

| algorithm | TAOCP | checked against |
|---|---|---|
| `RanArray` — subtractive lagged-Fibonacci generator (`ran_start`, `ran_array`, `ran_arr_next`) | Vol. 2 §3.6 | Knuth's own `rng.c` test: `ran_x[0] = 995235265`, reached two ways |
| `gcd` — Algorithm E (Euclid) | Vol. 1 §1.1 | the book's example: gcd(544, 119) = 17 |
| `spectralTest` — Algorithm S, ν₂..ν_t for a linear congruential generator | Vol. 2 §3.3.4 | exhaustive search on 16 generators (64/64); RANDU's ν₃² = 118, from 9 − 6a + a² ≡ 0 (mod 2³¹) -- its triples lie on 15 planes; the invariant U·Vᵀ = m·I asserted after every reduction |
| `binaryGcd` — Algorithm B | Vol. 2 §4.5.2 | agrees with Algorithm E on all 3,600 pairs 1..60 |
| `powMod` — Algorithm A, right-to-left binary powers | Vol. 2 §4.6.3 | Fermat's little theorem for p = 1000000007, bases 2..20 |
| `mpDivide` — Algorithm D, multiple-precision division (any base to 2¹⁶) | Vol. 2 §4.3.1 | 3,000 base-2⁸ divisions against `int128`, with the rare add-back step D6 seen to run (11 times); 300 base-2¹⁶ divisions by u = q·v + r, r < v (Algorithms M and A) |
| `insertionSort` — Algorithm S | Vol. 3 §5.2.1 | agrees with heapsort on 1,000 generated keys |
| `quickSort` / `quickSortM` — Algorithm Q (cutoff M, default 9) | Vol. 3 §5.2.2 | agrees with heapsort (M = 9 and M = 1); sorts Knuth's sixteen keys |
| `heapSort` — Algorithm H | Vol. 3 §5.2.3 | Knuth's sixteen standard keys for Chapter 5 |
| `binarySearch` — Algorithm B | Vol. 3 §6.2.1 | positions in the sorted standard keys |
| `grayCodes` — Algorithm G | Vol. 4A §7.2.1.1 | the closed form g(k) = k ⊕ ⌊k/2⌋, n = 10 |
| `combinations` — Algorithm L, lexicographic (colex) combinations | Vol. 4A §7.2.1.3 | the bitmasks with t bits set in increasing order, every 1 ≤ t ≤ n ≤ 10 (55/55); C(10,5) = 252 |
| `nextPermutation` — Algorithm L | Vol. 4A §7.2.1.2 | 4! = 24; multinomials 4!/(2!2!) = 6 and 6!/(1!2!3!) = 60 |
| `ExactCover` — Algorithm X, dancing links; `queens(n)` | Vol. 4B §7.2.2.1 | Knuth's example (5) and its single solution; n-queens counts for n = 1..8 (OEIS A000170) |
| `ExactCover.addColoredOption` — Algorithm C, color controls | Vol. 4B §7.2.2.1 | Knuth's colored example and its single solution; 50 generated problems against exhaustive search over every subset of options (50/50, 235 solutions) |
| `topologicalSort` — Algorithm T | Vol. 1 §2.2.3 | Knuth's example relations (18): a valid order; adding 6 ≺ 3 closes a loop and the output comes up short; 200 random DAGs (200/200) |
| `minstdNext` — the "minimal standard" X ← 16807X mod (2³¹ − 1), by Schrage's method | Vol. 2 §3.2.1.1, §3.6 | Park and Miller's check value X₁₀₀₀₀ = 1043618065 from X₀ = 1; agrees with the direct product at all 10,000 steps |
| `isProbablePrime` — Algorithm P, the strong probable-prime test (Miller–Rabin), 128-bit | Vol. 2 §4.5.4 | π(10⁵) = 9592, and a sieve agrees; fooled exactly where it should be: 2047 (base 2) and 3215031751 (bases 2, 3, 5, 7), each exposed by one more base; 2³¹ − 1 and 2⁶¹ − 1 prime, 2⁵⁹ − 1 not |
| `AvlTree` — Algorithm A, balanced tree insertion | Vol. 3 §6.2.3 | 2,000 random insertions: symmetric order = the sorted distinct keys, every balance factor equals the recomputed height difference, Theorem A in its exact form N ≥ F(h+2) − 1; 1..2ᵏ−1 inserted in order give a perfect tree of height k (k = 1..10) |
| `partitions` — Algorithm P, partitions in reverse lexicographic order | Vol. 4A §7.2.1.4 | p(n) for n = 1..20 and p(30) = 5604 (OEIS A000041); every visit sums to n, parts nonincreasing, order strictly decreasing |
| `setPartitions` — Algorithm H, restricted growth strings | Vol. 4A §7.2.1.5 | the Bell numbers for n = 1..9 (OEIS A000110); S(5, k) = 1, 15, 25, 10, 1 (Stirling numbers of the second kind); every string a restricted growth string, order strictly increasing |
| `nestedParentheses` — Algorithm P | Vol. 4A §7.2.1.6 | the Catalan numbers for n = 1..10 (OEIS A000108); every string balanced; the order strictly monotone |
| `langford` — Langford pairs as exact cover | Vol. 4B §7.2.2.1 | twice OEIS A014552 for n = 1..8 (each sequence and its reversal), every solution decoded and checked as a sequence |
| `pentominoBox` — the twelve pentominoes as exact cover | Vol. 4B §7.2.2.1 | 63 fixed orientations; 3 × 20 has 2 solutions; and in `taocp_heavy_test.zbr`, 6 × 10 has 2339 (Haselgrove, 1960) and 4 × 15 has 368 |

Every check has also been seen to FAIL: a one-line mutation of the generator's lag, of
heapsort's step H6, of quicksort's step Q4, of the Gray-code output, of Algorithm C's purify
(12/50), of Algorithm D's step D6 (exactly the 11 add-back cases fail) and of the
combinations' visit (0/55) each turns the corresponding line (or contract) red. A check
never seen red is not evidence.

The second batch (2026-10-12) was held to the same rule, one mutant per algorithm, each run on
a copy of the repository (11 in all, every one killed). Where it could be, the mutant is a
mistake someone would make rather than an arbitrary edit: Schrage's r off by one (X₁₀₀₀₀
becomes 590018985 and 9998 steps disagree); Miller–Rabin forgetting the −1 exit (300 primes
below 10⁵); Algorithm H never raising m (the Bell column becomes powers of two); Algorithm P
of §7.2.1.6 resetting m to k -- the first draft's own misreading -- (1372 malformed strings);
a Langford copy one slot too close; one of the eight motions lost (58 orientations); Algorithm
T forgetting to count a relation (the example fails, 1/200 random DAGs pass); a wrong balance
factor in step A9 (102 bad nodes). Two observations from it. Mutants of the partition
algorithm's bookkeeping did not reach the check at all: they ran off the end of the array and
Zebra's bounds check stopped the run, so a visit-level mutant was added (dropping the last
part), which the check catches with the counts still RIGHT -- 3339 malformed partitions,
p(n) unchanged. The per-visit checks are what see it; the count alone would have passed. And
the first Algorithm T mutant hung rather than answering, which is detection by timeout; its
replacement is caught by the check itself.

## Notes for a maintainer

- **`ran_array` is a translation, not Knuth's file.** `rng.c` is public domain on the
  condition that it is copied unchanged; this is a Zebra rendering of the algorithm it
  implements (the 9th-printing / 2002 version), credited to Knuth, with his 2019 test values.
- **Indices are 0-based.** Where the book's 1-based subscripts make a step clearer, the code
  keeps them and subtracts one at the access (`k[j - 1]` for K_j).
- **The spectral test was wrong twice before it was right, and the checks found both.** A
  misremembered sign in step S3 and a misremembered coordinate in step S4 each left ν₂
  correct (S3 computes it directly) and every later ν_t too large. Exhaustive search caught
  13 disagreements; asserting Knuth's invariant U·Vᵀ = m·I named the faulty step. It runs in
  128-bit integers: with m near 2³¹ the dot products pass 2⁶².
- **Algorithm Q drops the K_{N+1} = +∞ sentinel** and bounds step Q3's scan by `r`, which
  stops at the same place. Algorithm X keeps Knuth's array layout (item headers, spacers,
  TOP/ULINK/DLINK) unchanged, as a state machine over steps X2–X8.
- **A contract can cost more than its algorithm.** `binarySearch` requires sorted keys, an
  O(N) check on an O(log N) search: an ordinary build is linear there, a `--turbo` build
  logarithmic. Kept deliberately — a binary search over unsorted keys answers confidently
  and wrongly — and recorded because a complexity annotation would have to account for it.
- **Algorithm P of §7.2.1.6 assumes n ≥ 2.** With one pair, step P3's easy-case test reads
  the sentinel a₀ = ')' as a right parenthesis and walks off the front of the array; the test
  found it (a hand trace at n = 2 could not), and n = 1 is answered directly. Step P5 resets
  m to 2n − 1, where step P4 left the last left parenthesis -- the first version set m to the
  loop's final k, which breaks the invariant at n = 3; the mutant that restores it is in the
  set below.
- **The X pentomino counts each 6 × 10 solution once.** X is symmetric under all eight
  motions, so holding its centre to rows 0–2 and columns 0–4 picks one of the four images of
  every solution under the box's symmetries; the box has no centre row or column, so no
  solution is its own image. The 3 × 20 and 4 × 15 counts instead divide all solutions by 4,
  which is exact because twelve different pieces cannot each map onto themselves.
- **Requires zebra-language 68e80e3 or later.** This batch found two compiler bugs, and the
  code now uses the natural forms their fixes allow: `pentominoShapes` is one nested list
  literal across lines (BUG-561, `5e14144`), and the Stirling tally writes `stirling[mx] += 1`
  on a literal-bound list (BUG-562, `68e80e3`). Both were workarounds until the fixes landed;
  removing them was the test of the fixes, and the suite's output was identical, line for line.
- **The heavy suite is separate because it is slow in a debug build:** measured 2026-10-12 on
  a shared machine, 6 × 10 took 160 s in debug, 64 s with `--release` and 35 s with
  `--release --turbo` (each including compilation); 4 × 15 took 224 s in debug.
- **Requires zebra-language 0ad017b or later:** quicksort's stack uses `List.pop()`, which
  throws on an empty list (BUG-545, fixed there); the stack is checked non-empty first.

## Contracts have a cost, and a complexity annotation must say so

zebra-language's queue proposes complexity as reflection data, `Reflect.complexity(f)`, so
that a quadratic call inside a linear loop can be a compile-time diagnostic. This library is
meant to be the first body of honestly annotated code for it, and it shows one thing such an
annotation has to carry beyond `{ best, average, worst, space }`: **the cost of the
contracts, separately.**

- `binarySearch` is O(log N), and its precondition `isSorted(k)` is O(N). In an ordinary
  build, which checks contracts, the call is linear; under `--turbo`, which strips them, it is
  logarithmic. A diagnostic that read only the algorithm's cost would understate every
  ordinary build; one that read only the checked build would overstate the shipping one.
  **Measured** (2026-10-09, Debug, a busy machine; the ratio, not the milliseconds, is the
  point): 1,000 searches over 100,000 sorted keys took **22,046 ms checked and 8.1 ms under
  `--turbo`** -- about 2,700x, the order the arithmetic predicts (~17 comparisons per search
  against a 100,000-element precondition walk).
- The spectral test asserts Knuth's invariant U·Vᵀ = m·I after every reduction: O(t³) on top
  of a search that is far larger, so here the contract is cheap.
  `heapSort`'s `ensure isSorted(k)` is O(N) on an O(N log N) algorithm, also cheap.

So the proposal is an annotation of the shape
`{ best, average, worst, space, contracts }`, where `contracts` is the added cost when
checked, and a cost diagnostic that names which build it is reasoning about.

## License

MIT. The algorithms are Knuth's; see *The Art of Computer Programming*, Addison-Wesley.
