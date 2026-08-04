package puzzle.arrays;
import puzzle.Puzzle;

import java.util.ArrayList;
import java.util.List;

/**
 * Find all unique triplets that sum to zero.
 * LeetCode: 3Sum
 * Approach: Sort, fix one element, two-pointer scan, and skip duplicates.
 * Complexity: Time O(n^2), Space O(log n).
 */
public class ThreeSumPuzzle implements Puzzle {
    @Override
    public void resolve() {
        int [] arr = new int[]{11,-8,9,-6,-10,14,-5,-10,2,-1,-14,-13,-5,9,-5,-12,9,5,-1,-4,-14,5,-11,3,6,-7,2,-14,9,-6,-8,-2,-7,8,7,-2,7,9,3,-14,-14,5,-12,-4,-9,-1,-8,7,11,-2,-11,4,-11,-15,-7,10,-7,10,4,10,11,11,-7,-11,4,7,2,-12,1,12,-10,2,2,-15,6,1,-1,13,-7,-12,-4,-11,7,0,-11,-15,-12,-10,2,7,-15,-2,3,-15,-6,14,-1,11,-13,-15,9,14,-5,-12,-15,-14,4,-9,6,5,-6,-13,9};
        List<List<Integer>> ret = threeSum(arr);
        System.out.println("triplets: " + ret.size());
        System.out.println(ret);
    }

    public List<List<Integer>> threeSum(int[] nums) {
        List<List<Integer>> ret = new ArrayList<List<Integer>>();

        if (nums == null)
            return ret;
        int len = nums.length;
        if (len < 3)
            return ret;
        qSort(nums, 0, len - 1);
        for (int i = 0; i < len - 1 && nums[i] <=0; ) {
            int v = -nums[i];
            int k = i + 1, j = len - 1;
            while (k < j) {
                if (nums[k] + nums[j] == v) {
                    List<Integer> l = new ArrayList();
                    l.add(nums[i]);l.add(nums[k]);l.add(nums[j]);
                    ret.add(l);
                    int kv = nums[k];
                    while (kv == nums[k] && k < j) {
                        k++;
                    }
                } else if (nums[k] + nums[j] < v) {
                    int kv = nums[k];
                    while (kv == nums[k] && k < j) {
                        k++;
                    }
                } else {
                    int jv = nums[j];
                    while (jv == nums[j] && j > k) {
                        j--;
                    }
                }
            }
            int iv = nums[i];
            while (iv == nums[i] && i < len - 1) {
                i++;
            }
        }

        return ret;
    }

    public void qSort(int[] array, int l, int h) {
        if (l >= h)
            return;
        int i = l, j = h;

        int flag = array[l];

        while (i < j) {
            while (i < j && array[j] > flag) {
                j--;
            }
            if (i < j) {
                array[i] = array[j];
                i++;
            }
            while (i < j && array[i] < flag) {
                i++;
            }
            if (i < j) {
                array[j] = array[i];
                j--;
            }
        }
        array[i] = flag;

        qSort(array, l, i - 1);
        qSort(array, i + 1, h);

    }

}
