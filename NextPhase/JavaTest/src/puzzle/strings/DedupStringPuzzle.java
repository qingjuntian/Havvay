package puzzle.strings;
import puzzle.Puzzle;

import java.util.BitSet;
import java.util.HashSet;
import java.util.Set;

/**
 * Remove duplicate characters from a string, keeping only the first occurrence of each.
 * Approach: Single pass using a BitSet to mark characters already seen.
 * Complexity: Time O(n), Space O(1) for a fixed charset.
 * Created by qingjuntian on 8/6/16.
 */
public class DedupStringPuzzle implements Puzzle {
    @Override
    public void resolve() {
        String s = "baabaaabc";
        dedup(s);
    }

    private void dedup(String s) {

        if (s == null || s.length() == 0) return;

//        Set<Character> charSet = new HashSet<>();
        BitSet bitSet = new BitSet(256);

        char[] arr = s.toCharArray();

        StringBuffer ret = new StringBuffer();

        for (char c : arr) {
            if (bitSet.get(c) == false) {
                ret.append(c);
                bitSet.set(c);
            }
        }

        System.out.println(ret.toString());

//        char[] chars = s.toCharArray();
//
//        int i = 0, j = 0;
//
//        String ret = "";
//
//        while (j < s.length()) {
//            while (j < s.length() && chars[i] == chars[j]) {
//                j ++;
//            }
//            if (j  <= s.length()) {
//                ret += chars[i];
//                i = j;
//            }
//        }
//
//        if (ret.length() == 0) ret += chars[0];


    }
}
