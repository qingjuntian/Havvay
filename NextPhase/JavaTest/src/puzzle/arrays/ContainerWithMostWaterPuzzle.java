package puzzle.arrays;
import puzzle.Puzzle;

/**
 * Two classic two-pointer problems in one file.
 * Active path:
 *   - Container With Most Water: move the shorter wall inward.
 * Helper:
 *   - Two Sum on a sorted array: shrink from both ends based on the current sum vs target.
 * Complexity: both main routines run in O(n) time and O(1) extra space.
 */
public class ContainerWithMostWaterPuzzle implements Puzzle {
    /**
     * Run the container-with-most-water demo on a sample height array.
     */
    @Override
    public void resolve() {
        // Active path: Container With Most Water. The two-sum helper above is kept for contrast.
        int[] array = new int[] {3, 5, 1, 3, 4, 7, 8, 11};
        findMaxContainerArea(array);
    }

    /**
     * Two-sum via two pointers. PRECONDITION: array must be SORTED ascending; the two-pointer
     * shrink logic is invalid on unsorted input (note the commented demo array above is NOT sorted).
     */
    private void findTwoSumPairs(int[] array, int n) {
        if (array == null || array.length == 0) {
            return;
        }
        int i = 0, j = array.length - 1;
        while (i < j) {
            if (array[i] + array[j] > n) {
                j--;
            } else if (array[i] + array[j] < n) {
                i++;
            } else {
                System.out.println(array[i] + "\t" + array[j]);
                i++;
                j--;
            }
        }
    }

    /**
     * Container With Most Water: move the shorter wall inward because the current shorter wall is
     * the limiting height of any container using the current endpoints.
     */
    private void findMaxContainerArea(int[] array) {
        if (array == null || array.length == 0) {
            return;
        }
        int i = 0, j = array.length - 1;
        int volume = Integer.MIN_VALUE;
        while (i < j) {
            int width = j - i;
            int height = Math.min(array[i], array[j]);
            if (width * height > volume) {
                volume = width * height;
            }
            if (array[i] < array[j]) {
                i++;
            } else {
                j--;
            }
        }
        System.out.println("max volume is " + volume);
    }
}
