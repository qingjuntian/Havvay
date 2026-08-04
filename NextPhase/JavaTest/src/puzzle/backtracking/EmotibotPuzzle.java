package puzzle.backtracking;
import puzzle.Puzzle;

import java.util.ArrayList;
import java.util.Collection;
import java.util.LinkedList;

/**
 * Remove matching discount groups from a shopping cart to minimize the number of leftover items.
 * Approach: Recursive brute-force over all removable groups, keeping the best (smallest) leftover set.
 * Complexity: Time exponential, Space O(depth).
 * Created by qingjuntian on 7/28/16.
 */
public class EmotibotPuzzle implements Puzzle {

    class Cart {
        Collection<Integer> goods = new LinkedList<>();

        public void removeAll(Collection<Integer> items) {
            goods.removeAll(items);
        }

        public void addAll(Collection<Integer> items) {
            goods.addAll(items);
        }

        public boolean containsAll(Collection<Integer> items) {
            return goods.containsAll(items);
        }

        public void add(int i) {
            goods.add(i);
        }
    }

    @Override
    public void resolve(){
        Cart goods = initGoods();

        Collection<Collection<Integer>> discountGroup = initDiscountGroup();

        Collection<Integer> left = helpCustomer(goods, discountGroup);

        return;

    }

    private Collection<Collection<Integer>> initDiscountGroup() {
        Collection<Collection<Integer>> dg = new ArrayList<Collection<Integer>>();
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

    private Collection helpCustomer(Cart goods, Collection<Collection<Integer>> discountGroup) {
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

    private Collection<Collection<Integer>> dgAvaillable(Cart goods, Collection<Collection<Integer>> discountGroup) {
        Collection<Collection<Integer>> ret = new ArrayList<>();
        for (Collection<Integer> dg : discountGroup) {
            if (goods.containsAll(dg)) {
                ret.add(dg);
            }
        }
        return ret;
    }
}
