package puzzle.sorting;
import puzzle.Puzzle;

/**
 * Count the number of inversions (out-of-order pairs) in an array.
 * LeetCode: Reverse Pairs / Count Inversions
 * Approach: Merge sort; count (mid-i+1) inversions whenever a right element precedes remaining left elements.
 * Complexity: Time O(n log n), Space O(n).
 */
public class InversionCountPuzzle implements Puzzle {

    private int[] temp;

    /**
     * Count inversions in a sample array and print the result.
     */
    @Override
    public void resolve() {
        int[] array = {13, 7, 3, 2, 5, 8, 10, 9, 4};

        int inversionCount = countInversions(array, 0, array.length - 1);

        System.out.println("inversion count is: " + inversionCount);
    }

    /**
     * Merge-sort-based inversion counting. The recursive halves count their own inversions; the
     * merge step adds (mid - i + 1) whenever a right-half value precedes the remaining left-half values.
     */
    private int countInversions(int[] array, int low, int high) {
        if (array == null || array.length == 0) return 0;
        if (temp == null) {
            temp  = new int[array.length];
        }
        if (low >= high) return 0;
        int mid = low  + (high - low) / 2;

        int left = countInversions(array, low, mid);
        int right = countInversions(array, mid + 1, high);

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
