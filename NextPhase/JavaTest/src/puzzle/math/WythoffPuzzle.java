package puzzle.math;
import puzzle.Puzzle;

import java.util.ArrayList;
import java.util.HashSet;
import java.util.List;
import java.util.Set;

/**
 * Wythoff's game: two piles; a move takes any positive amount from ONE pile OR an equal amount from
 * BOTH piles; the player taking the last stone wins. The losing (P-)positions are the pairs
 * (a_k, b_k) = (floor(k*phi), floor(k*phi^2)), which also satisfy b_k = a_k + k.
 * Methods:
 *   wythoffLosingPositions - generate the P-positions by the mex/gap method;
 *   isLosing               - answer a position query in O(1) via the golden-ratio test.
 * Created by qingjuntian on 6/12/16.
 */
public class WythoffPuzzle implements Puzzle {

    @Override
    public void resolve() {
        System.out.println("Wythoff P-positions with a <= 20:");
        for (int[] p : wythoffLosingPositions(20)) {
            System.out.println("  (" + p[0] + ", " + p[1] + ")");
        }
        System.out.println("isLosing(3, 5) = " + isLosing(3, 5));   // P-position -> true
        System.out.println("isLosing(2, 3) = " + isLosing(2, 3));   // not a P-position -> false
    }

    /**
     * Generate Wythoff's-game losing (P-)positions (a_k, b_k) with a_k <= limit.
     * Method (as in the original): a_k is the next value not yet used as some upper coordinate b_j
     * (the lower/upper Wythoff sequences partition the naturals), and b_k = a_k + k.
     */
    private List<int[]> wythoffLosingPositions(int limit) {
        List<int[]> positions = new ArrayList<>();
        Set<Integer> upper = new HashSet<>();       // the b_k values seen so far (upper Wythoff)
        int a = 0, k = 0;
        while (a <= limit) {
            while (upper.contains(a)) a++;           // a_k = smallest value not used as some b_j
            int b = a + k;                           // b_k = a_k + k  (Wythoff difference property)
            positions.add(new int[]{a, b});
            upper.add(b);
            k++;
            a++;
        }
        return positions;
    }

    /**
     * O(1) test: (x, y) is a Wythoff P-position (a loss for the player to move) iff, with x <= y,
     * x == floor((y - x) * phi), where phi = (1 + sqrt(5)) / 2.
     */
    private boolean isLosing(int x, int y) {
        if (x > y) { int t = x; x = y; y = t; }
        double phi = (1 + Math.sqrt(5)) / 2.0;
        return x == (int) Math.floor((y - x) * phi);
    }
}
