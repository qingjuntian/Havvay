package puzzle.sorting;
import puzzle.Puzzle;

/**
 * Experimental sorting routine (calls quicksort, then an unfinished 'swing' pass).
 * NOTE: Incomplete; not a valid standalone algorithm.
 * Created by qingjuntian on 6/27/16.
 */
public class SwingSort implements Puzzle {
    @Override
    public void resolve() {
        int[] numbers = new int[]{};
        printNumArray(numbers);
        swingSort(numbers);
        printNumArray(numbers);
    }

    private void swingSort(int[] numbers) {
        QuickSort.qsort(numbers, 0, numbers.length - 1);

        int low = 0, high = numbers.length - 1;
        if ((numbers.length & 1) == 1) {
            low ++;
            high --;
        }
    }
}
