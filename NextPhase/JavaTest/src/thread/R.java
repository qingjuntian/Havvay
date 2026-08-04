package thread;

/**
 * Created by qingjuntian on 8/3/16.
 */
public class R implements Runnable {
    int i;
    private static final Object obj = new Object();
    private static boolean b = false;

    R(int i) {
        this.i = i;
    }

    public void run() {
        try {
            synchronized (obj) {
                while (!b) {
                    System.out.println("线程->  " + i + " 等待中");
                    obj.wait();
                }
                b = false;
                System.out.println("线程->  " + i + " 在运行了");
                Thread.sleep(2000);
            }
        } catch (Exception e) {
            e.printStackTrace();
        }
    }

    public static void test() {
        try {
            Thread[] rs = new Thread[10];
            for (int i = 0; i < 10; i++) {
                rs[i] = new Thread(new R(i));
            }
            for (Thread r : rs) {
                r.start();
            }
            while (true) {
                Thread.sleep(2000);
                synchronized (obj) {
                    b = true;
                    obj.notifyAll();
                }
            }
        } catch (Exception e) {
            e.printStackTrace();
        }
    }
}
