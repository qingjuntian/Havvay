package puzzle.concurrency;
import puzzle.Puzzle;

/**
 * Probe how many threads the JVM/OS can create before resource exhaustion.
 * NOTE: Thread stress test, not an algorithm.
 */
public class ThreadNumber implements Puzzle {
    /**
     * Continuously create sleeping threads until the runtime refuses more of them.
     */
    @Override
    public void resolve() {
        int i = 0;

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
                            Thread.currentThread().interrupt();
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
