package puzzle.math;
import puzzle.Puzzle;

/**
 * Compute safe/unsafe positions for a 2D grid Nim-like game: a token moves right, up, or up-right;
 * the player who reaches the top-right corner (no moves left) loses. safe[r][c]=1 marks a P-position
 * (mover loses), -1 an N-position (mover wins). initSafe/markSafe fill it via a P/N-position DP.
 * Complexity: Time O(mn), Space O(mn).
 * NOTE: initSafe2 is an incomplete stub (unused); resolve() uses the correct initSafe.
 * Created by qingjuntian on 8/6/16.
 */
public class Nim2Puzzle implements Puzzle {

    @Override
    public void resolve() {
        nim(5, 7);
    }


    private void nim(int m, int n) {

        int[][] safe = initSafe(m, n);


        System.out.println(safe[m - 1][0] == -1);
    }

    /** STUB (unused, incomplete) -- kept only as an artifact; resolve() now uses initSafe. */
    private int[][] initSafe2(int m, int n) {
        int ret[][] = new int[m][n];
        ret[0][n - 1] = 1;
        int[] flag45 = new int[m + n - 2];

        return ret;
    }

    private int[][] initSafe(int m, int n) {
        int ret[][] = new int[m][n];
        ret[0][n - 1] = 1;
        for (int row = 0; row < m; row++) {
            for (int col = n - 1; col >= 0; col --) {
                markSafe(ret, row, col);
            }
        }
        return ret;
    }

    private void markSafe(int[][] ret, int row, int col) {
        if (row == 0 && col == ret[0].length - 1) return;
        if (row == 0) {
            ret[row][col] = -ret[row][col + 1];
            return;
        }

        if (col == ret[0].length - 1) {
            ret[row][col] = -ret[row - 1][col];
            return;
        }

        if (ret[row][col + 1] == -1 && ret[row - 1][col] == -1 && ret[row - 1][col + 1] == -1) {
            ret[row][col] = 1;
        } else {
            ret[row][col] = -1;
        }

    }


}
