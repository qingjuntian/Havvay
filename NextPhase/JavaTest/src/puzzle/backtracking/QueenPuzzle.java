package puzzle.backtracking;
import puzzle.Puzzle;

/**
 * Place N queens on an N x N board so that none attack each other.
 * LeetCode: N-Queens
 * Approach: Iterative backtracking with occupied-column and diagonal (row+col, row-col) arrays.
 * Complexity: Time O(N!), Space O(N).
 * Created by qingjuntian on 6/21/16.
 */
public class QueenPuzzle implements Puzzle {
    int[] a;
    int[] b;
    int[] c;

    @Override
    public void resolve() {
        int n = 10;
        if (n < 1) return;
        a = new int [2 * n - 1];
        b = new int [2 * n - 1];
        c = new int[n];
        System.out.println("iterative:");
        placeQueen(n);

        a = new int [2 * n - 1];
        b = new int [2 * n - 1];
        c = new int[n];
        System.out.println("recursive:");
        placeQueenRecursive(n);
    }

    /**
     * Iterative/manual-backtracking formulation. room[row] stores the chosen column in that row.
     */
    private void placeQueen(int n) {
        int[] room = new int[n];
        int i = 0;
        int j = 0;
        while (i < n && i >= 0) {
            if (pickNextRoom(room, i, j, n) == true) {
                i++;
                j = 0;
            } else {
                i--;
                if( i < 0) break;
                a[room[i] + i] = 0;
                b[n - 1 + i - room[i]] = 0;
                c[room[i]] = 0;
                j = room[i] + 1;
            }
        }
        if (i == n) {
            String blank = "";
            for (j=0; j < n * 2; j++) {
                blank += " ";
            }

            for (j = 0; j < n; j++) {
                System.out.println(blank.substring(0, room[j] * 2) + "*");
            }
        } else {
            System.out.println(n + " queens could not be placed in " + n + "*" + n + " grids.");
        }
    }

    /**
     * Starting from column j in row i, place the next valid queen if possible.
     */
    private boolean pickNextRoom(int[] room, int i, int j, int n) {
        for (; j < n; j++) {
            if (validRoom(i, j , n)) {
                room[i] = j;
                a[j + i] = 1;
                b[n - 1 +  i - j] = 1;
                c[j] = 1;
                return true;
            }
        }
        return false;
    }

    /**
     * O(1) legality check via occupied-column and occupied-diagonal tables.
     */
    private boolean validRoom(int i, int j, int n) {
        return a[i + j] == 0 && b[n - 1 + i - j] == 0 && c[j] == 0;
    }

    /**
     * Recursive DFS/backtracking formulation of the same N-Queens search.
     */
    private void placeQueenRecursive(int n) {
        int[] room = new int[n];
        if (dfs(room, 0, n)) {
            String blank = "";
            for (int j = 0; j < n * 2; j++) {
                blank += " ";
            }
            for (int j = 0; j < n; j++) {
                System.out.println(blank.substring(0, room[j] * 2) + "*");
            }
        } else {
            System.out.println(n + " queens could not be placed in " + n + "*" + n + " grids.");
        }
    }

    /**
     * Return true once all rows are filled with non-attacking queens.
     */
    private boolean dfs(int[] room, int row, int n) {
        if (row == n) {
            return true;
        }
        for (int col = 0; col < n; col++) {
            if (!validRoom(row, col, n)) continue;
            room[row] = col;
            a[row + col] = 1;
            b[n - 1 + row - col] = 1;
            c[col] = 1;
            if (dfs(room, row + 1, n)) {
                return true;
            }
            a[row + col] = 0;
            b[n - 1 + row - col] = 0;
            c[col] = 0;
        }
        return false;
    }
}
