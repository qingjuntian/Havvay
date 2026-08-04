package puzzle.linkedlist; /**
 * Created by qingjuntian on 7/26/16.
 * Right spin the given list. For example given list is 1, 2, 3, 4, and given a number 3.
 * the return list should be 2, 3, 4, 1
 */

import puzzle.Puzzle;
import model.Node;

/**
 * Rotate a linked list to the right by k positions.
 * LeetCode: Rotate List
 * Approach: Form a cycle, walk to the new tail (k %= length), then break the cycle.
 * Complexity: Time O(n), Space O(1).
 */
public class RightSpinListPuzzle implements Puzzle {

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

    private Node rightSpin(Node head, int i) {
        if (head == null || head.next == null || i <= 0) {
            return head;
        }

        Node node = head;
        int num = 1;
        while (node.next != null) {
            node = node.next;
            num++;
        }

        i = (i - 1) % num;
        node.next = head;

        for (int k = 0; k < i; k++) {
            head = head.next;
        }

        Node next = head.next;
        head.next = null;

        return next;
    }

}
