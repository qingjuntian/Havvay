package puzzle.strings;
import puzzle.Puzzle;

/**
 * Longest substring containing at most two distinct characters.
 * LeetCode: Longest Substring with At Most Two Distinct Characters
 * Approach: Single-pass sliding window tracking the two active chars and the last run length.
 * Complexity: Time O(n), Space O(1).
 */
public class LongestDistSubString implements Puzzle {
    /**
     * Print the longest sample substring containing at most two distinct characters.
     */
    @Override
    public void resolve() {
        String testString = "aabbbccc";

        System.out.println(findLongest(testString));
    }

    /**
     * Return the longest substring containing at most two distinct characters.
     * The method tracks the two active characters plus the length of the most recent run so the
     * left boundary can be reset correctly when a third character appears.
     */
    private String findLongest(String str) {
        if (str == null) {
            return null;
        }
        if (str.length() <= 2) {
            return str;
        }

        char[] chars = str.toCharArray();

        int l = 0, r = 0, s = 0;
        char c1 = chars[0];
        char c2 = c1;
        int i = 1;
        int temp = 1;
        for (; i < chars.length; i++) {
            char ch = chars[i];
            if (ch == c2) {
                temp ++;
            } else {
                if (ch == c1) {
                    c1 = c2;
                    c2 = ch;
                } else if (c1==c2) {
                    c2 = ch;
                } else {
                    if (i - s > r - l) {
                        l = s;
                        r = i;
                    }
                    c1 = c2;
                    c2 = ch;
                    s = i - temp;
                }
                temp = 1;
            }
        }
        if (i - s > r - l) {
            l = s;
            r = i;
        }
        return str.substring(l, r);
    }
}
