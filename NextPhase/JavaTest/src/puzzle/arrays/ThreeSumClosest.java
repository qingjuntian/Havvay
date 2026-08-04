package puzzle.arrays;
import puzzle.Puzzle;


import java.util.Arrays;

/**
 * Find the triplet whose sum is closest to a target.
 * LeetCode: 3Sum Closest
 * Approach: Sort, then a fixed index + two pointers, tracking the closest sum on every step.
 * Complexity: Time O(n^2), Space O(1).
 * Created by qingjuntian on 7/26/16.
 */
public class ThreeSumClosest implements Puzzle {

    @Override
    public void resolve() {
        System.out.println(threeSumClosest(new int[] {1,20,30,60,100}, 150));
    }

    public int threeSumClosest(int[] nums, int target) {

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
