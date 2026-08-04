package puzzle.math;
import puzzle.Puzzle;

import java.util.Arrays;
import java.util.HashMap;
import java.util.Map;

/**
 * Find the maximum number of points lying on the same straight line.
 * LeetCode: Max Points on a Line
 * NOTE: Implementation incomplete (slope counting is commented out).
 */
public class CoupangPuzzle implements Puzzle {



    @Override
    public void resolve() {
        int[][] points = {{1, 3}, {-2, 5}, {4, 9}, {0, 0}, {5, 8}, {9, 13}, {-4, -7}};
        System.out.println(findMaxPointNumberInSameLine(points));
    }


    public int findMaxPointNumberInSameLine(int[][] points) {
        if (points == null || points.length < 2) return 0;
        int max = 2;
        int len = points.length;
        sortPointsByX(points);
        for (int i = 0; i < len; i++) {
            Map<Double, Integer> rate = new HashMap();
            for (int j = i + 1; j < len; j++) {
//                Double k = (points[j][1] - points[i][1]) * 1.0 /
            }
        }
        return max;
    }

    private void sortPointsByX(int[][] points) {
        Arrays.sort(points, (p0, p1) -> p0[0] - p1[0]);
    }

}
