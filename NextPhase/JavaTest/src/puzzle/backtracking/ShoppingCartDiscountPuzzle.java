package puzzle.backtracking;
import puzzle.Puzzle;

import java.util.ArrayList;
import java.util.Arrays;
import java.util.Collection;
import java.util.Collections;
import java.util.HashMap;
import java.util.LinkedList;
import java.util.List;
import java.util.Map;

/**
 * Remove matching discount groups from a shopping cart to minimize the number of leftover items.
 * Approaches:
 *   helpCustomer         - plain recursive brute force over removable groups;
 *   helpCustomerMemoized - memoized search on the multiset state of the cart (faster).
 * Both preserve multiset semantics: a discount group consumes ONE occurrence per listed item.
 * Created by qingjuntian on 7/28/16.
 */
public class ShoppingCartDiscountPuzzle implements Puzzle {

    /**
     * A shopping cart treated as a multiset of goods. The same item id may appear more than once.
     */
    class Cart {
        Collection<Integer> goods = new LinkedList<>();

        /**
         * Remove ONE occurrence per requested item.
         */
        public void removeAll(Collection<Integer> items) {
            for (Integer item : items) {
                goods.remove(item);               // remove ONE occurrence per requested item (multiset semantics)
            }
        }

        /**
         * Add all items back to the cart.
         */
        public void addAll(Collection<Integer> items) {
            goods.addAll(items);
        }

        /**
         * Multiset containment check: the cart must contain at least as many copies of each item as
         * the requested discount group consumes.
         */
        public boolean containsAll(Collection<Integer> items) {
            Map<Integer, Integer> count = new HashMap<>();
            for (Integer good : goods) {
                count.put(good, count.getOrDefault(good, 0) + 1);
            }
            for (Integer item : items) {
                int left = count.getOrDefault(item, 0);
                if (left == 0) return false;
                count.put(item, left - 1);
            }
            return true;
        }

        /**
         * Append one item to the cart.
         */
        public void add(int i) {
            goods.add(i);
        }
    }

    @Override
    public void resolve(){
        Cart goods = initGoods();

        Collection<Collection<Integer>> discountGroup = initDiscountGroup();

        Collection<Integer> left = helpCustomer(goods, discountGroup);
        Collection<Integer> memoLeft = helpCustomerMemoized(initGoods(), discountGroup);
        System.out.println("brute-force left size: " + left.size());
        System.out.println("brute-force left goods: " + left);
        System.out.println("memoized left size: " + memoLeft.size());
        System.out.println("memoized left goods: " + memoLeft);
    }

    /**
     * Build the available discount groups used in the demo.
     */
    private Collection<Collection<Integer>> initDiscountGroup() {
        Collection<Collection<Integer>> dg = new ArrayList<>();
        Collection<Integer> discount = new ArrayList<>();
        discount.add(1); discount.add(2);discount.add(3);discount.add(4);discount.add(5);discount.add(6);
        dg.add(discount);

        discount = new ArrayList<>();
        discount.add(1); discount.add(2);discount.add(50);
        dg.add(discount);

        discount = new ArrayList<>();
        discount.add(1); discount.add(2);discount.add(3);discount.add(4);
        dg.add(discount);


        discount = new ArrayList<>();
        discount.add(5);discount.add(10); discount.add(20);discount.add(30);
        dg.add(discount);

        discount = new ArrayList<>();
        discount.add(5);discount.add(6); discount.add(10);discount.add(15);
        dg.add(discount);

        discount = new ArrayList<>();
        discount.add(20);discount.add(30);
        dg.add(discount);

        discount = new ArrayList<>();
        discount.add(20);discount.add(25); discount.add(30);
        dg.add(discount);

        return dg;
    }

    /**
     * Build the demo shopping cart.
     */
    private Cart initGoods() {
        Cart goods = new Cart();
        goods.add(1);
        goods.add(2);
        goods.add(3);
        goods.add(4);
        goods.add(5);
        goods.add(6);
        goods.add(5);
        goods.add(6);
        goods.add(7);
        goods.add(8);
        goods.add(10);
        goods.add(15);
        goods.add(20);
        goods.add(25);
        goods.add(30);
        return goods;
    }

    /**
     * Plain recursive search over all currently applicable discount groups.
     */
    private Collection<Integer> helpCustomer(Cart goods, Collection<Collection<Integer>> discountGroup) {
        Collection<Integer> leftGoods = new LinkedList<>();
        leftGoods.addAll(goods.goods);
        Collection<Collection<Integer>> availlableDg = dgAvaillable(goods, discountGroup);
        for (Collection<Integer> dg : availlableDg) {
            goods.removeAll(dg);
            Collection<Integer> left = helpCustomer(goods, discountGroup);
            if (left.size() < leftGoods.size()) {
                leftGoods = left;
            }
            goods.addAll(dg);
        }
        return leftGoods;
    }

    /**
     * Memoized search on the multiset state of the cart. This avoids recomputing the same residual
     * shopping cart reached through different discount-application orders.
     */
    private Collection<Integer> helpCustomerMemoized(Cart goods, Collection<Collection<Integer>> discountGroup) {
        List<Integer> catalog = buildCatalog(goods, discountGroup);
        Map<Integer, Integer> index = new HashMap<>();
        for (int i = 0; i < catalog.size(); i++) {
            index.put(catalog.get(i), i);
        }
        List<int[]> groups = encodeDiscountGroups(discountGroup, index, catalog.size());
        int[] state = encodeGoods(goods, index, catalog.size());
        Map<String, List<Integer>> memo = new HashMap<>();
        return solveMemo(state, groups, catalog, memo);
    }

    /**
     * Return the discount groups that are currently applicable to the cart.
     */
    private Collection<Collection<Integer>> dgAvaillable(Cart goods, Collection<Collection<Integer>> discountGroup) {
        Collection<Collection<Integer>> ret = new ArrayList<>();
        for (Collection<Integer> dg : discountGroup) {
            if (goods.containsAll(dg)) {
                ret.add(dg);
            }
        }
        return ret;
    }

    /**
     * Solve one memoized cart state and return the minimum-leftover multiset as a sorted list.
     */
    private List<Integer> solveMemo(int[] state, List<int[]> groups, List<Integer> catalog, Map<String, List<Integer>> memo) {
        String key = Arrays.toString(state);
        if (memo.containsKey(key)) {
            return memo.get(key);
        }

        List<Integer> best = stateToGoods(state, catalog);     // "use nothing more" baseline
        for (int[] group : groups) {
            if (!canApply(state, group)) continue;
            int[] next = state.clone();
            apply(next, group);
            List<Integer> candidate = solveMemo(next, groups, catalog, memo);
            if (candidate.size() < best.size()) {
                best = candidate;
            }
        }
        memo.put(key, best);
        return best;
    }

    /**
     * Return true iff the current cart state contains all counts required by the encoded group.
     */
    private boolean canApply(int[] state, int[] group) {
        for (int i = 0; i < state.length; i++) {
            if (state[i] < group[i]) return false;
        }
        return true;
    }

    /**
     * Subtract one encoded discount group from the encoded cart state.
     */
    private void apply(int[] state, int[] group) {
        for (int i = 0; i < state.length; i++) {
            state[i] -= group[i];
        }
    }

    /**
     * Encode the current cart multiset as counts aligned with the shared catalog order.
     */
    private int[] encodeGoods(Cart goods, Map<Integer, Integer> index, int size) {
        int[] state = new int[size];
        for (Integer good : goods.goods) {
            state[index.get(good)]++;
        }
        return state;
    }

    /**
     * Encode every discount group into the same count-vector space as the cart state.
     */
    private List<int[]> encodeDiscountGroups(Collection<Collection<Integer>> discountGroup, Map<Integer, Integer> index, int size) {
        List<int[]> ret = new ArrayList<>();
        for (Collection<Integer> dg : discountGroup) {
            int[] encoded = new int[size];
            for (Integer item : dg) {
                encoded[index.get(item)]++;
            }
            ret.add(encoded);
        }
        return ret;
    }

    /**
     * Build a stable sorted catalog of all item ids that can appear in the cart or in any discount
     * group, so every memo state has a consistent coordinate system.
     */
    private List<Integer> buildCatalog(Cart goods, Collection<Collection<Integer>> discountGroup) {
        Map<Integer, Boolean> values = new HashMap<>();
        for (Integer good : goods.goods) {
            values.put(good, true);
        }
        for (Collection<Integer> dg : discountGroup) {
            for (Integer item : dg) {
                values.put(item, true);
            }
        }
        List<Integer> catalog = new ArrayList<>(values.keySet());
        Collections.sort(catalog);
        return catalog;
    }

    /**
     * Convert one encoded count-vector state back into a sorted list of leftover item ids.
     */
    private List<Integer> stateToGoods(int[] state, List<Integer> catalog) {
        List<Integer> goods = new ArrayList<>();
        for (int i = 0; i < state.length; i++) {
            for (int cnt = 0; cnt < state[i]; cnt++) {
                goods.add(catalog.get(i));
            }
        }
        return goods;
    }
}
