package reflection.stub;

import java.lang.reflect.Method;
import java.lang.reflect.Proxy;

/**
 * Created by qingjuntian on 8/3/16.
 */
public interface History extends java.io.Serializable {
    long recordMethodCall( Proxy p, Method m, Object[] args );
    void recordReturnValue( long callID, Object returnValue );
    void recordException( long callID, Throwable cause );
}
