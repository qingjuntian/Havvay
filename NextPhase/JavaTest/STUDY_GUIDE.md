# Algorithm Puzzle Study Guide — interview refresh

A pattern-based cheat sheet for the ~65 puzzles in `src/puzzle/`, grounded in what each file
**actually** does. Use it to review by **pattern** (how interviews test recognition), not file-by-file.
The puzzles are organized into category sub-packages under `src/puzzle/<category>/` — see the
**Folder map** below.

> Each file implements a common `Puzzle` interface (`resolve()`), so any one can be dropped into
> `TryMe.java`'s `main()` and run. (`TryMe.java` imports every `puzzle.*` sub-package, so any puzzle
> is reachable by its simple class name.)

## How to use this
1. Skim the **Pattern recognition** table to reload the mental triggers.
2. For each pattern, re-derive the **template** from memory, then check it against the puzzles.
3. Prioritize **Tier 1** (shows up constantly). Skip the **incomplete/demo** files.

### Priority tiers
- **Tier 1 (must-know):** Two pointers, Sliding window, 1D/2D DP, Backtracking, Binary search on answer, Monotonic stack, LRU/LFU, Merge-sort inversions, BFS/DFS graph.
- **Tier 2 (good-to-have):** Heapsort/quicksort, LIS (patience), LCS, N-Queens/Sudoku, game theory (Nim), bit tricks.
- **Tier 3 (niche/Java-trivia):** NIO, generics erasure, geohash, thread stress.

---

## 📁 Folder map
Puzzles are grouped by **primary technique** into sub-packages under `src/puzzle/`. The shared
`Puzzle` interface stays in `src/puzzle/Puzzle.java`; `TryMe.java` imports all sub-packages.

| Folder | Files |
|--------|-------|
| `arrays/` (11) | ContainerWithMostWaterPuzzle, ThreeSumPuzzle, ThreeSumClosest, KDiffPairPuzzle, KDiffPair2Puzzle, SortColorPuzzle, NextPermutation, BalanceArrayPuzzle, SumDivisibleByLengthPuzzle, ArrayPatchPuzzle, JumpReachabilityPuzzle |
| `strings/` (4) | LongestDistSubString, LongestDistSubString2, DedupStringPuzzle, ParamParsePuzzle |
| `dp/` (10) | AlphabetParser, LISPuzzle, LongestCommonSubsequencePuzzle, LongestCommonSubstringPuzzle, MaxSubArrPuzzle, MaxProfitPuzzle, WordBreakPuzzle, PalindromePuzzle, TwoEggPuzzle, RussianDollEnvelopesPuzzle |
| `backtracking/` (5) | QueenPuzzle, PermutationsPuzzle, BeautifulPuzzle, Sudoku, ShoppingCartDiscountPuzzle |
| `binarysearch/` (2) | MedianOfTwoSortedArray, SplitPuzzle |
| `stack/` (3) | LargestRectangleHistogramPuzzle, LongestValidaParentheses, CommitStatementPuzzle |
| `linkedlist/` (4) | LinkedListPuzzle, SwapPairNode, RemoveDupListNodePuzzle, RightSpinListPuzzle |
| `graph/` (2) | TreeAncestor, BiSplitGraph |
| `cache/` (4) | LRUCachePuzzle, LFUCachePuzzle, LFUCachePuzzle2, LFUCachePuzzle3 |
| `sorting/` (4) | QuickSort, HeapSortPuzzle, SwingSort, InversionCountPuzzle |
| `math/` (10) | HammingDistancePuzzle, SumWithoutPlus, WythoffPuzzle, GridNimPuzzle, PolyPuzzle, VariancePuzzle, GeoHashPuzzle, EstimatePiPuzzle, MaxPointsOnLinePuzzle, BitSetTest |
| `concurrency/` (4) | ThreadNumber, MultiPortEcho, NioPuzzle, IpLocPuzzle |
| `misc/` (2) | SugerPuzzle, RegexPuzzle |

> A few puzzles are filed by *primary* technique even though a pattern section below references them
> elsewhere: `LargestRectangleHistogramPuzzle` & `LongestValidaParentheses` live in `stack/` (also cited under DP),
> `MaxPointsOnLinePuzzle` in `math/` (cited under graphs), `ArrayPatchPuzzle` in `arrays/` (cited under
> sorting), `TwoEggPuzzle` in `dp/` (cited under binary search), `RegexPuzzle` in `misc/`.

---

## ⚠️ Historical / still-misaligned names
Most of the worst class-name mismatches have now been cleaned up. The items below are the main remaining historical names worth keeping in mind during review:

| File | Name suggests | **Actually is** |
|------|---------------|-----------------|
| `IpLocPuzzle` | IP geolocation | **NIO file copy** (no algorithm) |
| `LongestDistSubString` | — | Longest substring with **≤ 2 distinct chars** |
| `LongestDistSubString2` | — | Longest substring **without repeating chars** (brute force) |
| `SugerPuzzle` | — | Java **generics type-erasure** demo (not an algorithm) |

## 🚧 Incomplete / demo / skip
Don't spend review time here — these are drafts, demos, or Java-API experiments:
`RegexPuzzle` (regex demo), `Sudoku` (solver incomplete), `SwingSort` (unfinished),
`LinkedListPuzzle` (usage demo), `BitSetTest` (API demo), `ThreadNumber` (thread stress test),
`NioPuzzle`/`IpLocPuzzle` (NIO file-copy).

---

## Pattern recognition cheat sheet
| If you see… | Reach for… | Puzzles |
|-------------|-----------|---------|
| Sorted array, find pair/triplet | **Two pointers** | ContainerWithMostWaterPuzzle, ThreeSumPuzzle, ThreeSumClosest, KDiffPairPuzzle |
| "Longest/shortest substring with property" | **Sliding window** | LongestDistSubString, LongestDistSubString2 |
| "Minimize the max / maximize the min" | **Binary search on the answer** | SplitPuzzle, TwoEggPuzzle |
| Optimal over subsequences/partitions | **DP** | LISPuzzle, LongestCommonSubsequencePuzzle, WordBreakPuzzle, MaxSubArrPuzzle, MaxProfitPuzzle, RegexPuzzle, AlphabetParser |
| "All arrangements / place items w/ constraints" | **Backtracking** | QueenPuzzle, PermutationsPuzzle, BeautifulPuzzle, Sudoku |
| "Next greater/smaller", histogram | **Monotonic stack** | LargestRectangleHistogramPuzzle, LongestValidaParentheses |
| O(1) get/put with eviction | **HashMap + linked structure** | LRUCache, LFUCache |
| Count pairs out of order | **Merge sort** | InversionCountPuzzle |
| 2-colorable / shortest unweighted | **BFS** | BiSplitGraph |
| Tree "both sides contain target" | **Postorder recursion** | TreeAncestor (LCA) |

---

## 1. Two pointers (Tier 1) — `puzzle/arrays/`
| Puzzle | Problem | Time/Space | Key insight |
|--------|---------|-----------|-------------|
| `ContainerWithMostWaterPuzzle` | Container With Most Water (+ Two Sum helper) | O(n)/O(1) | Move the **shorter** wall inward |
| `ThreeSumPuzzle` | 3Sum = 0, unique triplets | O(n²)/O(1) | Sort, fix i, two-pointer; **skip duplicates** |
| `ThreeSumClosest` | Triplet sum closest to target | O(n²)/O(1) | Track best on **every** step |
| `KDiffPairPuzzle` | Pairs with diff k (sort + binary search) | O(n log n) | Normalize `k = abs(k)` |
| `KDiffPair2Puzzle` | Same, via frequency map | O(n)/O(n) | `k==0` → need count≥2; `k>0` → existence |
| `SortColorPuzzle` | Sort {0,1,2} | O(n)/O(1) | Dutch flag; on swap-to-right **don't advance** cur |
| `NextPermutation` | Next lexicographic permutation | O(n)/O(1) | Find pivot from right, swap, reverse suffix |

**Template — two pointers on sorted array**
```java
Arrays.sort(a);
int lo = 0, hi = a.length - 1;
while (lo < hi) {
    int s = a[lo] + a[hi];
    if (s == target) { /* record */ lo++; hi--; }
    else if (s < target) lo++;
    else hi--;
}
```

## 2. Sliding window (Tier 1) — `puzzle/strings/`
| Puzzle | Problem | Time/Space | Key insight |
|--------|---------|-----------|-------------|
| `LongestDistSubString` | Longest substring, ≤2 distinct chars | O(n)/O(1) | Preserve last run length on reset |
| `LongestDistSubString2` | Longest substring w/o repeats (brute) | O(n²)/O(1) | **Rewrite as optimal window** for practice |

**Template — variable window (rewrite the brute-force one this way)**
```java
Map<Character,Integer> last = new HashMap<>();
int start = 0, best = 0;
for (int end = 0; end < s.length(); end++) {
    char c = s.charAt(end);
    if (last.containsKey(c) && last.get(c) >= start) start = last.get(c) + 1;
    last.put(c, end);
    best = Math.max(best, end - start + 1);
}
```

## 3. Binary search on the answer (Tier 1) — `puzzle/binarysearch/` · `TwoEggPuzzle` in `dp/`
| Puzzle | Problem | Time/Space | Key insight |
|--------|---------|-----------|-------------|
| `SplitPuzzle` | Split array into m parts, minimize largest sum | O(n log Σ) | Feasibility is **monotonic** |
| `TwoEggPuzzle` | Egg drop, min worst-case trials | O(n²m) DP | Also solvable by BS; recurrence `1+min max(break,¬break)` |
| `MedianOfTwoSortedArray` | Median of 2 sorted arrays | O(log(m+n)) | kth-element; recurse on **smaller** array |

**Template — binary search on a monotonic predicate**
```java
int lo = maxElem, hi = sum;               // answer range
while (lo < hi) {
    int mid = lo + (hi - lo) / 2;
    if (feasible(mid)) hi = mid;          // can do it → try smaller
    else lo = mid + 1;
}
return lo;
```

## 4. Dynamic programming (Tier 1) — `puzzle/dp/` · `LargestRectangleHistogramPuzzle`/`LongestValidaParentheses` in `stack/`, `RegexPuzzle` in `misc/`
| Puzzle | Problem | Time/Space | Key insight |
|--------|---------|-----------|-------------|
| `MaxSubArrPuzzle` | Maximum subarray (+ indices) | O(n)/O(n) | Kadane; suffix-DP variant here |
| `MaxProfitPuzzle` | Best time to buy/sell stock | O(n)/O(1) | `maxProfit2` = track running min |
| `LISPuzzle` | Longest increasing subseq | O(n log n) | **Patience/tails** + binary search |
| `LongestCommonSubsequencePuzzle` | Longest **common** subsequence | O(mn)/O(mn) | Match→diagonal+1, else max(top,left) |
| `LongestCommonSubstringPuzzle` | Longest **common substring** | O(mn)/O(n) | Update DP row **backwards**; reset on mismatch |
| `WordBreakPuzzle` | Segment into dict words | O(n·d·k)/O(n) | `t[0]=true` seed |
| `LargestRectangleHistogramPuzzle` | **Largest rectangle in histogram** | O(n)/O(n) | Monotonic increasing stack |
| `AlphabetParser` | Decode Ways (1→A…26→Z) | O(n)/O(1) | **Zero handling** is the trap |
| `RegexPuzzle`* | Regex/wildcard matching | — | *demo only; real DP is `dp[i][j]` on `*`/`.` |
| `PalindromePuzzle` | Longest palindromic substring | O(n²)/O(n²) | Base cases len 1 & 2 first |
| `LongestValidaParentheses` | Longest valid parens | O(n)/O(n) | Stack of indices + DP stitch |

**Template — 2D DP (LCS shape)**
```java
int[][] dp = new int[m+1][n+1];
for (int i = 1; i <= m; i++)
  for (int j = 1; j <= n; j++)
    dp[i][j] = (a.charAt(i-1) == b.charAt(j-1))
        ? dp[i-1][j-1] + 1
        : Math.max(dp[i-1][j], dp[i][j-1]);   // substring: else 0 + track max
```

## 5. Backtracking / recursion (Tier 1–2) — `puzzle/backtracking/`
| Puzzle | Problem | Time/Space | Key insight |
|--------|---------|-----------|-------------|
| `QueenPuzzle` | N-Queens | O(N!)/O(N) | Diagonals = `row+col` and `row-col` |
| `PermutationsPuzzle` | All permutations | O(n·n!)/O(n) | **Swap back** to restore state |
| `BeautifulPuzzle` | Beautiful Arrangement | O(n!)/O(n) | Divisibility test = the pruning rule |
| `Sudoku`* | Sudoku solver | — | *incomplete; practice full backtracking |
| `ShoppingCartDiscountPuzzle` | Min leftover after removing discount sets | exp. | Multiset backtracking; memoized state search is faster |

**Template — backtracking (permutations via swap)**
```java
void permute(int[] a, int k) {
    if (k == a.length) { record(a); return; }
    for (int i = k; i < a.length; i++) {
        swap(a, k, i);
        permute(a, k + 1);
        swap(a, k, i);          // undo
    }
}
```

## 6. Monotonic stack (Tier 1) — `puzzle/stack/`
| Puzzle | Problem | Time/Space | Key insight |
|--------|---------|-----------|-------------|
| `LargestRectangleHistogramPuzzle` | Largest rectangle in histogram | O(n)/O(n) | Pop when bar lower; width from new top |
| `LongestValidaParentheses` | Longest valid parens | O(n)/O(n) | Keep indices; stitch adjacent blocks |

**Template — monotonic increasing stack (histogram)**
```java
Deque<Integer> st = new ArrayDeque<>();
int best = 0;
for (int i = 0; i <= n; i++) {
    int h = (i == n) ? 0 : height[i];
    while (!st.isEmpty() && height[st.peek()] >= h) {
        int top = st.pop();
        int width = st.isEmpty() ? i : i - st.peek() - 1;
        best = Math.max(best, height[top] * width);
    }
    st.push(i);
}
```

## 7. Linked lists (Tier 1–2) — `puzzle/linkedlist/`
| Puzzle | Problem | Time/Space | Key insight |
|--------|---------|-----------|-------------|
| `SwapPairNode` | Swap nodes in pairs (+ reverseKGroup) | O(n)/O(1) | **Dummy head**; save `next` before rewiring |
| `RemoveDupListNodePuzzle` | Remove *all* dup values (sorted) | O(n)/O(1) | Delete the **whole** run, not extras |
| `RightSpinListPuzzle` | Rotate list right by k | O(n)/O(1) | Make cycle, walk to new tail, cut; `k %= len` |

**Template — dummy head**
```java
ListNode dummy = new ListNode(0); dummy.next = head;
ListNode prev = dummy;
// ... rewire using prev, always save next first ...
return dummy.next;
```

## 8. Trees & graphs (Tier 1) — `puzzle/graph/` · `MaxPointsOnLinePuzzle` in `math/`
| Puzzle | Problem | Time/Space | Key insight |
|--------|---------|-----------|-------------|
| `TreeAncestor` | Lowest Common Ancestor | O(n)/O(h) | Non-null from **both** children ⇒ root is LCA |
| `BiSplitGraph` | Is graph bipartite? | O(V·E)/O(V) | BFS 2-coloring; conflict ⇒ not bipartite |
| `MaxPointsOnLinePuzzle` | Max points on a line | O(n²)/O(n) | Anchor one point; group others by GCD-reduced slope |

**Template — LCA (binary tree)**
```java
TreeNode lca(TreeNode root, TreeNode p, TreeNode q) {
    if (root == null || root == p || root == q) return root;
    TreeNode l = lca(root.left, p, q), r = lca(root.right, p, q);
    return (l != null && r != null) ? root : (l != null ? l : r);
}
```

## 9. Cache design — O(1) (Tier 1) — `puzzle/cache/`
| Puzzle | Problem | Approach | Key insight |
|--------|---------|----------|-------------|
| `LRUCachePuzzle` | LRU cache | `LinkedHashMap(accessOrder=true)` + `removeEldestEntry` | The `true` flag **is** the trick |
| `LFUCachePuzzle` / `2` | LFU cache | Freq buckets as DLL of `Node(count, keys:LinkedHashSet)` + key→bucket map | Head bucket = lowest freq (evict) |
| `LFUCachePuzzle3` | LRU+LFU under one skeleton | timestamp/count map, evict min | Simpler but **O(n) eviction** (scans keys) |

**Template — true O(1) LFU skeleton**
```
maps:  key->value, key->freq, freq->LinkedHashSet<key>
minFreq tracker
get:   bump freq (move key freq→freq+1 bucket); if old bucket empty & ==minFreq → minFreq++
put:   if full → evict LinkedHashSet at minFreq (eldest); insert freq=1, minFreq=1
```

## 10. Sorting & divide-and-conquer (Tier 2) — `puzzle/sorting/` · `ArrayPatchPuzzle` in `arrays/`
| Puzzle | Problem | Time/Space | Key insight |
|--------|---------|-----------|-------------|
| `QuickSort` | In-place quicksort | O(n log n) avg | Leftmost pivot ⇒ sorted input degrades to O(n²) |
| `HeapSortPuzzle` | Heapsort | O(n log n)/O(1) | Build max-heap, swap root↔end, sift down |
| `InversionCountPuzzle` | Count inversions / reverse pairs | O(n log n)/O(n) | Count **during merge**: `mid-i+1` per right pick |
| `ArrayPatchPuzzle` | Patching Array (greedy) | O(n)/O(1) | Invariant: all sums in `[1, upper)` reachable |

**Template — inversion count in merge**
```java
// during merge of L and R:
if (L[i] <= R[j]) tmp[k++] = L[i++];
else { tmp[k++] = R[j++]; inversions += (midLenLeft - i); }  // all remaining L > R[j]
```

## 11. Math / bits / game theory (Tier 2–3) — `puzzle/math/`
| Puzzle | Problem | Time/Space | Key insight |
|--------|---------|-----------|-------------|
| `HammingDistancePuzzle` | Total Hamming distance | O(31n)/O(1) | Per bit: `ones * zeros` |
| `SumWithoutPlus` | Add without `+` | O(1)/O(1) | XOR = sum bits, (AND<<1) = carry, recurse |
| `WythoffPuzzle` | Wythoff's game | O(n)/O(1) | P-positions (⌊kφ⌋,⌊kφ²⌋), b−a=k; query `x==⌊(y−x)φ⌋` |
| `PolyPuzzle` | Convex polygon check | O(n)/O(1) | Cross-product sign must not flip |
| `VariancePuzzle` | Variance two ways | O(n)/O(1) | `E[X²]−(E[X])²` one-pass (less stable) |
| `GeoHashPuzzle` | Geohash encode | O(prec)/O(1) | Interleave lon/lat bits → base32 |

## 12. Java-specific / concurrency (Tier 3) — `puzzle/concurrency/` & `misc/`
`SugerPuzzle` (generics erasure — overloads collide after erasure), `MultiPortEcho` (NIO `Selector`
event loop, handle `OP_ACCEPT`/`OP_READ` separately), `NioPuzzle`/`IpLocPuzzle` (FileChannel copy:
`clear→read→flip→write`), `ThreadNumber` (thread-count stress test), `EstimatePiPuzzle` (Monte-Carlo,
currently dead-coded).

---

## Suggested 1-week refresh plan
- **Day 1–2:** Two pointers + Sliding window (rewrite `LongestDistSubString2` as an optimal window).
- **Day 3:** DP core (LCS/LIS/WordBreak/MaxSubArr) — re-derive each recurrence from scratch.
- **Day 4:** Backtracking (`QueenPuzzle`, `PermutationsPuzzle`, finish `Sudoku`).
- **Day 5:** Monotonic stack + Binary-search-on-answer (`MaxSquare`, `SplitPuzzle`).
- **Day 6:** Design (LRU/LFU — implement the **true O(1)** LFU), Merge-sort inversions.
- **Day 7:** Graphs/trees (LCA, bipartite) + mixed mock set.

**Tip:** for each, cover the file, re-implement from the template above, then diff against your old code.
