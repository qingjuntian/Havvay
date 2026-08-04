package model;

/**
 * Created by qingjuntian on 7/6/16.
 */
public class Student extends MammalsImpl implements Comparable<Student> {
    private String name;
    private int score;

    public Student(String name, int score) {
        super(2);
        this.name = name;
        this.score = score;
    }

    public void setName(String name) {
        this.name = name;
    }

    public String getName() {
        return this.name;
    }

    public void setScore(int score) {
        this.score = score;
    }

    public int getScore() {
        return this.score;
    }

    public String toString() {
        return this.name + " - " + this.score;
    }

    public int compareTo(Student another) {
        return another.getScore() - this.score;
    }
}