package puzzle.linkedlist;

import puzzle.Puzzle;
import model.Node;

/**
 * Rotate a linked list to the right by k positions.
 * LeetCode: Rotate List
 * Approach: Form a cycle, walk to the new tail (k %= length), then break the cycle.
 * Complexity: Time O(n), Space O(1).
 * Example: 1 -> 2 -> 3 -> 4 rotated right by 1 becomes 4 -> 1 -> 2 -> 3.
 * (Equivalently, rotating right by 3 becomes 2 -> 3 -> 4 -> 1.)
 */
public class RightSpinListPuzzle implements Puzzle {

    /**
     * Build a sample list, rotate it, and print both before/after forms.
     */
    @Override
    public void resolve() {
        int[] array = new int[]{6, 5, 4, 3, 2, 1};
        Node head = null;
        for (int i : array) {
            if (head == null) {
                head = new Node(i);
            } else {
                head = head.addNode(i);
            }
        }
        head.debug();
        head = rightSpin(head, 2);
        head.debug();
    }

    /**
     * Rotate the list to the right by {@code k} positions.
     */
    private Node rightSpin(Node head, int k) {
        if (head == null || head.next == null || k <= 0) {
            return head;
        }

        Node tail = head;
        int len = 1;
        while (tail.next != null) {
            tail = tail.next;
            len++;
        }

        k %= len;
        if (k == 0) {
            return head;
        }

        tail.next = head;                              // form a cycle
        int stepsToNewTail = len - k - 1;             // new head is one step after the new tail
        Node newTail = head;
        for (int step = 0; step < stepsToNewTail; step++) {
            newTail = newTail.next;
        }
        Node newHead = newTail.next;
        newTail.next = null;                          // break the cycle
        return newHead;
    }
}
