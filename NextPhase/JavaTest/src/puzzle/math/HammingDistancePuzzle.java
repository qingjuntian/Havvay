package puzzle.math;
import puzzle.Puzzle;

/**
 * Sum of the Hamming distances between every pair of integers in an array.
 * LeetCode: Total Hamming Distance
 * Approach: For each bit position, contribute ones*zeros instead of comparing pairs directly.
 * The implementation scans 31 bits, which matches the non-negative 32-bit integer setting of the
 * classic problem.
 * Complexity: Time O(31n), Space O(1).
 */
public class HammingDistancePuzzle implements Puzzle {
    /**
     * Print the total Hamming distance for a small sample array.
     */
    @Override
    public void resolve() {
        int[] nums = {4, 14, 2};
        System.out.println(totalHammingDistance(nums));
    }

    /**
     * Sum the Hamming distance contribution bit-by-bit instead of pair-by-pair. For each bit, every
     * 1 can pair with every 0, so the contribution is ones * zeros.
     */
    public int totalHammingDistance(int[] nums) {
        int[][] dp = new int[31][2];
        int res = 0;
        for (int x : nums) {
            for (int i = 0; i < 31; ++i) {
                ++dp[i][(x >> i) & 1];
                res += dp[i][((x >> i) & 1) ^ 1];
            }
        }
        return res;
    }
}
