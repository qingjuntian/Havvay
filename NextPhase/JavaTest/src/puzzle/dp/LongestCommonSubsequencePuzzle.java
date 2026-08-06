package puzzle.dp;
import puzzle.Puzzle;

/**
 * Length of the longest common subsequence of two strings: Longest Common Subsequence of two strings — the longest sequence of characters appearing in both, in the same relative order but not necessarily contiguous.
 * LeetCode: Longest Common Subsequence
 * Approach: 2D DP: a match extends the diagonal, otherwise take max(top, left).
 * Complexity: Time O(mn), Space O(mn).
 */
public class LongestCommonSubsequencePuzzle implements Puzzle {

    /**
     * Compare two sample strings and print the LCS length.
     */
    @Override
    public void resolve() {
        String a = "cbeadsh";
        String b = "abcbfadshsd";

        System.out.println(findLongestCommonSubsequence(a, b));
    }

    /**
     * Standard 2D LCS DP. c[i][j] stores the LCS length for prefixes a[0..i) and b[0..j).
     */
    private int findLongestCommonSubsequence(String a, String b) {
        if (a == null || b == null || a.length() == 0 || b.length() == 0) {
            return 0;
        }

        int[][] dp = new int[a.length() + 1][b.length() + 1];
        for (int i = 1; i <= a.length(); i++) {
            for (int j = 1; j <= b.length(); j++) {
                if (a.charAt(i - 1) == b.charAt(j - 1)) {
                    dp[i][j] = dp[i - 1][j - 1] + 1;
                } else {
                    dp[i][j] = Math.max(dp[i - 1][j], dp[i][j - 1]);
                }
            }
        }
        return dp[a.length()][b.length()];
    }
}
