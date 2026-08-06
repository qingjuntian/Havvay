package puzzle.sorting;
import puzzle.Puzzle;

/**
 * Experimental sorting routine (calls quicksort, then an unfinished 'swing' pass).
 * NOTE: Incomplete; not a valid standalone algorithm.
 */
public class SwingSort implements Puzzle {
    /**
     * Run the placeholder demo on an empty sample array.
     */
    @Override
    public void resolve() {
        int[] numbers = new int[]{};
        printNumArray(numbers);
        swingSort(numbers);
        printNumArray(numbers);
    }

    /**
     * Sort the input first; the intended post-processing step was never finished, so this currently
     * behaves as a thin wrapper around quicksort.
     */
    private void swingSort(int[] numbers) {
        QuickSort.qsort(numbers, 0, numbers.length - 1);
    }
}
