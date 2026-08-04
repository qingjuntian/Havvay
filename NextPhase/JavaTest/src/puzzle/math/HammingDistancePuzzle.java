package puzzle.math;
import puzzle.Puzzle;

/**
 * Sum of the Hamming distances between every pair of integers in an array.
 * LeetCode: Total Hamming Distance
 * Approach: For each bit position, contribute ones*zeros instead of comparing pairs directly.
 * Complexity: Time O(31n), Space O(1).
 * Created by qingjuntian on 1/14/17.
 */
public class HammingDistancePuzzle implements Puzzle {
    @Override
    public void resolve() {
        int[] nums = {4, 14, 2};
        System.out.println(totalHammingDistance(nums));
    }

    public int totalHammingDistance(int[] nums) {
        int[][] dp = new int[31][2];
        int res = 0;
        for (int x : nums)
            for (int i=0; i<31; ++i) {
                ++dp[i][(x>>i)&1];
                res += dp[i][((x>>i)&1)^1];
            }
        return res;
    }
}
