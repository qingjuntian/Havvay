package puzzle.math;
import puzzle.Puzzle;

import java.util.BitSet;

/**
 * Demo of Java BitSet operations (set / get / size).
 * <p>
 * This is a library-usage example rather than an interview algorithm. It shows
 * that {@link BitSet} grows on demand and supports sparse indexed access.
 */
public class BitSetTest implements Puzzle {
    /**
     * Toggle a few sparse positions and print representative reads plus the internal capacity.
     */
    @Override
    public void resolve() {
        BitSet bitSet = new BitSet(200);

        bitSet.set(1, true);
        bitSet.set(195, true);
        bitSet.set(255, true);
        System.out.println(bitSet.get(1));
        System.out.println(bitSet.get(196));
        System.out.println(bitSet.get(195));
        System.out.println(bitSet.size());
    }
}