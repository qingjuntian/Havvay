package puzzle.dp;
import puzzle.Puzzle;

/**
 * Find the longest palindromic substring.
 * LeetCode: Longest Palindromic Substring
 * Approach: 2D interval DP (plus a center-expansion helper); base cases for length 1 and 2.
 * Complexity: Time O(n^2), Space O(n^2).
 * Created by qingjuntian on 8/4/16.
 */
public class PalindromePuzzle implements Puzzle {

    @Override
    public void resolve() {
        String s = "aabcdceecdcba";

        System.out.println(longestPalindromeDP(s));

    }

    private String longestPalindromeDP(String s) {
        int n = s.length();
        if (n == 0) return "";
        char[] chars = s.toCharArray();
        int longestBegin = 0;
        int maxLen = 1;
        boolean table[][] = new boolean[n][n];
        for (int i = 0; i < n; i++) {
            table[i][i] = true;
        }
        for (int i = 0; i < n-1; i++) {
            if (chars[i] == chars[i+1]) {
                table[i][i+1] = true;
                longestBegin = i;
                maxLen = 2;
            }
        }
        for (int len = 3; len <= n; len++) {
            for (int i = 0; i < n-len+1; i++) {
                int j = i+len-1;
                if (chars[i] == chars[j] && table[i+1][j-1]) {
                    table[i][j] = true;
                    longestBegin = i;
                    maxLen = len;
                }
            }
        }
        return s.substring(longestBegin, maxLen + longestBegin);
    }

    private void longestPalindrome(String s) {
        if (s == null || s.length() == 0) return;

        char[] chars = s.toCharArray();
        int start = 0, end = 0;
        for (int i = 0; i < chars.length; i++) {
            int[] lTemp = palindrome(chars, i);
            if (lTemp != null && (lTemp[1] - lTemp[0]) > (end - start)) {
                start = lTemp[0];
                end = lTemp[1];
            }
        }

        System.out.println(s.substring(start, end + 1));
    }

    private int[] palindrome(char[] chars, int i) {
        int[] ret = new int[2];
        ret[0] = ret[1] = i;
        while (ret[0] > 0 && ret[1] < chars.length - 1 && chars[ret[0]] == chars[ret[1]]) {
            ret[0]--;
            ret[1]++;
        }
        if (chars[ret[0]] != chars[ret[1]]) {

            ret[0]++;
            ret[1]--;
        }

        int len = ret[1] - ret[0];

        if (i < chars.length - 1 && chars[i] == chars[i + 1]) {
            int j = i, k = i + 1;

            while (j > 0 && k < chars.length - 1 && chars[j] == chars[k]) {
                j--;
                k++;
            }
            if ( chars[j] != chars[k]) {
                j++;k--;
            }
            if (k - j > len) {
                ret[0] = j;
                ret[1] = k;
            }
        }

        return ret;
    }


}
