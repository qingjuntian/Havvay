package thread;

import java.util.Random;

/**
 * Created by qingjuntian on 11/15/16.
 */
public class VolatileTest {

    public static void main(String args[]) {

        Counter counter = new Counter();

        new writerThread("writeThread", counter).start();

        new ReaderThread("readThread", counter).start();
    }
}

class Counter {

    private volatile boolean flag = false;
    private int a = 0;


    public void write(int i) {
        flag = false;
        a = i;
        System.err.println(Thread.currentThread().getName() + " write :" + a);
        flag = true;
    }

    public void read() {

        if (flag) {
            int _a = a;
            try {
                Thread.sleep(3);
            } catch (Exception e) {}
            System.err.println(Thread.currentThread().getName() + " read :" + _a);
            flag = false;
        }

    }
}

class writerThread extends Thread {

    private Counter counter;

    Random random = new Random();

    public writerThread(String name, Counter counter) {

        super(name);

        this.counter = counter;
    }


    public void run() {

        for (int i = 0; true; i++) {

            counter.write(i);

            try {
                Thread.sleep(random.nextInt(5));
            } catch (InterruptedException e) {
// TODO Auto-generated catch block
                e.printStackTrace();
            }
        }
    }

}


class ReaderThread extends Thread {

    private Counter counter;

    Random random = new Random();

    public ReaderThread(String name, Counter counter) {

        super(name);

        this.counter = counter;
    }

    public void run() {

        while (true) {

            counter.read();

            try {
                Thread.sleep(3);
            } catch (InterruptedException e) {
// TODO Auto-generated catch block
                e.printStackTrace();
            }
        }
    }

}