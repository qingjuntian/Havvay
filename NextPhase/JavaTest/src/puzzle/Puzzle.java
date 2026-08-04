package puzzle;

/**
 * Common interface implemented by every puzzle class; defines resolve().
 * NOTE: Shared interface, not a puzzle itself.
 * Created by qingjuntian on 8/3/16.
 */
public interface Puzzle {
    default public void resolve() {
        System.out.println("Not implemented yet.");
    }

    default public void printNumArray(int[] array) {
        if (array == null || array.length == 0) {
            System.out.println("input array is empty!");
        }
        for (int item: array) {
            System.out.print(item + " ");
        }
        System.out.println();
    }
}
