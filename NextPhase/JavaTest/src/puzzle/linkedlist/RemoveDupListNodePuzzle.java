package puzzle.linkedlist;
import puzzle.Puzzle;

import model.Node;

/**
 * Remove all nodes with duplicate values from a sorted linked list, leaving only distinct values.
 * LeetCode: Remove Duplicates from Sorted List II
 * Approach: Single pass with a dummy head, skipping entire duplicate runs.
 * Complexity: Time O(n), Space O(1).
 */
public class RemoveDupListNodePuzzle implements Puzzle {

    /**
     * Remove duplicates from a tiny sorted sample list and print the remaining nodes.
     */
    @Override
    public void resolve() {
        Node head = new Node(1);
        head = head.addNode(1);

        Node ret = deleteDuplicates(head);
        if (ret != null) {
            ret.debug();
        }
    }

    /**
     * Remove every value that appears more than once from a sorted linked list, leaving only values
     * whose frequency is exactly 1.
     */
    public Node deleteDuplicates(Node head) {
        if (head == null || head.next == null) {
            return head;
        }
        Node dummy = new Node(0);
        dummy.next = head;
        Node tail = dummy;
        int val = head.id;
        boolean dup = false;
        while (head != null) {
            if (dup) {
                if (head.id == val) {
                    head = head.next;
                } else {
                    dup = false;
                }
            } else if (head.next != null && head.next.id == head.id) {
                dup = true;
                val = head.id;
            } else {
                tail.next = head;
                tail = head;
                head = head.next;
            }
        }
        tail.next = head;
        return dummy.next;
    }
}
