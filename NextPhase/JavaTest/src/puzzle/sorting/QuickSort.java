package puzzle.sorting;
import puzzle.Puzzle;

/**
 * Sort an integer array in place.
 * Approach: Two-pointer partition around the leftmost pivot, then recurse on the subranges.
 * Complexity: Time O(n log n) avg / O(n^2) worst, Space O(log n).
 */
public class QuickSort implements Puzzle {

    /**
     * Run quicksort on a small unsorted sample and print the sorted result.
     */
    @Override
    public void resolve() {
        int[] list = new int[]{1, 3, 4, 2, 15, 4, 2, 7, 9, 8, 14, 10};

        qsort(list, 0, list.length - 1);
        printNumArray(list);
    }

    /**
     * In-place quicksort using the leftmost element as the pivot and the classic two-pointer
     * "digging hole" partition style on the inclusive range [l, h].
     */
    public static void qsort(int[] list, int l, int h) {
        if (list == null || list.length == 0) {
            return;
        }

        if (h <= l) {
            return;
        }

        int pivot = list[l];
        int left = l, right = h;
        while (l < h) {
            while (list[h] > pivot && h > l) {
                h--;
            }
            if (l < h) {
                list[l++] = list[h];
            }

            while (list[l] < pivot && h > l) {
                l++;
            }
            if (l < h) {
                list[h--] = list[l];
            }
        }
        list[l] = pivot;
        qsort(list, left, l - 1);
        qsort(list, l + 1, right);
    }
}
