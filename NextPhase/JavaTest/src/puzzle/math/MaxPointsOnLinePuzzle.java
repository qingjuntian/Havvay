package puzzle.math;
import puzzle.Puzzle;

import java.util.HashMap;
import java.util.Map;

/**
 * Find the maximum number of points lying on the same straight line.
 * LeetCode: Max Points on a Line
 * Approach: anchor each point i, group the others by GCD-reduced slope dx/dy (direction-normalized),
 * counting duplicates separately; the best line through i is maxSlopeGroup + duplicates + 1. Time O(n^2).
 */
public class MaxPointsOnLinePuzzle implements Puzzle {



    @Override
    public void resolve() {
        int[][] points = {{1, 3}, {-2, 5}, {4, 9}, {0, 0}, {5, 8}, {9, 13}, {-4, -7}};
        System.out.println(findMaxPointNumberInSameLine(points));
    }

    /**
     * O(n^2) anchor-and-slope solution. For each anchor point i, group all later points by their
     * normalized slope relative to i. The largest bucket through i, plus duplicates of i, gives the
     * best line through that anchor.
     */
    public int findMaxPointNumberInSameLine(int[][] points) {
        if (points == null) return 0;
        int n = points.length;
        if (n < 2) return n;
        int max = 1;
        for (int i = 0; i < n; i++) {
            Map<String, Integer> slopes = new HashMap<>();
            int duplicates = 0;                        // points identical to point i
            int localMax = 0;                          // largest collinear group through i (among j > i)
            for (int j = i + 1; j < n; j++) {
                int dx = points[j][0] - points[i][0];
                int dy = points[j][1] - points[i][1];
                if (dx == 0 && dy == 0) {              // same coordinates -> lies on every line through i
                    duplicates++;
                    continue;
                }
                int g = gcd(Math.abs(dx), Math.abs(dy));
                dx /= g;
                dy /= g;
                if (dx < 0 || (dx == 0 && dy < 0)) {   // normalize direction so opposite slopes share a key
                    dx = -dx;
                    dy = -dy;
                }
                String slope = dx + "/" + dy;
                int c = slopes.merge(slope, 1, Integer::sum);
                localMax = Math.max(localMax, c);
            }
            max = Math.max(max, localMax + duplicates + 1);   // +1 counts point i itself
        }
        return max;
    }

    /**
     * Greatest common divisor used to normalize slope directions into reduced integer pairs.
     */
    private int gcd(int a, int b) {
        return b == 0 ? a : gcd(b, a % b);
    }

}
