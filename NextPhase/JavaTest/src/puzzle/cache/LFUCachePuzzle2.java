package puzzle.cache;
import puzzle.Puzzle;

import java.util.HashMap;
import java.util.LinkedHashSet;
import java.util.Map;

/**
 * Implement an LFU cache (string-keyed variant with cleaned-up bucket insertion).
 * LeetCode: LFU Cache
 * Approach: Same frequency-bucket linked-list design as LFUCachePuzzle.
 * Complexity: Time ~O(1) amortized, Space O(n).
 */
public class LFUCachePuzzle2 implements Puzzle {

    @Override
    public void resolve() {
        LFUCache2 lfuCache = new LFUCache2(2);

        lfuCache.set("A", "1");
        lfuCache.set("B", "2");
        lfuCache.get("A");
        lfuCache.get("A");
        lfuCache.get("A");
        lfuCache.get("A");
        lfuCache.get("B");
        lfuCache.set("C", "Overflow");
        System.out.println(lfuCache.get("A"));
        System.out.println(lfuCache.get("B"));
        System.out.println(lfuCache.get("C"));
    }

    class LFUCache2 {
        int  cap;
        Node head = null;
        Map<String, String> valueHash;
        Map<String, Node> nodeHash;

        public LFUCache2(int capacity) {
            this.cap = capacity;
            valueHash = new HashMap<>();
            nodeHash = new HashMap<>();
        }

        public String get(String key) {
            if (valueHash.containsKey(key)) {
                increaseCount(key);
                return valueHash.get(key);
            }
            return null;
        }

        public void set(String key, String value) {
            if (cap == 0) return;

            if (valueHash.containsKey(key)) {
                valueHash.put(key, value);
            } else {
                if (valueHash.size() < cap) {
                    valueHash.put(key, value);
                } else {
                    removeOld();
                    valueHash.put(key, value);
                }
                addToHead(key);
            }
            increaseCount(key);
        }

        private void addToHead(String key) {
            if (head == null) {
                head = new Node(0);
                head.keys.add(key);
            } else if (head.count > 0) {
                Node h = new Node(0);
                h.keys.add(key);
                h.next = head;
                head.prev = h;
                head = h;
            } else {
                head.keys.add(key);
            }
            nodeHash.put(key, head);
        }

        private void increaseCount(String key) {
            Node node = nodeHash.get(key);
            node.keys.remove(key);

            if (node.next == null) {
                node.next = new Node(node.count + 1);
                node.next.prev = node;
                node.next.keys.add(key);
            } else if (node.next.count == node.count + 1) {
                node.next.keys.add(key);
            } else {
                Node temp = new Node(node.count + 1);
                temp.keys.add(key);
                temp.next = node.next;
                temp.prev = node;
                node.next = temp;
                temp.next.prev = temp;
            }
            nodeHash.put(key, node.next);
            if (node.keys.size() == 0) remove(node);
        }

        private void removeOld() {
            if (head == null) return;
            String old = null;
            for (String n : head.keys) {
                old = n;
                break;
            }
            head.keys.remove(old);
            if (head.keys.size() == 0) remove(head);
            nodeHash.remove(old);
            valueHash.remove(old);
        }

        private void remove(Node node) {
            if (node.prev == null) {
                head = node.next;
            } else {
                node.prev.next = node.next;
            }
            if (node.next != null) {
                node.next.prev = node.prev;
            }
        }
    }

    class Node {
        public int count = 0;
        public LinkedHashSet<String> keys = null;
        public Node prev = null, next = null;

        public Node(int count) {
            this.count = count;
            keys = new LinkedHashSet<String>();
            prev = next = null;
        }
    }
}
