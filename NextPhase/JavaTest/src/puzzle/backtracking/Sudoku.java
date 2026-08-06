package puzzle.backtracking;
import puzzle.Puzzle;

/**
 * Fill a 9x9 Sudoku grid respecting row / column / box constraints.
 * LeetCode: Sudoku Solver
 * Approaches:
 *   solveSudoku     - classic DFS/backtracking; each trial scans row / column / box for validity;
 *   solveSudokuFast - DFS/backtracking with row/column/box occupancy tables for O(1) validity checks.
 * The fast occupancy-table solver is the primary version to study and run.
 * Created by qingjun on 2021/1/31.
 */
public class Sudoku implements Puzzle {

    @Override
    public void resolve() {
        int[][] sudoku = new int[][] {
                {0, 2, 0, 1, 9, 0, 0, 6, 0},
                {0, 0, 0, 7, 0, 0, 3, 0, 0},
                {0, 8, 0, 0, 0, 0, 0, 0, 9},
                {1, 0, 0, 0, 2, 0, 0, 4, 3},
                {2, 0, 8, 0, 0, 1, 0, 0, 5},
                {7, 0, 0, 6, 0, 0, 0, 0, 2},
                {0, 0, 2, 8, 0, 5, 9, 0, 0},
                {0, 6, 0, 4, 0, 0, 0, 0, 0},
                {5, 0, 0, 0, 0, 0, 2, 0, 0}
        };

        System.out.println("before:");
        printSudoku(sudoku);
        int[][] fast = copyBoard(sudoku);
        if (solveSudokuFast(fast)) {
            System.out.println("after (fast occupancy-table solver):");
            printSudoku(fast);
        } else {
            System.out.println("this puzzle is not resolvable");
        }
    }

    /**
     * Print the board, showing empty cells as '*'.
     */
    private void printSudoku(int[][] sudoku) {
        for (int[] line : sudoku) {
            for (int c : line ){
                if (c > 0) {
                    System.out.print(c + " ");
                } else {
                    System.out.print("* ");
                }
            }
            System.out.println();
        }
    }

    /**
     * Reference/back-to-basics solver: pick the next empty cell, try 1..9, recurse, and undo on failure.
     * Validity is checked by scanning the corresponding row, column, and 3x3 box each time.
     */
    private boolean solveSudoku(int[][] su) {
        for (int row = 0; row < 9; row++) {
            for (int col = 0; col < 9; col++) {
                if (su[row][col] != 0) continue;
                for (int v = 1; v < 10; v++) {
                    if (!isValidPlacement(su, row, col, v)) continue;
                    su[row][col] = v;
                    if (solveSudoku(su)) return true;
                    su[row][col] = 0;
                }
                return false;                    // this empty cell cannot take any value -> backtrack
            }
        }
        return true;                             // no empty cell left -> solved
    }

    /**
     * Primary solver: cache row/column/box occupancy so each trial digit is validated in O(1).
     * Returns false immediately if the initial board already violates Sudoku constraints.
     */
    private boolean solveSudokuFast(int[][] su) {
        boolean[][] rowUsed = new boolean[9][10];
        boolean[][] colUsed = new boolean[9][10];
        boolean[][] boxUsed = new boolean[9][10];
        for (int row = 0; row < 9; row++) {
            for (int col = 0; col < 9; col++) {
                int v = su[row][col];
                if (v == 0) continue;
                int box = boxId(row, col);
                if (rowUsed[row][v] || colUsed[col][v] || boxUsed[box][v]) {
                    return false;               // invalid seed board: duplicate already exists
                }
                rowUsed[row][v] = true;
                colUsed[col][v] = true;
                boxUsed[box][v] = true;
            }
        }
        return dfsFast(su, 0, rowUsed, colUsed, boxUsed);
    }

    /**
     * DFS over the 81 cells in row-major order. Occupancy tables hold the active constraints.
     */
    private boolean dfsFast(int[][] su, int pos, boolean[][] rowUsed, boolean[][] colUsed, boolean[][] boxUsed) {
        if (pos == 81) return true;
        int row = pos / 9, col = pos % 9;
        if (su[row][col] != 0) return dfsFast(su, pos + 1, rowUsed, colUsed, boxUsed);

        int box = boxId(row, col);
        for (int v = 1; v <= 9; v++) {
            if (rowUsed[row][v] || colUsed[col][v] || boxUsed[box][v]) continue;
            su[row][col] = v;
            rowUsed[row][v] = true;
            colUsed[col][v] = true;
            boxUsed[box][v] = true;
            if (dfsFast(su, pos + 1, rowUsed, colUsed, boxUsed)) return true;
            su[row][col] = 0;
            rowUsed[row][v] = false;
            colUsed[col][v] = false;
            boxUsed[box][v] = false;
        }
        return false;
    }

    /**
     * Map (row, col) to its 3x3 box id in [0, 8].
     */
    private int boxId(int row, int col) {
        return (row / 3) * 3 + (col / 3);
    }

    /**
     * Defensive board copy so multiple solver variants can be run independently.
     */
    private int[][] copyBoard(int[][] su) {
        int[][] ret = new int[su.length][];
        for (int i = 0; i < su.length; i++) {
            ret[i] = su[i].clone();
        }
        return ret;
    }

    /**
     * Return true iff placing {@code number} at ({@code row}, {@code col}) violates neither row,
     * column, nor 3x3 box constraints.
     */
    private boolean isValidPlacement(int[][] su, int row, int col, int number) {
        for (int i = 0; i < 9; i++) { //line 1 to 9
            if (su[i][col] == number && i != row) {
                return false;
            }
        }

        for (int j = 0; j < 9; j++) {
            if (su[row][j] == number && j != col) {
                return false;
            }
        }

        int r = row / 3 * 3;
        int c = col / 3 * 3;

        for (int i = 0; i < 3; i++ ) {
            for (int j = 0; j < 3; j++) {
                if (su[r + i][c + j] == number) {
                    return false;
                }
            }
        }

        return true;
    }
}