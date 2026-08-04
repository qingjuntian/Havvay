package reflection;

import java.lang.reflect.Field;
import java.lang.reflect.InvocationHandler;
import java.lang.reflect.Proxy;

/**
 * Created by qingjuntian on 8/3/16.
 */
public abstract class InvocationHandlerBase implements InvocationHandler {

    protected Object nextTarget;
    protected Object realTarget = null;

    public InvocationHandlerBase(Object target) {
        nextTarget = target;
        if (nextTarget != null) {
            realTarget = findRealTarget(nextTarget);
            if (realTarget == null) {
                throw new RuntimeException("findRealTarget failure.");
            }
        }
    }

    protected Object getRealTarget() {
        return realTarget;
    }

    protected Object findRealTarget(Object t) {
        if (!Proxy.isProxyClass(t.getClass()))
            return t;
        InvocationHandler ih = Proxy.getInvocationHandler(t);
        if (InvocationHandlerBase.class.isInstance(ih)) {
            return ((InvocationHandlerBase) ih).getRealTarget();
        } else {
            try {
                Field f = findField(ih.getClass(), "target");
                if (Object.class.isAssignableFrom(f.getType()) &&
                        !f.getType().isArray()) {
                    f.setAccessible(true); // suppress access checks
                    Object innerTarget = f.get(ih);
                    return findRealTarget(innerTarget);
                }

                return null;
            } catch (NoSuchFieldException e) {
                return null;
            } catch (SecurityException e) {
                return null;
            } catch (IllegalAccessException e) {
                return null;
            } // IllegalArgumentException cannot be raised

        }
    }

    public Field findField(Class cls, String name)
            throws NoSuchFieldException {
        if (cls != null) {
            try {
                return cls.getDeclaredField(name);
            } catch (NoSuchFieldException e) {
                return findField(cls.getSuperclass(), name);
            }
        } else {
            throw new NoSuchFieldException();
        }
    }
}
