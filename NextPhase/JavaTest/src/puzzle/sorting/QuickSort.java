package puzzle.sorting;
import puzzle.Puzzle;

/**
 * Sort an integer array in place.
 * Approach: Two-pointer partition around the leftmost pivot, then recurse on the subranges.
 * Complexity: Time O(n log n) avg / O(n^2) worst, Space O(log n).
 * Created by qingjuntian on 6/4/16.
 */
public class QuickSort implements Puzzle {

    @Override
    public void resolve() {
        int[] list = new int[]{1, 3, 4, 2, 15, 4, 2, 7, 9, 8, 14, 10};

        qsort(list, 0, list.length - 1);
        printNumArray(list);
    }

    public static  void qsort(int[] list, int l, int h) {
        if (list == null || list.length == 0) {
            return;
        }

        if (h <= l) {
            return;
        }

        int flag = list[l];
        int left = l, right = h;
        while (l < h) {
            while (list[h] > flag && h > l) {
                h--;
            }
            if (l < h) {
                list[l++] = list[h];
            }

            while (list[l] < flag && h > l) {
                l++;
            }
            if (l < h) {
                list[h--] = list[l];
            }
        }
        list[l] = flag;
        qsort(list, left, l - 1);
        qsort(list, l + 1, right);
    }
}
