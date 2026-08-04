package puzzle.backtracking;
import puzzle.Puzzle;

/**
 * Count permutations of 1..n where for each position i, arr[i] % i == 0 or i % arr[i] == 0.
 * LeetCode: Beautiful Arrangement
 * Approach: Backtracking with in-place swaps; the divisibility test prunes the search.
 * Complexity: Time O(n!), Space O(n).
 * Created by qingjuntian on 7/18/16.
 */
public class BeautifulPuzzle implements Puzzle {

    int number = 0;

    @Override
    public void resolve() {
        int n = 6;
//        dfs(new int[n + 1], n, 1);
//        System.out.println(number);
        System.out.println(beautifyArrangement(new int[]{1, 2, 3, 4, 5, 6}, 6));
    }


    private void dfs(int[] used, int n, int pos) {
        if (pos > n) {
            ++number;
            return ;
        }
        for (int i = 1; i <= n; i++) {
            if (used[i] == 0 && ((pos % i) == 0 || (i % pos) == 0)) {
                used[i] = 1;
                dfs(used, n, pos + 1);
                used[i] = 0;
            }
        }
    }

    private int beautifyArrangement(int[] arr, int n) {
        if (n == 0) {
            this.printNumArray(arr);
            return ++number;
        }
        for (int k = n; k > 0; k--) {
            swap(arr, n, k);
            if ((arr[n - 1] % n == 0) || (n % arr[n - 1]) == 0) {
                beautifyArrangement(arr, n - 1);
            }
            swap(arr, k, n);
        }
        return number;
    }

    private void swap(int[] arr, int n, int k) {
        int t = arr[k - 1];
        arr[k - 1] = arr[n - 1];
        arr[n - 1] = t;
    }

}
