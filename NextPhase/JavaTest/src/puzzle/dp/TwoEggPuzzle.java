package puzzle.dp;
import puzzle.Puzzle;

/**
 * Minimize the worst-case number of trials in the egg-drop problem.
 * LeetCode: Super Egg Drop
 * Approach: DP over floors and egg count: 1 + min over drop floors of max(break, not-break).
 * Complexity: Time O(n^2 m), Space O(nm).
 * Created by qingjuntian on 6/6/16.
 */
public class TwoEggPuzzle implements Puzzle {
    @Override
    public void resolve() {
        int n = 100, m = 3;
        System.out.println("O(n^2*m) DP:   " + minTry(n, m));
        System.out.println("O(k*t) super:  " + minTrySuper(n, m));
    }

    private int minTry(int n) {
        if (n <= 0) return 0;
        int[] minArr = new int[n + 1];
        minArr[0] = 0;
        minArr[1] = 1;                       // 1 floor -> 1 trial (was wrongly 0)

        for (int i = 2; i <= n; i++) {
            int min = Integer.MAX_VALUE;
            for (int j = 1; j < i; j++) {
                min = Math.min(min, Math.max(j - 1, minArr[i - j]));
            }
            minArr[i] = min + 1;
        }

        return minArr[n];                    // was minArr[n - 1] (off-by-one)
    }

    private int minTry(int n, int m) {
        if (n <= 0 || m <= 0) return 0;
        int[][] minArr = new int[n + 1][m + 1];

        for (int i = 1; i <= n; i++) {
            minArr[i][1] = i;                        // 1 egg -> linear scan
        }
        for (int k = 2; k <= m; k++) {               // fill missing base cases (were left as 0)
            minArr[1][k] = 1;                        // 1 floor  -> 1 trial
            if (n >= 2) minArr[2][k] = 2;            // 2 floors (>=2 eggs) -> 2 trials
        }

        for (int k = 2; k <= m; k++) {
            for (int i = 3; i <= n; i++) {
                int min = Integer.MAX_VALUE;
                for (int j = 1; j < i; j++) {
                    min = Math.min(min, Math.max(minArr[j - 1][k - 1], minArr[i - j][k]));
                }
                minArr[i][k] = min + 1;
            }
        }

        return minArr[n][m];
    }

    // Optimal O(k * answer): index by TRIALS, not floors. f[e] = max floors solvable with t trials, e eggs.
    // f(t, e) = f(t-1, e-1) + f(t-1, e) + 1; return the smallest t with f(t, m) >= n.
    private int minTrySuper(int n, int m) {
        if (n <= 0 || m <= 0) return 0;
        int[] f = new int[m + 1];               // f[e] rolls over trials t = 1, 2, 3, ...
        int t = 0;
        while (f[m] < n) {
            t++;
            for (int e = m; e >= 1; e--) {       // high egg -> low, so f[e-1] is still the previous t
                f[e] = f[e] + f[e - 1] + 1;
            }
        }
        return t;                                // first t whose reach covers all n floors
    }

}
