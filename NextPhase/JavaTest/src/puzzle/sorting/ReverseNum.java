package puzzle.sorting;
import puzzle.Puzzle;

/**
 * Count the number of inversions (out-of-order pairs) in an array.
 * LeetCode: Reverse Pairs / Count Inversions
 * Approach: Merge sort; count (mid-i+1) inversions whenever a right element precedes remaining left elements.
 * Complexity: Time O(n log n), Space O(n).
 * NOTE: Name is misleading -- this counts inversions, it does not reverse an integer.
 * Created by qingjuntian on 7/3/16.
 */
public class ReverseNum implements Puzzle {

    private int[] temp;

    @Override
    public void resolve() {
        int[] array = {13, 7, 3, 2, 5, 8, 10, 9, 4};

        int reverseNumber = reverseNum(array, 0, array.length - 1);

        System.out.println("reverse number is: " + reverseNumber);
//        puzzle.LongestSubString.PuzzleUtil.printNumArray(array);
    }

    private int reverseNum(int[] array, int low, int high) {
        if (array == null || array.length == 0) return 0;
        if (temp == null) {
            temp  = new int[array.length];
        }
        if (low >= high) return 0;
        int mid = low  + (high - low) / 2;

        int left = reverseNum(array, low, mid);
        int right = reverseNum(array, mid + 1, high);

        int i = low, j = mid + 1, cur = low;
        int number = 0;
        while (i <= mid && j <= high) {
            if (array[i] <= array[j]) {
                temp[cur++] = array[i++];
            } else {
                number += mid - i + 1;
                temp[cur++] = array[j++];
            }
        }

        while (i <= mid) {
            temp[cur++] = array[i++];
        }

        while (j <= high) {
            temp[cur++] = array[j++];
        }

        for (int k = low; k <= high; k++) {
            array[k] = temp[k];
        }

        printNumArray(array);
        return number + left + right;
    }

}
