package thread;

/**
 * Created by qingjuntian on 11/2/16.
 */
public class ThreadLocalTest extends Thread {
    private static Index num = new Index();
    private static ThreadLocal<Index> local = new ThreadLocal<Index>() {
        @Override
        protected Index initialValue() {
            return num;
        }
    };

    public void run() {
        Index index = local.get();
        for (int i = 0; i < 10000; i++) {
            index.increase();
        }
        System.out.println(Thread.currentThread().getName() + " : " + index.num);
    }

    public static void main(String[] args) throws InterruptedException {
        Thread[] threads = new Thread[5];
        for (int j = 0; j < 5; j++) {
            threads[j] = new ThreadLocalTest();
        }
        for (Thread thread : threads) {
            thread.start();
        }
    }

    static class Index {
        int num;

        public void increase() {
            num++;
        }
    }
}
