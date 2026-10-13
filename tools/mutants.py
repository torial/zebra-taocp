"""Every check in taocp_test.zbr must be seen to FAIL: one mutant per algorithm, each applied to
a COPY of the repository, the everyday suite run under a memory cap and a time limit, and the
check's output line compared with the unmutated run's.

A mutant is KILLED when its check's line changes, when the run fails, or when it hits a cap
(a hang or a runaway is a bug the suite noticed, but by its symptom rather than its check,
and the report says which). SURVIVED -- the line unchanged -- means the check cannot see that
bug, and the script exits 1.

Each mutant runs under tools/run_capped.py (1 GB job cap, 300 s): on 2026-10-12 one of these
mutants, run without a cap, looped and appended for 900 s and reached 16.7 GB committed.

usage: python tools/mutants.py [--zebra PATH] [--only SUBSTRING]
"""
import os
import shutil
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from run_capped import run_capped  # noqa: E402

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FILES = ('taocp.zbr', 'taocp_test.zbr')

# (name, file, original text, mutated text, prefix of the output line the check prints).
# Where it could be, the mutant is a mistake someone would make, not an arbitrary edit.
MUTANTS = [
    ('minstd: Schrage r off by one', 'taocp.zbr',
     'const MINSTD_R = 2836', 'const MINSTD_R = 2837', 'minstd:'),
    ('Miller-Rabin: forget the -1 exit', 'taocp.zbr',
     'if (j == 0 and y == 1) or y == n - 1', 'if (j == 0 and y == 1)', 'primes below'),
    ('partitions: the visit drops the last part', 'taocp.zbr',
     '            for i in 1 : m + 1\n                part.add(a[i])',
     '            for i in 1 : m\n                part.add(a[i])', 'partitions:'),
    ('set partitions: H6 never raises m', 'taocp.zbr',
     '            if a[j] == b[j]\n                m += 1\n', '', 'set partitions:'),
    ('parentheses: P5 sets m = k (the first draft\'s misreading)', 'taocp.zbr',
     '        a[j] = PAREN_L\n        m = 2 * n - 1\n', '        a[j] = PAREN_L\n        m = k\n', 'parentheses:'),
    ('langford: copies one slot too close', 'taocp.zbr',
     'ec.addOption([v, n + i, n + i + v + 1])', 'ec.addOption([v, n + i, n + i + v])', 'langford:'),
    ('pentominoes: lose one of the eight motions', 'taocp.zbr',
     '            else if t == 7\n', '            else if t == 99\n', 'pentomino orientations:'),
    ('topological sort: T3 forgets to count a relation', 'taocp.zbr',
     '        count[k] += 1\n        suc.add(k)\n', '        suc.add(k)\n', 'topological sort:'),
    ('topological sort: T4 queues a node with one predecessor (hangs; the cap stops it)', 'taocp.zbr',
     '        if count[k] == 0\n            qlink[rr] = k\n', '        if count[k] <= 1\n            qlink[rr] = k\n',
     'topological sort:'),
    ('AVL: A9 balance factor of S wrong', 'taocp.zbr',
     '            if .bal[p] == a\n                .bal[s] = 0 - a\n', '            if .bal[p] == a\n                .bal[s] = 0\n',
     'AVL: in order'),
    # batch 3 (2026-10-13)
    ('extended gcd: X3 uses v1 where v2 belongs', 'taocp.zbr',
     '        var t2: int = u2 - v2 * q', '        var t2: int = u2 - v1 * q', 'extended gcd:'),
    ('rho: double-and-add forgets to reduce the doubling', 'taocp.zbr',
     '        x = x + x\n        if x >= m\n            x -= m\n', '        x = x + x\n', 'factor 18446744073709551617'),
    ('plain changes: P5 forgets the offset s', 'taocp.zbr',
     '                var y: int = j - q + s', '                var y: int = j - q', 'plain changes:'),
    ('sideways addition: mu_1 one bit short', 'taocp.zbr',
     '    y = (y & 858993459) + ((y >> 2) & 858993459)', '    y = (y & 858993458) + ((y >> 2) & 858993459)', 'bit tricks:'),
    ('bitwise queens: one diagonal shifted the wrong way', 'taocp.zbr',
     '            c[l + 1] = (c[l] | t) >> 1', '            c[l + 1] = ((c[l] | t) << 1) & mask', 'queens, bitwise:'),
    ('buddy system: S1 merges with a buddy of another size', 'taocp.zbr',
     '            if .tag[p] == 0 or .kval[p] != k', '            if .tag[p] == 0', 'buddy system:'),
    ('merge insertion: search the whole chain, not below a_j', 'taocp.zbr',
     '                limit = listIndexOf(chain, a[j - 1])', '                limit = chain.count()', 'merge insertion:'),
    ('karatsuba: forget to subtract u1 v1 from the middle term', 'taocp.zbr',
     '    digitsSubInPlace(z1, z2, b)\n', '', 'karatsuba:'),
    # batch 4 (2026-10-13)
    ('radix conversion: pad inner groups to 3 digits, not 4', 'taocp.zbr',
     '        while g.len < 4\n', '        while g.len < 3\n', 'radix conversion vs int128'),
    ('linear probing: R4 forgets the wrap-around case', 'taocp.zbr',
     '            if (i <= r and r < j) or (r < j and j < i) or (j < i and i <= r)',
     '            if (i <= r and r < j) or (r < j and j < i)', 'linear probing:'),
    ('mixed-radix Gray: H5 forgets to reset f_{j+1}', 'taocp.zbr',
     '            f[j] = f[j + 1]\n            f[j + 1] = j + 1\n', '            f[j] = f[j + 1]\n', 'mixed-radix Gray:'),
    ('partitions into m parts: H3 tweaks while a_2 < a_1', 'taocp.zbr',
     '        if a[2] < a[1] - 1                   # H3.', '        if a[2] < a[1]                       # H3.',
     'partitions into m parts'),
    ('tree deletion: D3 drops the successor\'s right subtree', 'taocp.zbr',
     '                .llink[r] = .rlink[s]\n', '', 'search tree insert/delete:'),
]


def run(dirpath, zebra):
    r = run_capped([zebra, 'taocp_test.zbr'], dirpath, mem_mb=1024, timeout_s=300)
    return r


def line_for(out, prefix):
    for ln in out.splitlines():
        if ln.startswith(prefix):
            return ln
    return None


def copy_repo():
    d = tempfile.mkdtemp(prefix='zz_taocp_mut_')
    for f in FILES:
        shutil.copy(os.path.join(REPO, f), d)
    return d


def main():
    args = sys.argv[1:]
    zebra = os.environ.get('ZEBRA', 'zebra')
    only = None
    while args:
        if args[0] == '--zebra':
            zebra = args[1]; args = args[2:]
        elif args[0] == '--only':
            only = args[1]; args = args[2:]
        else:
            raise SystemExit(f'unknown option {args[0]}')
    base = copy_repo()
    b = run(base, zebra)
    shutil.rmtree(base, ignore_errors=True)
    if b.status != 'exit' or b.code != 0:
        print(f'REFUSING: the unmutated suite did not pass ({b.status}, code {b.code}, peak {b.peak_mb} MB)')
        sys.exit(2)
    print(f'unmutated suite: pass, peak {b.peak_mb} MB')
    survived = 0
    ran = 0
    for name, fname, old, new, prefix in MUTANTS:
        if only and only not in name:
            continue
        ran += 1
        want = line_for(b.output, prefix)
        if want is None:
            print(f'REFUSING: the unmutated output has no line starting {prefix!r}')
            sys.exit(2)
        d = copy_repo()
        p = os.path.join(d, fname)
        src = open(p, encoding='utf-8').read()
        if src.count(old) != 1:
            print(f'REFUSING: mutant {name!r}: its target text occurs {src.count(old)} times (need 1)')
            sys.exit(2)
        open(p, 'w', encoding='utf-8', newline='\n').write(src.replace(old, new))
        r = run(d, zebra)
        got = line_for(r.output, prefix)
        # The check's own line first: a run can print the changed line and THEN hang in a later
        # section (the Miller-Rabin mutant did, inside the factoring that relies on it).
        if got is not None and got != want:
            verdict = f'KILLED by the check: {got}'
            if r.status != 'exit':
                verdict += f'  (the run then hit the {r.status})'
        elif r.status in ('timeout', 'memory-cap'):
            verdict = f'KILLED by the {r.status} (peak {r.peak_mb} MB) -- detected by symptom, not by the check'
        elif got is None:
            verdict = f'KILLED (the run failed, code {r.code}; the check line is absent)'
        elif got != want:
            verdict = f'KILLED by the check: {got}'
        else:
            verdict = 'SURVIVED -- the check did not see this bug'
            survived += 1
        print(f'{name}: {verdict}')
        shutil.rmtree(d, ignore_errors=True)
    print(f'{ran - survived}/{ran} mutants killed')
    sys.exit(1 if survived else 0)


if __name__ == '__main__':
    main()
