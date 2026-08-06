package puzzle.strings;
import puzzle.Puzzle;

import java.util.HashSet;
import java.util.Set;

/**
 * Length of the longest substring without repeating characters.
 * LeetCode: Longest Substring Without Repeating Characters
 * Approach: Backward brute-force scan (not optimal -- a sliding window would be O(n)).
 * Complexity: Time O(n^2), Space O(1).
 */
public class LongestDistSubString2 implements Puzzle {
    /**
     * Print the longest non-repeating substring length for a sample input.
     */
    @Override
    public void resolve() {
        String testString = "acbbd";
        System.out.println(findLongest(testString));
    }

    /**
     * Backward brute-force scan kept for contrast with the optimal sliding-window solution.
     */
    private int findLongest(String str) {
        if (str == null || str.length() == 0) return 0;
        int max = 1;
        char[] chars = str.toCharArray();

        int start = 1;
        for (int i = chars.length - 2; i >= 0; i--) {
            int end = i + start;
            start = 1;
            for (int j = i + 1; j <= end && chars[j] != chars[i]; j++) {
                start++;
            }
            if (start > max) max = start;
        }
        return max;
    }

    /**
     * Utility helper: count how many distinct characters appear in the string.
     */
    int lengthOfUniqChar(String s) {
        Set<Character> seen = new HashSet<>();
        for (int i = 0; i < s.length(); i++) {
            seen.add(s.charAt(i));
        }
        return seen.size();
    }
}
