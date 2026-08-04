package puzzle.arrays;
import puzzle.Puzzle;

/**
 * Rearrange numbers into the next lexicographically greater permutation, in place.
 * LeetCode: Next Permutation
 * Approach: Find the pivot from the right, swap with the next larger suffix element, then reverse the suffix.
 * Complexity: Time O(n), Space O(1).
 * Created by qingjuntian on 6/16/16.
 */
public class NextPermutation implements Puzzle {

    @Override
    public void resolve() {

        int[] nums = new int[]{3,1,4,6,5,2};
        nextPermutation(nums);
        printNumArray(nums);
    }

    public void nextPermutation(int[] nums) {

        int i = nums.length - 1;
        int last = nums[i];
        for (; i >=0; i--) {
            if (nums[i] < last) {
                break;
            } else {
                last = nums[i];
            }
        }
        if (i >= 0) {
            for (int n = nums.length - 1; n > i; n--) {
                if (nums[n] > nums[i]) {
                    int t = nums[i];
                    nums[i] = nums[n];
                    nums[n] = t;
                    break;
                }
            }
        }

        i++;
        int j = nums.length - 1;
        while (i < j) {
            int t = nums[i];
            nums[i] = nums[j];
            nums[j] = t;
            i++;
            j--;
        }

    }



}
