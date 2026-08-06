package puzzle.dp;
import puzzle.Puzzle;
import java.util.Arrays;

/**
 * Maximum number of envelopes that can be nested (Russian doll).
 * LeetCode: Russian Doll Envelopes
 * Approach: maxEnvelopesLIS() = standard O(n log n) sort + strict-LIS on heights (correct).
 * Complexity: Time O(n log n), Space O(n).
 * NOTE: maxEnvelopes() is an older ternary-tree attempt kept for reference; it is BUGGY
 *       (e.g. [[1,2],[1,1],[2,2],[3,3]] -> 2, but the answer is 3). Use maxEnvelopesLIS().
 * Created by qingjuntian on 7/1/16.
 */
public class RussianDollEnvelopesPuzzle implements Puzzle {

    @Override
    public void resolve() {
//        int[][] envelopes = {{1,3}, {3,5}, {6, 7}, {6, 8}, {8, 4}, {9, 5}};
        int[][] envelopes = {{15,8},{2,20},{2,14},{4,17},{8,19},{8,9},{5,7},{11,19},{8,11},{13,11},{2,13},{11,19},{8,11},{13,11},{2,13},{11,19},{16,1},{18,13},{14,17},{18,19}};
//        int[][] envelopes = {{1,3}};
//        for (int[s] envelope : envelopes) {
//            envelope = new int[2];
//        }

        System.out.println("tree method (unreliable): " + maxEnvelopes(envelopes));
        System.out.println("sort+LIS (correct):       " + maxEnvelopesLIS(envelopes));
    }

    /**
     * Legacy ternary-tree node used by the older experimental approach below.
     */
    private class Node {
        private Node left, middle, right;

        int[] value;

        public Node(int[] v) {
            value = v;
        }

        public void append(int[] v) {
            if (v[0] > value[0] && v[1] > value[1]) {
                if (left == null) {
                    left = new Node(v);
                } else {
                    left.append(v);
                }
            } else if (v[0] < value[0] && v[1] < value[1]) {

                if (right == null) {
                    right = new Node(v);
                } else {
                    right.append(v);
                }
            } else {
                if (middle == null) {
                    middle = new Node(v);
                } else {
                    middle.append(v);
                }
            }
        }

    }

    /**
     * Legacy tree-style attempt kept only for contrast. Prefer maxEnvelopesLIS().
     */
    public int maxEnvelopes(int[][] envelopes) {
        if (envelopes == null || envelopes.length == 0) return 0;
        Node root = new Node(envelopes[0]);
        for (int[] envelope : envelopes) {
            root.append(envelope);
        }

        return maxEnvelopes(root, 0);
    }

    /**
     * Recursive evaluator for the legacy tree-style attempt.
     */
    public  int maxEnvelopes(Node root, int len) {

        if (root == null) return 0;

        int max = maxEnvelopes(root.left, 1) + maxEnvelopes(root.right, 1) + 1;
        max = Math.max(max, maxEnvelopes(root.middle, 0));
        max = Math.max(max, maxEnvelopes(root.left, 0));
        max = Math.max(max, maxEnvelopes(root.right, 0));

        return max;
    }

    /**
     * Standard O(n log n) solution: sort by width asc (equal width -> height DESC, so same-width
     * envelopes cannot chain), then take the strict LIS of the heights.
     */
    public int maxEnvelopesLIS(int[][] envelopes) {
        if (envelopes == null || envelopes.length == 0) return 0;
        int[][] es = envelopes.clone();                                   // don't mutate the caller's array
        Arrays.sort(es, (a, b) -> a[0] != b[0] ? a[0] - b[0] : b[1] - a[1]);
        int[] tails = new int[es.length];
        int size = 0;
        for (int[] e : es) {
            int h = e[1];
            int lo = 0, hi = size;                                        // lower_bound: first tail >= h
            while (lo < hi) {
                int mid = (lo + hi) >>> 1;
                if (tails[mid] < h) lo = mid + 1;
                else hi = mid;
            }
            tails[lo] = h;
            if (lo == size) size++;
        }
        return size;
    }

}
