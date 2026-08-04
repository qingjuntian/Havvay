package puzzle.math;
import puzzle.Puzzle;

import java.util.ArrayList;
import java.util.List;

/**
 * Determine whether a polygon (given by ordered points) is convex.
 * LeetCode: Convex Polygon
 * Approach: Check that the sign of consecutive edge cross products never flips.
 * Complexity: Time O(n), Space O(1).
 * Created by qingjuntian on 6/26/16.
 */
public class PolyPuzzle implements Puzzle {

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

    public boolean isConvex(List<List<Integer>> points) {
        List<Integer> p0 = points.get(0);
        List<Integer> p1 = points.get(1);
        List<Integer> p2 = points.get(2);
        int product = product(p0, p1, p2);
        int number = points.size();
        for (int i = 3; i < number; i++) {
            List<Integer> p3 = points.get(i);
            int p = product(p1, p2, p3);
            if (p * product < 0) return false;
            product = (product == 0 ? p : product);
            p1 = p2;
            p2 = p3;
        }
        int p = product(p1, p2, p0);
        if (p * product < 0) return false;
        return p * product(p2, p0, points.get(1)) >= 0;
    }


    private int product(List<Integer> p0, List<Integer> p1, List<Integer> p2) {
        return (p1.get(0) - p0.get(0)) * (p2.get(1) - p0.get(1)) -
                (p2.get(0) - p0.get(0)) * (p1.get(1) - p0.get(1));
    }
}
