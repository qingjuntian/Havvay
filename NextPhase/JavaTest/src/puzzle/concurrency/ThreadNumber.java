package puzzle.concurrency;
import puzzle.Puzzle;

/**
 * Probe how many threads the JVM/OS can create before resource exhaustion.
 * NOTE: Thread stress test, not an algorithm.
 * Created by qingjuntian on 6/29/16.
 */
public class ThreadNumber implements Puzzle {
    @Override
    public void resolve() {
        int i = 0;

        String s;

        try {
            while (true) {
                if (((++i) % 100) == 0) {
                    System.out.println(i);
                }
                Thread t = new Thread(new Runnable() {
                    @Override
                    public void run() {
                        try {
                            Thread.sleep(Long.MAX_VALUE);
                        } catch (InterruptedException e) {
                            e.printStackTrace();
                        }
                    }
                }, "Thread " + i);
                t.start();

            }
        } catch (Throwable e) {
            e.printStackTrace();
        }
        System.out.println(i);
    }
}
