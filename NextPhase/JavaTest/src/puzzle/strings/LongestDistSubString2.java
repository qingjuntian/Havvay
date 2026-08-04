package puzzle.strings;
import puzzle.Puzzle;

import java.util.HashSet;
import java.util.Set;

/**
 * Length of the longest substring without repeating characters.
 * LeetCode: Longest Substring Without Repeating Characters
 * Approach: Backward brute-force scan (not optimal -- a sliding window would be O(n)).
 * Complexity: Time O(n^2), Space O(1).
 * Created by qingjuntian on 6/6/16.
 */
public class LongestDistSubString2 implements Puzzle {
    @Override
    public void resolve() {
        String testString = "acbbd";
        System.out.println(findLongest(testString));
    }

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

    int lengthOfUniqChar(String s) {
        Set<Character> set = new HashSet<>();
        for(int i = 0; i < s.length(); i++) {
            set.add(s.charAt(i));
        }
        return set.size();
    }
}
