package puzzle.math;
import puzzle.Puzzle;

/**
 * Add two integers without using the + operator.
 * LeetCode: Sum of Two Integers
 * Approach: Recursive bitwise add: XOR for the sum bits, (AND<<1) for the carry.
 * Complexity: Time O(1), Space O(1).
 * The separate hate49() helper returns the n-th positive integer whose decimal form has no digit 4 or 9.
 * Created by qingjuntian on 6/4/16.
 */
public class SumWithoutPlus implements Puzzle {

    @Override
    public void resolve() {
        System.out.println("sum(15, 11) = " + sum(15, 11));      // add without '+' -> 26
        System.out.println("hate49(600) = " + hate49(600));      // 600th number with no digit 4 or 9 -> 1130
    }

    /**
     * Recursive bitwise addition. XOR computes the sum bits without carry; (AND << 1) computes the
     * carry bits. Recurse until the carry becomes zero.
     */
    private int sum(int a, int b) {
        if (a == 0) return b;
        return sum(((a&b) << 1), a^b);
    }

    /**
     * Return the nth positive integer whose decimal representation contains neither digit 4 nor 9.
     */
    private int hate49(int n) {
        int i = 0;
        int ret = 0;
        while (++i <= n) {
            ret++;
            while (is49(ret)) ret++;
        }
        return ret;
    }

    /**
     * Return true iff the decimal representation contains digit 4 or digit 9.
     */
    private boolean is49(int i) {
        String s = "" + i;
        return s.contains("4") || s.contains("9");
    }


}
