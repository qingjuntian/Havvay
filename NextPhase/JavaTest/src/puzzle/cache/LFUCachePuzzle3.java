package puzzle.cache;
import puzzle.Puzzle;

import java.util.HashMap;
import java.util.Map;

/**
 * Compare LRU vs LFU eviction under a single abstract cache skeleton.
 * Approach: A single abstract cache skeleton stores values plus one per-key metric map. Concrete
 * subclasses interpret that metric either as recency (LRU) or frequency (LFU), then evict the key
 * with the minimum metric by scanning the whole map.
 * Complexity: Time O(n) eviction, Space O(n).
 */
public class LFUCachePuzzle3 implements Puzzle {

    @Override
    public void resolve() {
        Cache3<String, String> cache = new LRUCache(2);

        cache.set("A", "1");
        cache.set("B", "2");
        cache.get("A");
        cache.get("A");
        cache.get("A");
        cache.get("A");
        cache.get("B");
        cache.set("C", "Overflow");
        System.out.println(cache.get("A"));
        System.out.println(cache.get("B"));
        System.out.println(cache.get("C"));
    }


    abstract class Cache3<K, V> {
        int cap;
        Map<K, V> valueHash;
        Map<K, Integer> accessMap;

        /**
         * Create a cache skeleton of fixed capacity.
         */
        public Cache3(int capacity) {
            this.cap = capacity;
            valueHash = new HashMap<>();
            accessMap = new HashMap<>();
        }

        /**
         * Return the cached value or null if absent. Subclasses decide how the “access metric”
         * changes after a successful read.
         */
        public V get(K key) {
            if (valueHash.containsKey(key)) {
                increaseAccess(key);
                return valueHash.get(key);
            }
            return null;
        }

        /**
         * Insert or update one entry. On overflow, subclasses choose the eviction victim via
         * {@link #removeOld()}.
         */
        public void set(K key, V value) {
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
            }
            increaseAccess(key);
        }


        /**
         * Update the subclass-specific metric for a successful access or insertion.
         */
        abstract void increaseAccess(K key);

        /**
         * Evict one old entry according to the subclass-specific metric.
         */
        abstract void removeOld();
    }

    /**
     * LRU variant: the access metric is an ever-increasing timestamp. The smallest timestamp is the
     * least recently used key, so eviction scans for the minimum timestamp.
     */
    class LRUCache<K, V> extends Cache3<K, V> {

        public LRUCache(int capacity) {
            super(capacity);
        }

        @Override
        void increaseAccess(K key) {
            int latest = Integer.MIN_VALUE;
            for (Map.Entry<K, Integer> entry : accessMap.entrySet()) {
                latest = Math.max(latest, entry.getValue());
            }
            accessMap.put(key, latest + 1);
        }

        @Override
        void removeOld() {
            int least = Integer.MAX_VALUE;
            K key = null;
            for (Map.Entry<K, Integer> entry : accessMap.entrySet()) {
                if (least > entry.getValue()) {
                    least = entry.getValue();
                    key = entry.getKey();
                }
            }
            if (key != null) {
                valueHash.remove(key);
                accessMap.remove(key);
            }
        }

    }

    /**
     * LFU variant: the access metric is plain frequency count. The lowest frequency key is evicted.
     * This keeps the code shape simple but still requires O(n) scanning to find the victim.
     */
    class LFUCache<K, V> extends Cache3<K, V> {

        public LFUCache(int capacity) {
            super(capacity);
        }

        @Override
        void increaseAccess(K key) {
            if (accessMap.containsKey(key)) {
                accessMap.put(key, 1 + accessMap.get(key));
            } else {
                accessMap.put(key, 1);
            }
        }

        @Override
        void removeOld() {
            int least = Integer.MAX_VALUE;
            K toRemove = null;
            for (Map.Entry<K, Integer> entry : accessMap.entrySet()) {
                if (entry.getValue() < least) {
                    least = entry.getValue();
                    toRemove = entry.getKey();
                }
            }
            if (toRemove != null) {
                valueHash.remove(toRemove);
                accessMap.remove(toRemove);

            }
        }
    }
}
