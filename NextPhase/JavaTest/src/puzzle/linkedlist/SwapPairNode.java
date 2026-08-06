package puzzle.linkedlist;
import puzzle.Puzzle;

/**
 * Swap every two adjacent nodes in a linked list.
 * LeetCode: Swap Nodes in Pairs
 * Approach: Iterative pointer rewiring with a dummy head (also includes a recursive reverse-k-group).
 * Complexity: Time O(n), Space O(1).
 */
public class SwapPairNode implements Puzzle {

    /**
     * Minimal singly linked-list node used by the pair-swap / k-group-reverse demos.
     */
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
        printList("swapPairs", swapPairs(copyList(head)));
        printList("reverseKGroup k=3", reverseKGroup(copyList(head), 3));
    }


    /**
     * Reverse the list in groups of size k. If the remaining tail contains fewer than k nodes,
     * that tail is left unchanged.
     */
    public ListNode reverseKGroup(ListNode head, int k) {
        if (head == null || k <= 1) return head;   // k=0 would recurse forever; k=1 means no change
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

    /**
     * Swap every two adjacent nodes in-place using a dummy head and iterative pointer rewiring.
     */
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

    /**
     * Defensive copier so the pair-swap and k-group demos can run independently on the same input.
     */
    private ListNode copyList(ListNode head) {
        if (head == null) return null;
        ListNode dummy = new ListNode(0);
        ListNode tail = dummy;
        while (head != null) {
            tail.next = new ListNode(head.val);
            tail = tail.next;
            head = head.next;
        }
        return dummy.next;
    }

    /**
     * Print one linked list in a readable a -> b -> c format.
     */
    private void printList(String title, ListNode head) {
        System.out.print(title + ": ");
        while (head != null) {
            System.out.print(head.val);
            head = head.next;
            if (head != null) System.out.print(" -> ");
        }
        System.out.println();
    }


}
