package puzzle.strings;
import puzzle.Puzzle;

import java.util.BitSet;

/**
 * Remove duplicate characters from a string, keeping only the first occurrence of each.
 * Approach: Single pass using a BitSet to mark characters already seen.
 * Complexity: Time O(n), Space O(1) for a fixed charset.
 */
public class DedupStringPuzzle implements Puzzle {
    /**
     * Deduplicate a sample string and print the result.
     */
    @Override
    public void resolve() {
        String s = "baabaaabc";
        System.out.println(dedup(s));
    }

    /**
     * Return the string with duplicate characters removed, keeping only the first occurrence of each.
     * A BitSet is used as a compact fixed-charset "seen" table.
     */
    private String dedup(String s) {
        if (s == null || s.length() == 0) {
            return s;
        }

        BitSet bitSet = new BitSet(256);
        char[] arr = s.toCharArray();
        StringBuilder ret = new StringBuilder();

        for (char c : arr) {
            if (!bitSet.get(c)) {
                ret.append(c);
                bitSet.set(c);
            }
        }
        return ret.toString();
    }
}
