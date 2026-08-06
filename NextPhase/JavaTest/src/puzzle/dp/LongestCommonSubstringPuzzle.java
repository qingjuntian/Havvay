package puzzle.dp;
import puzzle.Puzzle;

/**
 * Longest common contiguous substring of two strings.
 * LeetCode: Longest Common Substring
 * Approach: 1D DP updated right-to-left storing the common-suffix length; resets to 0 on mismatch.
 * Complexity: Time O(mn), Space O(n).
 */
public class LongestCommonSubstringPuzzle implements Puzzle {

    /**
     * Compare two sample strings and print their longest common contiguous substring.
     */
    @Override
    public void resolve() {
        String a = "cbeadsh";
        String b = "abcbfadshsd";

        System.out.println(findLongestCommonSubstring(b, a));
    }

    /**
     * 1D rolling-DP for longest common substring. c[j] stores the length of the common suffix ending
     * at the current character of a and b[j-1], so j must be updated right-to-left.
     */
    private String findLongestCommonSubstring(String a, String b) {
        if (a == null || b == null || a.length() == 0 || b.length() == 0) {
            return "";
        }

        int[] dp = new int[b.length() + 1];
        int max = 0;
        int end = 0;
        for (int i = 1; i < a.length() + 1; i++) {
            for (int j = b.length(); j >= 1; j--) {
                if (a.charAt(i - 1) == b.charAt(j - 1)) {
                    dp[j] = dp[j - 1] + 1;
                } else {
                    dp[j] = 0;
                }

                if (dp[j] > max) {
                    max = dp[j];
                    end = i;
                }
            }
        }
        if (max == 0) {
            return "";
        }
        return a.substring(end - max, end);
    }
}
