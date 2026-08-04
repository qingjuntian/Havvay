package model;

import java.util.Arrays;

/**
 * Created by qingjuntian on 7/8/16.
 */
public class AnimalImpl implements Animal {
    private int feetNum;

    public AnimalImpl(int feetNum) {
        this.feetNum = feetNum;
    }

    @Override
    public int getFeetNum() {
        return feetNum;
    }

    protected void sing(int voice){
        System.out.println("sing with voice: " + voice);
    }

    public static int getFeetNum(AnimalImpl[] animals) {
        return Arrays.stream(animals).mapToInt(a -> a.getFeetNum()).sum();
    }
}
