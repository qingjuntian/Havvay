package puzzle.arrays;
import puzzle.Puzzle;

import java.util.ArrayList;
import java.util.HashSet;
import java.util.List;
import java.util.Set;

/**
 * Minimum patches to add so every value in [1, n] is formable as a subset sum of the array.
 * LeetCode: Patching Array
 * Approach: Greedy (composePatch2) on a SORTED array: keep `upper` = smallest sum not yet formable;
 *   if the next number <= upper extend coverage, else patch with `upper` itself and double the reach.
 * Complexity: Time O(n + log number), Space O(1). (composePatch1 is a buggy non-optimal alternate.)
 * Created by qingjuntian on 6/26/16.
 */
public class ArrayPatchPuzzle implements Puzzle {

    @Override
    public void resolve() {
        List<Integer> patches = composePatch2(new int[]{4}, 50);
        for (int i : patches) {
            System.out.print(i + " ");
        }

    }

    /**
     * Greedy solution. Maintain {@code upper} = the smallest sum not yet formable, so the current
     * covered interval is exactly [1, upper-1]. If the next input value is <= upper, coverage
     * extends without gaps; otherwise, patch with upper itself, which doubles the reach.
     */
    private List<Integer> composePatch2(int[] ints, int number) {

        List<Integer> patches = new ArrayList<>();

        int idx = 0;
        long upper = 1;                     // long: upper can exceed Integer.MAX_VALUE via doubling
        while (upper <= number) {           // <= : the range [1, number] must include number itself
            if (idx < ints.length && ints[idx] <= upper) {
                upper += ints[idx++];
            } else {
                patches.add((int) upper);   // the patched value equals upper (<= number), fits in int
                upper += upper;
            }
        }
        return patches;



    }

    /**
     * NOTE (buggy / non-optimal): an alternate subset-sum attempt that patches i in [1,n] when it
     * cannot be formed. It tracks only ONE index-decomposition per sum, so it under-explores subsets
     * and sometimes marks a formable value as unformable -> it adds MORE patches than optimal
     * (e.g. ints={3,10,12}, n=33 yields 4 patches vs the optimal 3). NOT called by resolve(); the
     * correct O(n) greedy is composePatch2. Kept only as a study artifact.
     */
    private List<Integer> composePatch1(int[] ints, int number) {
        List<Integer> patches = new ArrayList<>();

        for (int item : ints) {
            patches.add(item);
        }


        Set<Integer>[] sums = new HashSet[number + 1];

        for (int i = 1; i < number + 1; i++) {
            sums[i] = new HashSet<>();
            if (patches.contains(i)) {
                sums[i].add(patches.indexOf(i));
                continue;
            }
            boolean ok = false;
            for (int j=0; j < patches.size(); j++) {
                if (i > patches.get(j) && sums[i - patches.get(j)].contains(j) == false) {
                    sums[i].addAll(sums[i - patches.get(j)]);
                    sums[i].add(j);
                    ok = true;
                    break;
                }
            }
            if (ok ==false) {
                patches.add(i);
                sums[i].add(patches.indexOf(i));
            }
        }
        return patches;
    }
}
