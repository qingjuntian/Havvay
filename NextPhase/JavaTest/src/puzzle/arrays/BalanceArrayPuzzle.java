package puzzle.arrays;
import puzzle.Puzzle;

import java.util.ArrayList;
import java.util.Arrays;
import java.util.List;

/**
 * Given two equal-length arrays, swap elements to minimize the difference between their sums.
 * Approaches:
 *   balanceArray - recursive brute-force / backtracking over swap decisions;
 *   minDiffDp    - exact-cardinality subset-sum DP with reconstruction of one optimal split.
 * Complexity:
 *   brute-force = exponential time, O(n) recursion stack;
 *   DP          = pseudo-polynomial O(n^2 * S) time / O(n^2 * S) space, where
 *                 S = sum of absolute values across all 2n numbers.
 */
public class BalanceArrayPuzzle implements Puzzle {

    private int sum;

    @Override
    public void resolve() {
        int[] arr1 = {1, 2, 7, 6, 43, 17};
        int[] arr2 = {3, 4, 5, 12, 11, -5};

        if (arr1.length != arr2.length || arr1.length <=1 ) return;

        sum = Arrays.stream(arr1).sum() + Arrays.stream(arr2).sum();
        System.out.println("DP min |sumA - sumB|: " + minDiffDp(arr1, arr2));
        balanceArray(arr1, arr2, arr1.length, calculateDiff(arr1));

        System.out.println();

    }

    /**
     * Brute-force search over swap decisions. The method recursively decides whether items placed at
     * the current suffix position should stay or be swapped across the two arrays.
     */
    private int balanceArray(int[] a, int[] b, int items, int diff) {
        if (items == 0) {
            int d = calculateDiff(a);
            if (d < diff) {
                outputBest(d, a, b);
                diff= d;
            }
        } else {
            for (int i = 0; i < items; i++) {
                swap(a, items - 1, i);
                for (int j = 0; j < items; j++) {
                    swap(b, items - 1, j);

                    diff = balanceArray(a, b, items - 1, diff);
                    if (diff <= 1) break;
                    int temp  = a[items - 1];
                    a[items - 1] = b[items - 1];
                    b[items - 1] = temp;

                    diff = balanceArray(a, b, items - 1, diff);
                    if (diff <= 1) break;
                    b[items - 1] = a[items - 1];
                    a[items - 1] = temp;
                    swap(b, items - 1, j);
                }
                if (diff <= 1) break;
                swap(a, items - 1, i);
            }
        }
        return diff;
    }

    /**
     * Pseudo-polynomial DP alternative to the exponential backtracking above.
     * Splits the 2n combined values into two groups of exactly n, minimizing |sumA - sumB|,
     * and RECONSTRUCTS the actual split by backtracking through the table.
     * R[i][c][s] = using the first i items, can we pick exactly c of them summing to s (offset-encoded)?
     * Time O(n^2 * S), Space O(n^2 * S), where S = sum of |value| over all elements.
     */
    public int minDiffDp(int[] a, int[] b) {
        int m = a.length + b.length;            // total items = 2n
        int n = a.length;                       // group A keeps exactly n items
        int[] nums = new int[m];
        System.arraycopy(a, 0, nums, 0, a.length);
        System.arraycopy(b, 0, nums, a.length, b.length);

        int total = 0, offset = 0;
        for (int x : nums) { total += x; offset += Math.abs(x); }
        int size = 2 * offset + 1;              // subset sums range over [-offset, offset]

        boolean[][][] R = new boolean[m + 1][n + 1][size];
        R[0][0][offset] = true;                 // 0 items, 0 chosen, sum 0 (encoded at index offset)
        for (int i = 1; i <= m; i++) {
            int x = nums[i - 1];
            for (int c = 0; c <= n; c++) {
                for (int s = 0; s < size; s++) {
                    if (R[i - 1][c][s]) {
                        R[i][c][s] = true;                        // skip item i (goes to group B)
                    } else if (c >= 1) {
                        int ps = s - x;
                        if (ps >= 0 && ps < size && R[i - 1][c - 1][ps]) {
                            R[i][c][s] = true;                    // take item i into group A
                        }
                    }
                }
            }
        }

        int best = Integer.MAX_VALUE, bestIdx = -1;
        for (int idx = 0; idx < size; idx++) {
            if (R[m][n][idx]) {
                int d = Math.abs(2 * (idx - offset) - total);
                if (d < best) { best = d; bestIdx = idx; }
            }
        }

        // backtrack from (m, n, bestIdx): prefer "taken into A" whenever that sub-state was reachable
        List<Integer> groupA = new ArrayList<>(), groupB = new ArrayList<>();
        int sumA = 0, sumB = 0, c = n, s = bestIdx;
        for (int i = m; i >= 1; i--) {
            int x = nums[i - 1], ps = s - x;
            if (c >= 1 && ps >= 0 && ps < size && R[i - 1][c - 1][ps]) {
                groupA.add(x); sumA += x; c--; s = ps;            // item i was taken into A
            } else {
                groupB.add(x); sumB += x;                         // item i stays in B
            }
        }
        System.out.println("DP split -> A" + groupA + " (sum " + sumA + "), B" + groupB + " (sum " + sumB + ")");
        return best;
    }

    /**
     * Swap two elements inside one array.
     */
    private void swap(int[] a, int i, int i1) {
        int temp  = a[i];
        a[i] = a[i1];
        a[i1]  =temp;
    }


    /**
     * Given one side of the partition, compute |sumA - sumB| using the precomputed total sum.
     */
    private int calculateDiff(int[] arr1) {
        int sum1 = Arrays.stream(arr1).sum();
        return Math.abs((sum1 << 1) - sum);
    }

    /**
     * Print one best split found by the brute-force search.
     */
    private void outputBest(int diff, int[] a, int[] b) {
        System.out.println();
        System.out.println("diff: " + diff);
        System.out.print("A: ");
        printNumArray(a);
        System.out.print("B: ");
        printNumArray(b);
    }

    /**
     * Utility printer for integer arrays.
     */
    public void printNumArray(int[] array) {
        if (array == null || array.length == 0) {
            System.out.println("input array is empty!");
        }
        for (int item: array) {
            System.out.print(item + " ");
        }
        System.out.println();
    }
}
