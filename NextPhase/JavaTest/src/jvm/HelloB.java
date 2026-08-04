package jvm;

/**
 * Created by qingjuntian on 8/8/16.
 */
class HelloA {
    private static final String name = "Name A";

    public HelloA() {
    }

    public String getName() {
        return name;
    }

    public void debug() {
        System.out.println(getName());
    }

    {
        System.out.println("I'm A class");
    }

    static {
        System.out.println("static A");
    }

}

public class HelloB extends HelloA {
    private static final String name = "Name B";

    public HelloB() {

    }

    public String getName() {
        return name;
    }

    public static void main(String[] args) throws Exception {
        HelloB b = new HelloB();
        b.debug();
    }

}
