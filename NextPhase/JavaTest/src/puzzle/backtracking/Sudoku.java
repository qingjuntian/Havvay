package puzzle.backtracking;
import puzzle.Puzzle;

import java.util.LinkedList;

class Cell {
    int row;
    int col;
    int value;

    public Cell(int r, int c, int v) {
        this.row = r;
        this.col = c;
        this.value = v;
    }
}

/**
 * Fill a 9x9 Sudoku grid respecting row / column / box constraints.
 * LeetCode: Sudoku Solver
 * NOTE: Backtracking solver is incomplete / a draft.
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

        printSudoku(sudoku);
        LinkedList<Cell> queue = new LinkedList<Cell>();

        try {
            //fillInSudoku(sudoku, queue, 0, 0, 1);
        } catch (Exception e) {
            System.out.println("this puzzle is not resolvable");
        }

        return;
    }

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

    private void fillInSudoku(int[][] su, LinkedList<Cell> queue, int missedNumber) throws Exception {
        while (queue.size() < missedNumber) {
            for (int v = 1; v < 10; v++) {
                int row = 0;
                int col = 0;
                while (row < 9) { //line 1 to 9
                    int j = 0;
                    for (; j < 9; j++) {
                        if (su[row][j] == v) {
                            break;
                        }
                    }
                    if (j == 9) { // not found number in row
                        j = col;
                        for (; j < 9; j++) {
                            if (su[row][j] == 0 && ExamineNumber(su, row, j, v)) {
                                queue.addLast(new Cell(row, j, v));
                                break;
                            }
                        }
                        if (j == 9) {
                            // can not put v in row
                            traceBack(su, queue);
                            row--;
                            col++;
                        }
                    }

                }
            }
        }
    }

    private void traceBack(int[][] su, LinkedList<Cell> queue) {
        Cell c = queue.removeLast();
        su[c.row][c.col] = 0;

    }

    private boolean ExamineNumber(int[][] su, int row, int col, int number) {


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