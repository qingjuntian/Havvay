package puzzle.arrays;
import puzzle.Puzzle;

/**
 * Maximum water container area (active path); also includes a two-sum pair helper.
 * LeetCode: Container With Most Water / Two Sum
 * Approach: Two pointers; move the shorter wall inward.
 * Complexity: Time O(n), Space O(1).
 * Created by qingjuntian on 7/19/16.
 */
public class Sum2Puzzle implements Puzzle {
    @Override
    public void resolve() {
//        int[] array = new int[] {2, 5, 1, 3, -10, 7, 8, 11, 0, 9, -1, 4, 6};
//
//        int n = 8;
//
//        findSum(array, n);

        int[] array = new int[] {3, 5, 1, 3, 4, 7, 8, 11};
        findMaxBucket(array);
    }

    /**
     * Two-sum via two pointers. PRECONDITION: array must be SORTED ascending; the two-pointer
     * shrink logic is invalid on unsorted input (note the commented demo array above is NOT sorted).
     */
    private void findSum(int[] array, int n) {
        if (array == null || array.length == 0) return;
        int i = 0, j = array.length - 1;
        while (i < j) {
            if (array[i] + array[j] > n) {
                j--;
            } else if (array[i] + array[j] < n) {
                i++;
            } else {
                System.out.println(array[i] + "\t" + array[j]);
                i++;
                j--;
            }
        }
    }

    private void findMaxBucket(int[] array) {
        if (array == null || array.length == 0) return;
        int i = 0, j = array.length - 1;
        int volume = Integer.MIN_VALUE;
        while (i < j) {
            int width = j - i;
            int height = Math.min(array[i], array[j]);
            if (width * height > volume) {
                volume = width * height;
            }
            if (array[i] < array[j]) {
                i++;
            } else {
                j--;
            }
        }
        System.out.println("max volume is " + volume);
    }

}
