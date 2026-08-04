package puzzle.math;
import puzzle.Puzzle;

/**
 * Estimate Pi via Monte-Carlo sampling of random points in a unit quarter-circle (threaded variant included).
 * estimatePi: single-threaded (NUM*10 samples). estimatePi_B: 10 worker threads, then aggregate.
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
            System.out.println(String.format("PI (single-thread) is roughly %.4f", estimatePi()));
            System.out.println(String.format("PI (parallel)      is roughly %.4f", estimatePi_B()));
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

    private double estimatePi() throws InterruptedException {
        int samples = NUM * 10;
        int inside = 0;
        for (int i = 0; i < samples; i++) {
            double x = Math.random();
            double y = Math.random();
            if (x * x + y * y < 1) {
                inside++;
            }
        }
        return 4.0 * inside / samples;      // fraction of unit-square points inside the quarter circle is pi/4
    }

    private double estimatePi_B() throws InterruptedException {

        EstimatePiPuzzle[] threads = new EstimatePiPuzzle[10];
        for (int i = 0; i < 10; i++) {
            threads[i] = new EstimatePiPuzzle();
        }
        for (Thread t : threads) {
            t.start();                      // start all workers first ...
        }
        for (Thread t : threads) {
            t.join();                       // ... then wait for them -> they run in parallel
        }

        int sum = 0;
        for (EstimatePiPuzzle t: threads) {
            sum += t.getTotal();
        }

        return 4.0 * sum / (NUM * 10);
    }
}
