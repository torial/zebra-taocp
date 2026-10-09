# zebra-taocp

Algorithms from D. E. Knuth, *The Art of Computer Programming*, written in
[Zebra](https://github.com/torial/zebra-language), each checked against a result defined
outside this repository.

```bash
zebra taocp_test.zbr
```

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

Every check has also been seen to FAIL: a one-line mutation of the generator's lag, of
heapsort's step H6, of quicksort's step Q4, of the Gray-code output, of Algorithm C's purify
(12/50), of Algorithm D's step D6 (exactly the 11 add-back cases fail) and of the
combinations' visit (0/55) each turns the corresponding line (or contract) red. A check
never seen red is not evidence.

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
- The spectral test asserts Knuth's invariant U·Vᵀ = m·I after every reduction: O(t³) on top
  of a search that is far larger, so here the contract is cheap.
  `heapSort`'s `ensure isSorted(k)` is O(N) on an O(N log N) algorithm, also cheap.

So the proposal is an annotation of the shape
`{ best, average, worst, space, contracts }`, where `contracts` is the added cost when
checked, and a cost diagnostic that names which build it is reasoning about.

## License

MIT. The algorithms are Knuth's; see *The Art of Computer Programming*, Addison-Wesley.
