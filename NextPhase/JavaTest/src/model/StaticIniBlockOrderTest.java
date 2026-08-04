package model;

/**
 * Created by qingjuntian on 8/25/16.
 */
class Parent {
    static {

    } {

    }

    {
        System.out.println("parent block");
    }

    static {
        System.out.println("parent static block");
    }

    public Parent() {
        System.out.println("parent constructor");
    }
}

class Child extends Parent {
    static Child c = new  Child();
    {
        System.out.println("child block");
    }
    static {
        System.out.println("child static block");
    }
    public Child() {
        System.out.println("child constructor");
    }


    public static void main(String[] args) throws Exception{
        System.out.println();
        new Child();
    }
}