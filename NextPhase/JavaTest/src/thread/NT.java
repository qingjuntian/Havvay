package thread;

/**
 * Created by qingjuntian on 8/6/16.
 */
public class NT {

    public void main(String[] args) {
        new Thread(new Runnable() {
            @Override
            public void run() {
                System.out.println("aaa");
            }
        }).start();
    }
}
