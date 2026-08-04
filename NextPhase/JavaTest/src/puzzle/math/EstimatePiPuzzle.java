package puzzle.math;
import puzzle.Puzzle;

/**
 * Estimate Pi via Monte-Carlo sampling of random points in a unit quarter-circle (threaded variant included).
 * NOTE: The active resolve() path is dead-coded (early return); the estimation logic needs fixing.
 * Created by qingjuntian on 8/3/16.
 */
public class EstimatePiPuzzle extends Thread implements Puzzle {


    int NUM = 1000000;
    int total;

    public int getTotal() {
        return total;
    }

    @Override
    public void resolve() {
        try {
            System.out.println(String.format("PI is roughly %.4f", estimatePi()));
        } catch (Exception e) {

        }
    }

    @Override
    public void run() {
        for (int i = 0; i < NUM; i++) {
            double x = Math.random();
            double y = Math.random();
            if (x * x + y * y < 1) {
                total++;
            }
        }
    }

    private <T extends Comparable> int compare(T a, T b) {
        return b.compareTo(a);
    }

    private double estimatePi() throws InterruptedException {
        if (true) {
            return compare("helloa", "helloacb");
        }

        if (false) {
            return estimatePi_B();
        }

        for (int i = 0; i < NUM * 10; i++) {
            double x = Math.random();
            double y = Math.random();
            if (x * x + y * y < 1) {
                total++;
            }
        }

        return 4.0 * total / (NUM * 10);
    }

    private double estimatePi_B() throws InterruptedException {

        EstimatePiPuzzle[] threads = new EstimatePiPuzzle[10];
        for (int i = 0; i < 10; i++) {
            threads[i] = new EstimatePiPuzzle();
        }
        for (Thread t : threads) {
            t.start();
            t.join();
        }

        int sum = 0;
        for (EstimatePiPuzzle t: threads) {
            sum += t.getTotal();
        }

        return 4.0 * sum / (NUM * 10);
    }
}
