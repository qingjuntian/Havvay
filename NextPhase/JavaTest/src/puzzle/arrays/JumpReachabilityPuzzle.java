package puzzle.arrays;
import puzzle.Puzzle;

import java.util.ArrayDeque;
import java.util.Deque;

/**
 * Jump Game variant: from index i you may jump to i+arr[i]+1, i+arr[i]+2, or i+arr[i]*2.
 * Two interpretations, both solved here via BFS (helper bfsReach):
 *   canReachEnd     (A) - zeros are plain data; can index 0 reach or pass the last index?
 *   canLandAllZeros (B) - every zero is a mandatory checkpoint that must be landed on, in order.
 * Created by qingjuntian on 6/4/16.
 */
public class JumpReachabilityPuzzle implements Puzzle {


    @Override
    public void resolve() {
        int[] arr = {1, 2, 5, 1, 15, 0, 0, 3, 2, 5, 7, 4, 1, 0, 8};
        System.out.println("canReachEnd (A):     " + canReachEnd(arr));
        System.out.println("canLandAllZeros (B): " + canLandAllZeros(arr));
    }

    /**
     * Interpretation (A) -- plain Jump Game reachability: from index i you may jump to i+arr[i]+1,
     * i+arr[i]+2, or i+arr[i]*2. True iff, starting at 0, you can reach the last index (n-1) or beyond.
     * Time O(n), Space O(n).
     */
    public boolean canReachEnd(int[] arr) {
        return arr.length >= 1 && bfsReach(arr, 0, -1);
    }

    /**
     * Interpretation (B) -- every zero is a mandatory checkpoint that must be landed on EXACTLY,
     * in increasing index order, before finally reaching/passing the last index. Chains reachability
     * 0 -> z1 -> z2 -> ... -> zk -> end, each link solved by one BFS. Time O(n^2), Space O(n).
     */
    public boolean canLandAllZeros(int[] arr) {
        int n = arr.length;
        if (n == 0) return false;
        int from = 0;
        for (int z = 0; z < n; z++) {
            if (arr[z] == 0) {                           // z is the next checkpoint
                if (!bfsReach(arr, from, z)) return false;
                from = z;
            }
        }
        return bfsReach(arr, from, -1);                  // from the last checkpoint (or 0), reach the end
    }

    /**
     * BFS from src over the jump graph. If target >= 0, returns whether some jump lands EXACTLY on
     * index target; if target < 0, returns whether some jump reaches index >= n-1 (last index or beyond).
     */
    private boolean bfsReach(int[] arr, int src, int target) {
        int n = arr.length;
        if (target >= 0 ? src == target : src >= n - 1) return true;
        boolean[] visited = new boolean[n];
        Deque<Integer> queue = new ArrayDeque<>();
        queue.add(src);
        visited[src] = true;
        while (!queue.isEmpty()) {
            int i = queue.poll();
            for (int nx : new int[]{ i + arr[i] + 1, i + arr[i] + 2, i + arr[i] * 2 }) {
                if (target >= 0 ? nx == target : nx >= n - 1) return true;
                if (nx >= 0 && nx < n && !visited[nx]) {
                    visited[nx] = true;
                    queue.add(nx);
                }
            }
        }
        return false;
    }
}
