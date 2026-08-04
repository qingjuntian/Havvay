package model;

/**
 * Created by qingjuntian on 8/3/16.
 */
public class Node {
    public int id;
    public Node next;
    public Node pre;
    public int lc;
    public int rc;

    public Node(int id) {
        this.id = id;
    }

    public Node addNode(int newValue) {
        Node newNode = new Node(newValue);
        this.next = newNode;
        newNode.pre = this;
        return newNode;
    }

    public Node addNode(int flag, int i) {
        Node n = addNode(flag + i);
        n.lc = flag;
        n.rc = i;
        return n;
    }

    public void lastN(int n) {
        if (n <= 0) return;

        int step = 0;
        Node fast = this, slow = this;
        while (step < n && fast != null) {
            fast = fast.next;
            step ++ ;
        }
        while (fast != null) {
            fast = fast.next;
            slow = slow.next;
        }

        slow.debug();
    }


    public Node reverse() {
        Node head = this;
        Node next =head.next;
        head.next = null;
        while (next != null) {
            Node temp = next.next;
            next.next = head;
            head = next;
            next = temp;
        }
        return head;
    }

    public void debug() {
        Node head = this;
        while (head != null) {
            System.out.println(head.id);
            head = head.next;
        }
        System.out.println();
    }

}
