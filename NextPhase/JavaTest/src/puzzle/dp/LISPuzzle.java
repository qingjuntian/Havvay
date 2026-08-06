package puzzle.dp;
import puzzle.Puzzle;

/**
 * Length of the longest strictly increasing subsequence.
 * LeetCode: Longest Increasing Subsequence
 * Approach: Patience sorting: maintain a tails array and binary-search each value (O(n log n)); an O(n^2) DP variant is also included.
 * Complexity: Time O(n log n), Space O(n).
 * Created by qingjuntian on 12/9/16.
 */
public class LISPuzzle implements Puzzle {
    @Override
    public void resolve() {
        int[] arr = new int[]{10, 9, 2, 5, 3, 4, 7, 4, 101, 18};

        System.out.println(lis3(arr));

    }

    /**
     * Classic O(n^2) DP: lisArr[i] = length of the LIS ending exactly at i.
     */
    private int lis(int[] arr) {
        if (arr == null || arr.length == 0) return 0;
        int[] lisArr = new int[arr.length];
        for (int i = 0; i < arr.length; i++) {
            lisArr[i] = 1;
        }
        int max = 1;
        for (int i = 1; i < arr.length; i++) {
            for (int j = 0; j < i; j++) {
                if (arr[j] < arr[i] && lisArr[i] < lisArr[j] + 1) {
                    lisArr[i] = lisArr[j] + 1;
                    if (lisArr[i] > max) {
                        max = lisArr[i];
                    }
                }
            }
        }
        return max;
    }

    /**
     * Older O(n log n) tails-array attempt kept for study. The cleaner, preferred version in this
     * file is {@link #lis3(int[])}.
     */
    private int lis2(int[] arr) {
        if (arr == null || arr.length == 0) return 0;
        int[] lisArr = new int[arr.length];
        for (int i = 0; i < arr.length; i++) {
            lisArr[i] = Integer.MAX_VALUE;
        }
        int max = 0;
        for (int i = 0; i < arr.length; i++) {
            int l = 0, h = max;
            while (l <= h) {
                int mid = l + (h - l) / 2;
                if (arr[i] > lisArr[mid]) {
                    l = mid + 1;
                } else if (arr[i] < lisArr[mid]) {
                    h = mid -1;
                }
            }
            if (arr[i] < lisArr[l]) {
                lisArr[l] = arr[i];
            }

            if (max < l + 1) {
                max = l + 1;
            }
        }
        return max;
    }
    
    /**
     * Preferred O(n log n) patience-sorting / tails solution. lis[i] stores the minimum possible
     * tail value of any increasing subsequence of length i+1 seen so far.
     */
    public int lis3(int[] arr) {
        int max = 0;
        int[] lis = new int[arr.length];
        for (int i = 0; i < arr.length; i++) lis[i] = Integer.MAX_VALUE;

        for (int i = 0; i < arr.length; i++) {
            int l = 0, h = max;
            while (l <= h) {
                int m = l + (h - l) / 2;
                if (arr[i] > lis[m]) {
                    l = m + 1;
                } else {
                    h = m - 1;
                }
            }

            if (arr[i] < lis[l]) lis[l] = arr[i];
            if (max < l + 1) max = l + 1;
        }


        return max;
    }


}
