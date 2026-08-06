package puzzle.cache;
import puzzle.Puzzle;

import java.util.HashMap;
import java.util.LinkedHashSet;

/**
 * Implement a Least-Frequently-Used (LFU) cache with get/set.
 * LeetCode: LFU Cache
 * Approach: Frequency buckets as a doubly linked list of nodes. Each node stores all keys with the
 * same access count in insertion order; two hash maps provide O(1)-style access from key->value and
 * key->current-bucket. The head bucket always represents the lowest frequency, so eviction removes
 * one key from head.keys.
 * Complexity: Time ~O(1) amortized, Space O(n).
 */
public class LFUCachePuzzle implements Puzzle {

    @Override
    public void resolve() {
        LFUCache lfuCache = new LFUCache(2);
        lfuCache.set(1, 1);
        lfuCache.set(2, 2);
        int result = lfuCache.get(1);
        lfuCache.set(3, 3);
        result = lfuCache.get(2);
        result = lfuCache.get(2);
        lfuCache.set(4, 4);
        result = lfuCache.get(1);
        System.out.println();
    }

    class LFUCache {
        private Node head = null;
        private int cap = 0;
        private HashMap<Integer, Integer> valueHash = null;
        private HashMap<Integer, Node> nodeHash = null;

        /**
         * Create an LFU cache with the given capacity.
         */
        public LFUCache(int capacity) {
            this.cap = capacity;
            valueHash = new HashMap<Integer, Integer>();
            nodeHash = new HashMap<Integer, Node>();
        }

        /**
         * Return the cached value, or -1 if missing. A successful read counts as one more access,
         * so the key is moved to the next higher-frequency bucket.
         */
        public int get(int key) {
            if (valueHash.containsKey(key)) {
                increaseCount(key);
                return valueHash.get(key);
            }
            return -1;
        }

        /**
         * Insert or update a value. On insert when full, evict one key from the lowest-frequency
         * bucket (head). New keys start in frequency bucket 0 and are then immediately promoted once
         * by increaseCount(), so their first visible frequency becomes 1.
         */
        public void set(int key, int value) {
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

        /**
         * Ensure there is a head bucket for frequency 0 and place the new key there before it is
         * promoted by increaseCount().
         */
        private void addToHead(int key) {
            if (head == null) {
                head = new Node(0);
                head.keys.add(key);
            } else if (head.count > 0) {
                Node node = new Node(0);
                node.keys.add(key);
                node.next = head;
                head.prev = node;
                head = node;
            } else {
                head.keys.add(key);
            }
            nodeHash.put(key, head);
        }

        /**
         * Move key from frequency c to c+1. If the c+1 bucket does not yet exist, create it in the
         * linked-list position directly after the current bucket. Remove the old bucket if it becomes
         * empty after the move.
         */
        private void increaseCount(int key) {
            Node node = nodeHash.get(key);
            node.keys.remove(key);

            if (node.next == null) {
                node.next = new Node(node.count + 1);
                node.next.prev = node;
                node.next.keys.add(key);
            } else if (node.next.count == node.count + 1) {
                node.next.keys.add(key);
            } else {
                Node tmp = new Node(node.count + 1);
                tmp.keys.add(key);
                tmp.prev = node;
                tmp.next = node.next;
                node.next.prev = tmp;
                node.next = tmp;
            }

            nodeHash.put(key, node.next);
            if (node.keys.size() == 0) remove(node);
        }

        /**
         * Evict one key from the current lowest-frequency bucket. LinkedHashSet preserves insertion
         * order inside a bucket, giving a deterministic tie-breaker among keys with the same count.
         */
        private void removeOld() {
            if (head == null) return;
            int old = 0;
            for (int n : head.keys) {
                old = n;
                break;
            }
            head.keys.remove(old);
            if (head.keys.size() == 0) remove(head);
            nodeHash.remove(old);
            valueHash.remove(old);
        }

        /**
         * Remove an empty frequency bucket from the doubly linked list.
         */
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

    /**
     * One frequency bucket in the LFU structure. All keys in {@code keys} share the same access
     * count. Buckets are ordered by count in the doubly linked list.
     */
    class Node {
        public int count = 0;
        public LinkedHashSet<Integer> keys = null;
        public Node prev = null, next = null;

        public Node(int count) {
            this.count = count;
            keys = new LinkedHashSet<Integer>();
            prev = next = null;
        }
    }
}
