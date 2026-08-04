package jvm;

/**
 * Created by qingjuntian on 10/8/16.
 */
public class DaemonThread extends Thread {
    public static void main(String[] args) {
        System.out.println("main thread start");
        DaemonThread t = new DaemonThread();
//        t.setDaemon(false);
        t.start();

        try {
            Thread.sleep(3000);
        } catch (Exception e) {

        }
        System.out.println("main thread exit");
    }

    public void run() {
        while (true) {
            System.out.println("worker wake up");
            try {
                Thread.sleep(1000);
            } catch (Exception e) {

            }


        }
    }
}
