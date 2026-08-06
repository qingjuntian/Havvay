package puzzle.arrays;
import puzzle.Puzzle;


import java.util.Arrays;

/**
 * Find the triplet whose sum is closest to a target.
 * LeetCode: 3Sum Closest
 * Approach: Sort, then fix one index and move two pointers on the suffix. Every probe can improve
 * the best answer, so the closest sum is updated on every step, not just on exact hits.
 * Complexity: Time O(n^2), Space O(1).
 */
public class ThreeSumClosest implements Puzzle {

    /**
     * Print the closest triplet sum for a small sample input.
     */
    @Override
    public void resolve() {
        System.out.println(threeSumClosest(new int[] {1, 20, 30, 60, 100}, 150));
    }

    /**
     * Return the triplet sum whose distance to {@code target} is minimal.
     */
    public int threeSumClosest(int[] nums, int target) {
        if (nums == null || nums.length < 3) {
            throw new IllegalArgumentException("Need at least three numbers.");
        }

        Arrays.sort(nums);
        int closest = nums[0] + nums[1] + nums[2];   // seed with a real triplet sum (assumes n >= 3);
                                                     // avoids the Integer.MAX_VALUE sentinel, whose
                                                     // Math.abs(MAX_VALUE - target) overflows for target < 0.

        for (int i = 0; i < nums.length; i++) {
            int j = i + 1;
            int k = nums.length - 1;

            while (j < k) {
                int sum = nums[i] + nums[j] + nums[k];
                if (target == sum) {
                    return target;
                } else if (sum < target) {
                    j++;
                } else {
                    k--;
                }
                if (Math.abs(sum - target) < Math.abs(closest - target)) {
                    closest = sum;
                }
            }
        }
        return closest;
    }
}
