package puzzle.arrays;
import puzzle.Puzzle;

import java.util.Arrays;

/**
 * Check whether the array's sum is divisible by its length.
 * Complexity: Time O(n), Space O(1).
 * NOTE: Trivial; despite the name there is no rotation logic.
 * Created by qingjuntian on 6/7/16.
 */
public class RoundArrayPuzzle implements Puzzle {

    @Override
    public void resolve() {
        int [] arr = new int[]{2, -1, 1, 2, 2};
        System.out.println(isRound(arr));
    }

    private boolean isRound(int[] arr) {
        if (arr == null || arr.length < 2) return false;
        int sum = Arrays.stream(arr).sum();
        if ((sum % arr.length) == 0) return true;

        return false;
    }


}
