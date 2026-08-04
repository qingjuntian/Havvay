package puzzle.dp;
import puzzle.Puzzle;

/**
 * Maximum-sum contiguous subarray (and its start/end indices).
 * LeetCode: Maximum Subarray
 * Approach: Suffix-DP variant of Kadane's algorithm.
 * Complexity: Time O(n), Space O(n).
 * Created by qingjuntian on 6/29/16.
 */
public class MaxSubArrPuzzle implements Puzzle {
    @Override
    public void resolve() {
        int[] result = maxSubArr(new int[]{10,-7, -4, 8, -7, 5, 0, 8, -9, 4, 4});
        System.out.println(String.format("Max is %d from %d to %d", result[0], result[1], result[2]));
    }

    private int[] maxSubArr(int[] arr) {
        int[][] result = new int[arr.length][];
        for (int i = 0; i < arr.length; i ++ ) {
            result[i] = new int[3];
        }

        result[arr.length - 1][0] = arr[arr.length - 1];
        result[arr.length - 1][1] = arr.length - 1;
        result[arr.length - 1][2] = arr.length - 1;
        int max = arr.length - 1;

        for (int i = arr.length - 2; i>=0; i--) {
            if (arr[i] > result[i + 1][0] + arr[i]) {
                result[i][0] = arr[i];
                result[i][1] = i;
                result[i][2] = i;
            } else {
                result[i][0] = arr[i] + result[i+1][0];
                result[i][1] = i;
                result[i][2] = result[i+1][2];
            }
            if (result[max][0] < result[i][0]) {
                max = i;
            }
        }

        return result[max];
    }

    // O(1) space — standard left-to-right Kadane; also returns [maxSum, start, end].
    private int[] maxSubArr2(int[] arr) {
        if (arr == null || arr.length == 0) return new int[]{0, -1, -1};
        int bestSum = arr[0], bestStart = 0, bestEnd = 0;   // global best so far
        int curSum = arr[0], curStart = 0;                  // best subarray ending at i
        for (int i = 1; i < arr.length; i++) {
            if (curSum < 0) {           // a negative prefix only hurts -> restart at i
                curSum = arr[i];
                curStart = i;
            } else {                    // otherwise extend the current run
                curSum += arr[i];
            }
            if (curSum > bestSum) {     // update the global best (+ its bounds)
                bestSum = curSum;
                bestStart = curStart;
                bestEnd = i;
            }
        }
        return new int[]{bestSum, bestStart, bestEnd};
    }
}
