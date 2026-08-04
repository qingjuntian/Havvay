package reflection.stub.impl;

import reflection.stub.History;

import java.lang.reflect.Method;
import java.lang.reflect.Proxy;

/**
 * Created by qingjuntian on 8/3/16.
 */
public class DefaultHistory implements History {

    public long recordMethodCall(Proxy p, Method m, Object[] args) {
        return 0;
    }

    public void recordReturnValue(long callID, Object returnValue) {
    }

    public void recordException(long callID, Throwable cause) {
    }
}
