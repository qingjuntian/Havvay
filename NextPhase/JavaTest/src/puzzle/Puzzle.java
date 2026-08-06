package puzzle;

/**
 * Common contract implemented by every puzzle demo in this repository.
 * <p>
 * Most classes expose their runnable sample through {@link #resolve()}, while
 * {@link #printNumArray(int[])} is a small shared helper used by array-based demos.
 */
public interface Puzzle {
    /**
     * Run the sample scenario for this puzzle class.
     */
    default void resolve() {
        System.out.println("Not implemented yet.");
    }

    /**
     * Print an integer array on one line for quick console inspection.
     */
    default void printNumArray(int[] array) {
        if (array == null || array.length == 0) {
            System.out.println("input array is empty!");
        }
        for (int item : array) {
            System.out.print(item + " ");
        }
        System.out.println();
    }
}
