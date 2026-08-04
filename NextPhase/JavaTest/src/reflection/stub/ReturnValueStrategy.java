package reflection.stub;

import java.lang.reflect.Method;
import java.lang.reflect.Proxy;

/**
 * Created by qingjuntian on 8/3/16.
 */
public interface ReturnValueStrategy {
    /**
     * Note that getReturnValue is expected to produce the return values
     * for calls to Object.equals, Object.toString, and Object.hashCode.
     */
    Object getReturnValue(Proxy p, Method m, Object[] args, History h)
            throws WrappedException;
}
