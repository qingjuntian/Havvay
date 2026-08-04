package reflection.stub.impl;

import reflection.stub.History;
import reflection.stub.ReturnValueStrategy;
import reflection.stub.WrappedException;

import java.lang.reflect.Method;
import java.lang.reflect.Proxy;

/**
 * Created by qingjuntian on 8/3/16.
 */
public class DefaultReturnValueStrategy implements ReturnValueStrategy {
    public Object getReturnValue(Proxy p, Method m, Object[] args, History h)
            throws WrappedException {
        if (!m.getReturnType().isPrimitive()) {
            try {
                return m.getReturnType().newInstance();
            } catch (InstantiationException e) {
                return null;
            } catch (IllegalAccessException e) {
                return null;
            }
        } else if (m.getReturnType() == void.class) {
            return null;
        } else if (m.getReturnType() == boolean.class) {
            return new Boolean(false);
        } else if (m.getReturnType() == short.class) {
            return new Short((short) 0);
        } else if (m.getReturnType() == int.class) {
            return new Integer(0);
        } else if (m.getReturnType() == long.class) {
            return new Long(0);
        } else if (m.getReturnType() == double.class) {
            return new Double(0);
        } else if (m.getReturnType() == byte.class) {
            return new Byte((byte) 0);
        } else if (m.getReturnType() == char.class) {
            return new Character((char) 0);
        } else if (m.getReturnType() == float.class) {
            return new Float(0);
        }
        throw new Error("Unknown return type: " + m.getReturnType());
    }
}
