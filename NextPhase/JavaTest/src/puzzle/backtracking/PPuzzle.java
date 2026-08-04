package puzzle.backtracking;
import puzzle.Puzzle;

/**
 * Generate all permutations of an array.
 * LeetCode: Permutations
 * Approach: Recursive in-place swapping with a swap-back to restore state between branches.
 * Complexity: Time O(n*n!), Space O(n).
 * Created by qingjuntian on 6/7/16.
 */
public class PPuzzle implements Puzzle {

    @Override
    public void resolve() {
        int n = 9;
        int [] arr = new int[n];
        for (int i = 1; i < n + 1; i++) {
            arr[i - 1] = i;
        }
        printP2(arr, n);
    }

    private void printP(int[] arr, int n) {
        if (n == 1) {
            printNumArray(arr);
            return;
        }

        for (int i = n - 1; i >= 0 ; i--) {
            swap(arr, i, n - 1);
            printP(arr, n-1);
            swap(arr, i, n - 1);
        }
    }



    private void printP2(int[] arr, int number) {
        if (number == 1) {
            this.printNumArray(arr);
            return;
        }

        for (int j = number - 1; j >= 0 ;j--) {
            swap(arr, j, number - 1);
            printP2(arr, number - 1);
            swap(arr, j, number - 1);
        }
    }


    private void swap(int[] arr, int i, int n) {
        int a = arr[i];
        arr[i]  = arr[n];
        arr[n] = a;
    }




















}
