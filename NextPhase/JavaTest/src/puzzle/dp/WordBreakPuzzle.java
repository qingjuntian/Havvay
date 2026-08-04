package puzzle.dp;
import puzzle.Puzzle;

import java.util.Arrays;
import java.util.HashSet;
import java.util.Set;
import java.util.stream.Collectors;

/**
 * Decide whether a string can be segmented into words from a dictionary.
 * LeetCode: Word Break
 * Approach: Boolean DP over prefixes (with a naive recursion variant); seed dp[0]=true.
 * Complexity: Time O(n*d*k), Space O(n).
 * Created by qingjuntian on 6/16/16.
 */
public class WordBreakPuzzle implements Puzzle {



    @Override
    public void resolve() {
        String b = "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaabaaaaaaaaaaaacaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa";
        String[] words = new String[] {"ab","aac","aaa","aaaa","aaaaa","aaaaaa","aaaaaaa","aaaaaaaa","aaaaaaaaa","aaaaaaaaaa"};
        Set<String> dict = new HashSet<>();
        dict.addAll( Arrays.stream(words).collect(Collectors.toList()));
//        dict.add("car");
//        dict.add("ca");
//        dict.add("rs");
//        dict.add("fg");
//        dict.add("cd");
        System.out.println(wordBreakDP(b, dict));
    }

    public boolean wordBreak(String s, Set<String> dict) {
        if (s.length() == 0) return true;
        for (String a : dict) {
            if (s.startsWith(a)) {
                if (wordBreak(s.substring(a.length()), dict)) return true;
            }
        }
        return false;
    }

    public boolean wordBreakDP(String s, Set<String> dict) {
        boolean[] t = new boolean[s.length() + 1];
        t[0] = true;//set first to be true, why?
        //Because we need initial state
        for (int i = 0; i < s.length(); i++) {
            //should continue from match position
            if (!t[i])
                continue;

            for (String a : dict) {
                int len = a.length();
                int end = i + len;
                if (end > s.length())
                    continue;

                if (t[end]) continue;

                if (s.substring(i, end).equals(a)) {
                    t[end] = true;
                }
            }
        }

        return t[s.length()];
    }

}
