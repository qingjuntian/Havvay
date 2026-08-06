package puzzle.arrays;
import puzzle.Puzzle;

import java.util.Arrays;

/**
 * Check whether the array's sum is divisible by its length.
 * The file is intentionally tiny and mainly serves as a simple arithmetic utility example.
 * Complexity: Time O(n), Space O(1).
 */
public class SumDivisibleByLengthPuzzle implements Puzzle {

    /**
     * Run the divisibility check on a sample array.
     */
    @Override
    public void resolve() {
        int[] arr = new int[]{2, -1, 1, 2, 2};
        System.out.println(isSumDivisibleByLength(arr));
    }

    /**
     * Return true iff the array sum is divisible by the array length.
     */
    private boolean isSumDivisibleByLength(int[] arr) {
        if (arr == null || arr.length < 2) {
            return false;
        }
        int sum = Arrays.stream(arr).sum();
        return (sum % arr.length) == 0;
    }
}
