package puzzle.dp;
import puzzle.Puzzle;

/**
 * Length of the longest common subsequence of two strings: Longest Common Subsequence of two strings — the longest sequence of characters appearing in both, in the same relative order but not necessarily contiguous.
 * LeetCode: Longest Common Subsequence
 * Approach: 2D DP: a match extends the diagonal, otherwise take max(top, left).
 * Complexity: Time O(mn), Space O(mn).
 * NOTE: This is a subsequence (not a substring), despite the class name.
 * Created by qingjuntian on 6/16/16.
 */
public class LongestSubSequence implements Puzzle {

    @Override
    public void resolve() {
        String a = "cbeadsh";
        String b = "abcbfadshsd";

        System.out.println(findLongestSubSequence(a, b));
    }

    private int findLongestSubSequence(String a, String b) {
        if (a == null || b == null || a.length() == 0 || b.length() == 0) return 0;


        int c[][] = new int[a.length() + 1][b.length() + 1];

        int max = 0;

        for (int i = 1; i <= a.length(); i++) {
            for (int j = 1; j <= b.length(); j++) {
                if (a.charAt(i - 1) == b.charAt(j - 1)) {
                    c[i][j] = c[i - 1][j - 1] + 1;
                } else {
                    c[i][j] = Math.max(c[i-1][j], c[i][j-1]);
                }
                if (c[i][j] > max) {
                    max = c[i][j];
                }
            }
        }
        for (int i = 0; i < c.length; i++) {
            for (int j = 0; j <= b.length(); j++) {
                System.out.print(c[i][j] + "\t");
            }
            System.out.println();
        }

        return max;
    }



}
