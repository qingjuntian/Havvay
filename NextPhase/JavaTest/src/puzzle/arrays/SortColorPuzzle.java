package puzzle.arrays;
import puzzle.Puzzle;

/**
 * Sort an array containing only the values 0, 1, and 2, in place.
 * LeetCode: Sort Colors
 * Approach: Dutch national flag partition with three pointers.
 * Complexity: Time O(n), Space O(1).
 * Created by qingjuntian on 7/29/16.
 */
public class SortColorPuzzle implements Puzzle {


    @Override
    public void resolve() {
        int[] colors = new int[]{2, 0, 1, 1, 0, 2, 0, 1, 2};

        sortColors(colors);
        this.printNumArray(colors);
        return;
    }

    /**
     * One-pass Dutch national flag partition. The interval [0, zero) holds 0s, [zero, cur) holds
     * 1s, and (second, end] holds 2s. When swapping a 2 to the right, cur is not advanced because
     * the incoming value at cur has not yet been examined.
     */
    public void sortColors(int[] nums) {
        if (nums == null || nums.length <= 1) return;
        int zero = 0, second = nums.length - 1;
        int cur = 0;
        while(cur <= second) {
            if(nums[cur] == 0) {
                swap(nums, cur++, zero++);
            } else if(nums[cur] == 1) {
                cur++;
            } else if(nums[cur] == 2) {
                swap(nums, cur, second--);
            }
        }

    }

    /**
     * Swap two array positions in-place.
     */
    public void swap(int[] arr, int p0, int p1) {
        int temp = arr[p0];
        arr[p0] = arr[p1];
        arr[p1] = temp;


    }
}
