package puzzle.misc;
import puzzle.Puzzle;

import java.util.ArrayList;
import java.util.Collection;
import java.util.List;

/**
 * Demonstrate Java generics type erasure and overload resolution.
 * NOTE: Language-feature demo, not an algorithm (List<String> vs Collection<String> overloads collide after erasure).
 */
public class SugerPuzzle implements Puzzle {

    /**
     * Call the surviving overload with a {@code List<String>} instance.
     */
    @Override
    public void resolve() {
        List<String> paramStr = new ArrayList<>();
        paramStr.add("hello");
        method(paramStr);
    }

    /**
     * Accept a string collection. Using {@code Collection<String>} instead of {@code List<String>}
     * avoids the type-erasure collision with {@link #method(List)}.
     */
    private int method(Collection<String> param) {
        System.out.println("String");
        return 1;
    }

    /**
     * Distinct overload because {@code List<Integer>} erases to a different raw signature than
     * {@code Collection<String>}.
     */
    private boolean method(List<Integer> param) {
        System.out.println("Integer");
        return true;
    }
}
