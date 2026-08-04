package puzzle.math;
import puzzle.Puzzle;

import java.util.BitSet;

/**
 * Demo of Java BitSet operations (set / get / size).
 * NOTE: API demo, not an algorithm puzzle.
 * Created by qingjuntian on 7/3/16.
 */
public class BitSetTest implements Puzzle {
    @Override
    public void resolve() {
        BitSet bitSet = new BitSet(200);

        bitSet.set(1, true);
        bitSet.set(195, true);
        bitSet.set(255, true);
        boolean s = bitSet.get(1);
        s = bitSet.get(196);
        s = bitSet.get(195);
        System.out.println(bitSet.size());
    }
}