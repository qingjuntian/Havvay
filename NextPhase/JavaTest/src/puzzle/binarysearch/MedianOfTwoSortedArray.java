package puzzle.binarysearch;
import puzzle.Puzzle;

import java.io.FileInputStream;
import java.io.FileOutputStream;
import java.nio.ByteBuffer;
import java.nio.channels.FileChannel;

/**
 * Find the median of two sorted arrays.
 * LeetCode: Median of Two Sorted Arrays
 * Approach: Recursive kth-element selection, discarding half of one array each step.
 * Complexity: Time O(log(m+n)), Space O(log(m+n)) recursion.
 */
public class MedianOfTwoSortedArray implements Puzzle {

    @Override
    public void resolve() {
        int[] s1 = {1, 3, 5, 8, 10, 11, 12, 14, 15, 18, 19, 20, 25, 60, 79, 81};
        int[] s2 = {2, 3, 5, 7, 9,  15, 25, 60, 79, 81};
        System.out.println(findMedianSortedArrays(s1, s1.length, s2, s2.length));
    }

    int getkth(int[] s, int sStart, int sNum, int[] l, int lStart, int lNum, int k) {
        // let m <= n
        if (lNum > sNum)
            return getkth(l, lStart, lNum, s, sStart, sNum, k);
        if (sNum == 0)
            return l[lStart + k - 1];
        if (lNum == 0)
            return s[sStart + k - 1];
        if (k == 1)
            return Math.min(s[sStart], l[lStart]);

        int i = Math.min(sNum, k / 2), j = Math.min(lNum, k / 2);
        if (s[sStart + i - 1] > l[lStart + j - 1])
            return getkth(s, sStart, sNum, l, lStart + j, lNum- j, k - j);
        else
            return getkth(s,sStart + i, sNum - i, l, lStart, lNum, k - i);
    }

    double findMedianSortedArrays(int A[], int m, int B[], int n) {
        int l = (m + n + 1) >> 1;
        int r = (m + n + 2) >> 1;
        int left = getkth(A, 0, m ,B, 0, n, l);
        int right = getkth(A, 0, m, B, 0, n, r);
        return (left + right) / 2.0;
    }

}
