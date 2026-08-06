package puzzle.arrays;
import puzzle.Puzzle;

import java.util.*;

/**
 * Count distinct pairs with absolute difference k, using frequency information.
 * LeetCode: K-diff Pairs in an Array
 * Approach: Frequency map + set; k==0 needs a count >= 2, k>0 needs value+k to exist.
 * Complexity: Time O(n), Space O(n).
 */
public class KDiffPair2Puzzle implements Puzzle {
    /**
     * Print the number of distinct pairs found in the sample input.
     */
    @Override
    public void resolve() {
        int[] arr = new int[]{3, 1, 4, 1, 5, 6, 6};
        int k = 0;
        System.out.println(kDiffPair(arr, k).size());

    }

    /**
     * Simple value-pair holder for demo output.
     */
    static class Pair {
        final int m;
        final int n;

        Pair(int a, int b) {
            m = a;
            n = b;
        }
    }

    /**
     * Frequency-map solution. For k==0, keep values whose count is at least 2; for k>0, keep each
     * distinct x such that x+k also exists in the map.
     */
    private List<Pair> kDiffPair(int[] arr, int k) {
        List<Pair> ret = new LinkedList<>();
        if (arr == null || arr.length < 2) {
            return ret;
        }
        Map<Integer, Integer> countMap = new HashMap<>();
        Set<Integer> distinct = new HashSet<>();
        for (int n : arr) {
            distinct.add(n);
            if (countMap.containsKey(n)) {
                countMap.put(n, countMap.get(n) + 1);
            } else {
                countMap.put(n, 1);
            }
        }

        for (int n : distinct) {
            if (k == 0) {
                if (countMap.get(n) > 1) {
                    ret.add(new Pair(n, n));
                }
            } else {
                if (countMap.containsKey(n + k)) {
                    ret.add(new Pair(n, n + k));
                }
            }
        }
        return ret;
    }
}
