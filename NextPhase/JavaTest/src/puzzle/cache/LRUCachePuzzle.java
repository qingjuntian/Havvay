package puzzle.cache;
import puzzle.Puzzle;

import java.util.HashMap;
import java.util.LinkedHashMap;
import java.util.Map;

/**
 * Implement a Least-Recently-Used (LRU) cache with O(1) get/put.
 * LeetCode: LRU Cache
 * Approach: LinkedHashMap with access-order enabled + removeEldestEntry for automatic eviction.
 * In this mode, every successful get/put on an existing key moves that entry to the logical tail
 * as the most recently used element; the eldest entry at the head is therefore the least recently
 * used element and the correct eviction candidate.
 * Complexity: Time O(1) avg, Space O(capacity).
 */
public class LRUCachePuzzle implements Puzzle {

    @Override
    public void resolve() {
        LRUCache<String, String> cache = new LRUCache(2);
        cache.put("A", "1");
        cache.put("B", "2");
        cache.get("A");
        cache.get("A");
        cache.get("A");
        cache.get("A");
        cache.get("B");
        cache.put("C", "Overflow");
        System.out.println(cache.get("A"));
        System.out.println(cache.get("B"));
        System.out.println(cache.get("C"));
    }



    class LRUCache<K, V> extends LinkedHashMap<K, V> {

        int capacity;

        /**
         * Create an LRU cache of fixed capacity.
         *
         * <p>The third argument ({@code true}) is the key switch: it tells LinkedHashMap to maintain
         * access order rather than insertion order, which is exactly what LRU needs.</p>
         */
        public LRUCache(int capacity) {
            super(capacity, 0.75F, true);
            this.capacity = capacity;
        }

        /**
         * Automatically evict the least-recently-used entry after a put if the cache size exceeds
         * capacity. Because access-order is enabled, {@code eldest} is the current LRU entry.
         */
        @Override
        protected boolean removeEldestEntry(Map.Entry<K,V> eldest) {
            return size() > capacity;
        }

    }
}
