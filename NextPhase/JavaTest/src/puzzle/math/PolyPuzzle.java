package puzzle.math;
import puzzle.Puzzle;

import java.util.ArrayList;
import java.util.List;

/**
 * Determine whether a polygon (given by ordered points) is convex.
 * LeetCode: Convex Polygon
 * Approach: Check that the sign of consecutive edge cross products never flips.
 * Complexity: Time O(n), Space O(1).
 */
public class PolyPuzzle implements Puzzle {

    /**
     * Build a sample polygon and print whether it is convex.
     */
    @Override
    public void resolve() {
        List<List<Integer>> ps = new ArrayList<>();

        List<Integer> p = new ArrayList<>();
        p.add(0);
        p.add(0);
        ps.add(p);

        p = new ArrayList<>();
        p.add(0);
        p.add(0);
        ps.add(p);

        p = new ArrayList<>();
        p.add(0);
        p.add(1);
        ps.add(p);

        p = new ArrayList<>();
        p.add(1);
        p.add(1);
        ps.add(p);


        p = new ArrayList<>();
        p.add(2);
        p.add(1);
        ps.add(p);


        p = new ArrayList<>();
        p.add(2);
        p.add(2);
        ps.add(p);


        p = new ArrayList<>();
        p.add(2);
        p.add(3);
        ps.add(p);


        p = new ArrayList<>();
        p.add(3);
        p.add(3);
        ps.add(p);

        p = new ArrayList<>();
        p.add(3);
        p.add(0);
        ps.add(p);

        System.out.println(isConvex(ps));
    }

    /**
     * A polygon is convex iff the sign of the turn (cross product) never flips while walking
     * through triples of consecutive vertices.
     */
    public boolean isConvex(List<List<Integer>> points) {
        int n = points.size();
        boolean pos = false, neg = false;
        for (int i = 0; i < n; i++) {                       // check the turn at every vertex
            long cross = product(points.get(i), points.get((i + 1) % n), points.get((i + 2) % n));
            if (cross > 0) pos = true;
            if (cross < 0) neg = true;
            if (pos && neg) return false;                   // orientation flipped -> not convex
        }
        return true;
    }


    /**
     * Cross product of vectors p0->p1 and p0->p2. Positive = left turn, negative = right turn,
     * zero = collinear.
     */
    private long product(List<Integer> p0, List<Integer> p1, List<Integer> p2) {
        return (long) (p1.get(0) - p0.get(0)) * (p2.get(1) - p0.get(1)) -
                (long) (p2.get(0) - p0.get(0)) * (p1.get(1) - p0.get(1));
    }
}
