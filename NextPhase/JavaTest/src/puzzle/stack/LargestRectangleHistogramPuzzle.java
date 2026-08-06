package puzzle.stack;
import puzzle.Puzzle;

import java.util.Deque;
import java.util.LinkedList;

/**
 * Largest rectangle area in a histogram.
 * LeetCode: Largest Rectangle in Histogram
 * Approach: Monotonic increasing stack of bar indices; when a lower bar appears, pop and
 *   compute area = poppedHeight * width, where width spans back to the previous shorter bar.
 *   Two tail-handling styles: largestRectangleArea uses a virtual 0-height sentinel at i==n;
 *   largestRectangleAreaExplicitFlush runs an explicit flush loop after the scan. Both settle the
 *   still-increasing bars left on the stack.
 * Complexity: Time O(n), Space O(n).
 * Created by qingjuntian on 12/5/16.
 */
public class LargestRectangleHistogramPuzzle implements Puzzle {
    @Override
    public void resolve() {
        int[] arr = new int[]{2, 1, 5, 6, 2, 3, 4, 6, 6, 2, 1, 0};
        System.out.println(largestRectangleArea(arr));
        System.out.println(largestRectangleAreaExplicitFlush(arr));
    }

    /**
     * Monotonic-stack solution with a virtual trailing 0-height bar that flushes every remaining
     * increasing bar automatically.
     */
    private int largestRectangleArea(int[] arr) {
        if (arr.length == 0) return 0;
        Deque<Integer> stack = new LinkedList<>();   // indices whose heights are strictly increasing
        int max = 0;
        for (int i = 0; i <= arr.length; i++) {
            int h = (i == arr.length) ? 0 : arr[i];  // virtual 0-height bar at the end flushes the stack
            while (!stack.isEmpty() && h < arr[stack.peek()]) {
                int height = arr[stack.pop()];
                int width = stack.isEmpty() ? i : i - stack.peek() - 1;
                max = Math.max(max, height * width);
            }
            stack.push(i);
        }
        return max;
    }


    /**
     * Equivalent monotonic-stack solution with an explicit post-scan flush loop instead of a
     * virtual trailing sentinel bar.
     */
    public int largestRectangleAreaExplicitFlush(int[] arr) {
        if (arr.length == 0) return 0;
        Deque<Integer> stack = new LinkedList<>();    // indices with strictly increasing heights
        int max = 0;
        int i = 0;
        while (i < arr.length) {
            int h = arr[i];
            if (stack.isEmpty() || h > arr[stack.peek()]) {
                stack.push(i++);
            } else {
                int index = stack.pop();
                int width = stack.isEmpty() ? i : i - stack.peek() - 1;
                max = Math.max(max, width * arr[index]);
            }
        }
        while (!stack.isEmpty()) {                     // flush leftover bars: their width reaches the end i
            int index = stack.pop();
            int width = stack.isEmpty() ? i : i - stack.peek() - 1;
            max = Math.max(max, width * arr[index]);
        }
        return max;
    }
























}
