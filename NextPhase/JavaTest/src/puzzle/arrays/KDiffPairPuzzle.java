package puzzle.arrays;
import puzzle.Puzzle;

import java.util.Arrays;
import java.util.LinkedList;
import java.util.List;

/**
 * Find distinct pairs whose values differ by k.
 * LeetCode: K-diff Pairs in an Array
 * Approach: Sort, then for each distinct value binary-search value+k in the suffix; normalizes k=abs(k).
 * Complexity: Time O(n log n), Space O(1).
 * Created by qingjuntian on 12/9/16.
 */
public class KDiffPairPuzzle implements Puzzle {
    public void resolve() {
        int[] arr = new int[]{3, 1, 4, 1, 5};
        int k = 2;
        System.out.println(kDiffPair(arr, k));

    }

    class Pair {
        int m, n;
        Pair(int a, int b) {
            this.m = a;
            this.n = b;
        }
    }
    private List<Pair> kDiffPair(int[] arr, int k) {
        List<Pair> ret = new LinkedList();
        Arrays.sort(arr);

        if (k < 0) k = -k;
        for (int i = 0; i < arr.length; ) {
            int cur = arr[i];
            int sum = cur + k;
            if (bSearch(arr, i + 1, arr.length - 1, sum)) {
                ret.add(new Pair(cur, sum));
            }
            while (i < arr.length && arr[i] == cur) i++;
        }
        return ret;
    }

    private boolean bSearch(int[] arr, int l, int h, int sum) {
        while (l <= h) {
            int m = l + (h - l) / 2;
            if (arr[m] == sum) return true;
            if (arr[m] < sum) {
                l= m + 1;
            } else {
                h = m - 1;
            }
        }
        return false;
    }

}
