package puzzle.linkedlist;
import puzzle.Puzzle;

import model.Node;

/**
 * Small harness for linked-list helper operations defined on {@link Node}.
 * <p>
 * This class is intentionally lightweight: it builds a sample list, prints it,
 * and demonstrates the "last n-th node" lookup helper.
 */
public class LinkedListPuzzle implements Puzzle {
    /**
     * Construct a six-node list and invoke the helper demo methods on it.
     */
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
    }
}
