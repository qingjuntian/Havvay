package puzzle.sorting;
import puzzle.Puzzle;

/**
 * Sort an array using a binary heap.
 * Approach: Build a max-heap, then repeatedly swap the root with the end and sift down.
 * Complexity: Time O(n log n), Space O(1).
 * Created by qingjuntian on 6/28/16.
 */
public class SiftSort implements Puzzle {

    private static int swapTimes = 0;

    @Override
    public void resolve() {
        int[] nArray = new int[]{1, 3, 4, 2, 15, 4, 2, 7, 9, 8, 14, 10};
        for (int i = nArray.length / 2 - 1; i >= 0; i--) {
            heapify(nArray, i, nArray.length);
        }

        for (int i = nArray.length - 1; i >= 0; i--) {
            swap(nArray, 0, i);
            heapify(nArray, 0, i);
        }

        printNumArray(nArray);
        System.out.println("" + swapTimes);
    }

    private void heapify(int[] arr, int i, int size) {
        int left = 2 * i + 1;
        int right = 2 * i + 2;
        int largest = i;
        while (left < size) {
            if (arr[left] > arr[i]) {
                largest = left;
            }
            if (right < size && arr[right] > arr[largest]) {
                largest = right;
            }
            if (largest != i) {
                swap(arr, largest, i);
            } else {
                break;
            }

            i = largest;
            left = 2 * i + 1;
            right = 2 * i + 2;
        }

    }

    private void swap(int[] nArray, int i, int l) {

        int temp = nArray[i];
        nArray[i] = nArray[l];
        nArray[l] = temp;
        swapTimes++;
    }


    private void heapinsert(int[] arr, int index) {
        while (index != 0) {
            int parent = (index - 1) / 2;
            if (arr[index] > arr[parent]) {
                swap(arr, index, parent);
                index = parent;
            } else {
                break;
            }
        }
    }
}
