package puzzle.dp;
import puzzle.Puzzle;

/**
 * Longest common contiguous substring of two strings.
 * LeetCode: Longest Common Substring
 * Approach: 1D DP updated right-to-left storing the common-suffix length; resets to 0 on mismatch.
 * Complexity: Time O(mn), Space O(n).
 * Created by qingjuntian on 6/16/16.
 */
public class LongestSubString implements Puzzle {

    @Override
    public void resolve() {
        String a = "cbeadsh";
        String b = "abcbfadshsd";

        System.out.println(findLongestSubString(b, a));
    }

    private String findLongestSubString(String a, String b) {
        if (a == null || b == null || a.length() == 0 || b.length() == 0) return "";


        int c[] = new int[b.length() + 1];

        int max = 0;
        int end = 0;
        for (int i = 1; i < a.length() + 1; i++) {
            for (int j = b.length(); j >= 1; j--) {
                if (a.charAt(i - 1) == b.charAt(j - 1)) {
                    c[j] = c[j - 1] + 1;
                } else {
                    c[j] = 0;
                }

                if (c[j] > max) {
                    max = c[j];
                    end = i;
                }
                this.printNumArray(c);
            }
        }
        if (max == 0) return "";
        return a.substring(end - max, end);
    }



}
