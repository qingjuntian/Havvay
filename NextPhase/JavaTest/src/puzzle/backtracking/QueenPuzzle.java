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
        placeQueen(n);
    }

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

    private boolean validRoom(int i, int j, int n) {
        return a[i + j] == 0 && b[n - 1 + i - j] == 0 && c[j] == 0;
    }
}
