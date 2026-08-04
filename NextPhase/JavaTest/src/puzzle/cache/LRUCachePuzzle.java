package puzzle.cache;
import puzzle.Puzzle;

import java.util.HashMap;
import java.util.LinkedHashMap;
import java.util.Map;

/**
 * Implement a Least-Recently-Used (LRU) cache with O(1) get/put.
 * LeetCode: LRU Cache
 * Approach: LinkedHashMap with access-order enabled + removeEldestEntry for automatic eviction.
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

        public LRUCache(int capacity) {
            super(capacity, 0.75F, true);
            this.capacity = capacity;
        }

        @Override
        protected boolean removeEldestEntry(Map.Entry<K,V> eldest) {
            return size() > capacity;
        }

    }
}
