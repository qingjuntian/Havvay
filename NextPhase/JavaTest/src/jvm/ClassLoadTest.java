package jvm;


import model.*;

import java.lang.reflect.Array;
import java.lang.reflect.Field;
import java.lang.reflect.Method;

public class ClassLoadTest {
    public static void main(String[] args) {
        try {
            AnimalImpl[] animals = new AnimalImpl[3];
            animals[0] = new Dog();
            animals[1] = new Student("Tommy", 89);
            animals[2] = new Fish();

            int feetNum = AnimalImpl.getFeetNum(animals);

//            Method[] methods = Dog.class.getSuperclass().getDeclaredMethods();

            Method singMethod = getSupportedMethod(Dog.class, "sing", new Class[] {int.class});
            singMethod.setAccessible(true);

            singMethod.invoke(animals[1], new Object[]{15});

            Class classes = Mammals.class.getSuperclass();

            Class claz =  Class.forName("[Ljava.lang.String;");
            int m = 6, n = 4;

            Object s = Array.newInstance(String.class, new int[] {m, n});
                s =    Array.newInstance(String[].class, new int[] {2, 3});

            Object o = Array.newInstance(claz, 6);

            boolean b = Mammals.class.isAssignableFrom(Animal.class);

            b= Class.class.isInstance(Class.class);
            b = Animal.class.isAssignableFrom(Mammals.class);

            b = Mammals.class.isInstance(animals[2]);
            b = Mammals.class.isInstance(animals[1]);
            b = Mammals.class.isInstance(animals[0]);

            for (Animal animal : animals) {
                serializeObject(animal);
            }

            System.out.println(feetNum);

        } catch (Exception e) {
            e.printStackTrace();
        }
    }

    private static void serializeObject(Object obj) {
        Field[] fields = obj.getClass().getDeclaredFields();
    }

    public static Method getSupportedMethod(Class cls,
                                            String name,
                                            Class[] paramTypes)
            throws NoSuchMethodException {
        if (cls == null) {
            throw new NoSuchMethodException();
        }
        try {
            return cls.getDeclaredMethod(name, paramTypes);
        } catch (NoSuchMethodException ex) {
            return getSupportedMethod(cls.getSuperclass(), name, paramTypes);
        }
    }
}