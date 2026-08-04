package puzzle.misc;
import puzzle.Puzzle;

import java.util.ArrayList;
import java.util.Collection;
import java.util.List;

/**
 * Demonstrate Java generics type erasure and overload resolution.
 * NOTE: Language-feature demo, not an algorithm (List<String> vs Collection<String> overloads collide after erasure).
 * Created by qingjuntian on 7/18/16.
 */
public class SugerPuzzle implements Puzzle {

    @Override
    public void resolve() {
        List<String> paramStr = new ArrayList<>();
        paramStr.add("hello");
        try {method(paramStr);} catch (Exception e){}
    }

//    private int method(List<String> param) throws Exception{
    private int method(Collection<String> param) throws Exception{
        System.out.println("String");
        return 1;
    }


    private boolean method(List<Integer> param) {

        System.out.println("Integer");
        return true;
    }

}
