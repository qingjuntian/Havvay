package puzzle.linkedlist;
import puzzle.Puzzle;

import model.Node;

import java.util.*;

/**
 * Harness that builds a linked list and exercises helper methods (e.g., last-n node).
 * NOTE: Usage demo, not a solved puzzle.
 * Created by qingjuntian on 7/28/16.
 */
public class LinkedListPuzzle implements Puzzle {



    @Override
    public void resolve() {
        Node root = new Node(1);
        root = root.addNode(2);
        root = root.addNode(3);
        root = root.addNode(4);
        root = root.addNode(5);
        root = root.addNode(6);

        root.debug();
        root.lastN(5);

        Deque stack = new LinkedList();
    }
}
