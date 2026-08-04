package puzzle.linkedlist;
import puzzle.Puzzle;

import model.Node;

import java.util.*;

/**
 * Swap every two adjacent nodes in a linked list.
 * LeetCode: Swap Nodes in Pairs
 * Approach: Iterative pointer rewiring with a dummy head (also includes a recursive reverse-k-group).
 * Complexity: Time O(n), Space O(1).
 */
public class SwapPairNode implements Puzzle {

    public class ListNode {
        int val;
        ListNode next;

        ListNode(int x) {
            val = x;
        }
    }

    @Override
    public void resolve() {
        ListNode head = new ListNode(1);
        head.next = new ListNode(2);
        head.next.next = new ListNode(3);
        head.next.next.next  = new ListNode(4);
        head.next.next.next.next  = new ListNode(5);
        head = reverseKGroup(head, 0);
        int a = 0;
    }


    public ListNode reverseKGroup(ListNode head, int k) {
        int step = 0;
        ListNode cur = head;
        while (cur != null && step < k) {
            step++;
            cur = cur.next;
        }
        if (step < k) {
            return head;
        } else {
            ListNode ret  = reverseKGroup(cur, k);
            for (int i = 0; i < k; i++) {
                ListNode n = head;
                head = head.next;
                n.next = ret;
                ret = n;
            }
            return ret;
        }
    }

    public ListNode swapPairs(ListNode head) {
        ListNode dummy = new ListNode(0);
        ListNode tail = dummy;
        if (head == null || head.next == null) return head;
        while (head != null && head.next != null) {
            tail.next = head.next;
            ListNode temp = head.next.next;
            head.next.next = head;
            tail = head;
            head.next = temp;
            head = temp;
        }
        return dummy.next;
    }


}
