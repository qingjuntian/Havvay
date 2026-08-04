import puzzle.*;
import puzzle.arrays.*;
import puzzle.strings.*;
import puzzle.dp.*;
import puzzle.backtracking.*;
import puzzle.binarysearch.*;
import puzzle.stack.*;
import puzzle.linkedlist.*;
import puzzle.graph.*;
import puzzle.cache.*;
import puzzle.sorting.*;
import puzzle.math.*;
import puzzle.concurrency.*;
import puzzle.misc.*;

/**
 * Created by qingjuntian on 10/30/15.
 */
public class TryMe {


    public static void main(String[] args) {
//        try {
//            byte[] buffer = new byte[1024];
//            int l = System.in.read(buffer);
//            String s = new String(buffer, 0, l, "UTF-8");
//
//            System.out.println(s);
//        } catch (UnsupportedEncodingException e) {
//            e.printStackTrace();
//        } catch (IOException e) {
//            e.printStackTrace();
//        } finally {
//            ;
//        }

        Puzzle puzzle = new MedianOfTwoSortedArray();
        long curr = System.currentTimeMillis();
        puzzle.resolve();
        System.out.println();
        System.out.println("time cost: " + (System.currentTimeMillis() - curr));
//
//        try {
//            Puzzle p = (Puzzle) SynchronizedIH.createProxy(TraceInvocationHandler.createProxey(puzzle));
//            boolean eq = p.equals(p);
//            p.resolve();
//        } catch (NoSuchMethodException e) {
//            e.printStackTrace();
//        } catch (IllegalAccessException e) {
//            e.printStackTrace();
//        } catch (InvocationTargetException e) {
//            e.printStackTrace();
//        } catch (InstantiationException e) {
//            e.printStackTrace();
//        }

//        Integer a = -129;
//        Integer b = -129;
//
//        System.out.println(a == b);
//
//        a = 127;
//        b = 127;
//
//        System.out.println(a == b);
//
//        estimatePi();


    }


}
