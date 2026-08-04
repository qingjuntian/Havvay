package reflection;

import java.lang.reflect.Method;
import java.lang.reflect.Proxy;

/**
 * Created by qingjuntian on 8/3/16.
 */
public class SynchronizedIH extends InvocationHandlerBase {

    public SynchronizedIH(Object target) {
        super(target);
    }

    public static Object createProxy( Object obj ) {
        return Proxy.newProxyInstance(obj.getClass().getClassLoader(),
                obj.getClass().getInterfaces(),
                new SynchronizedIH(obj));
    }

    public Object invoke( Object proxy, Method method, Object[] args )
            throws Throwable
    {
        Object result = null;
        synchronized ( this.getRealTarget() ) {
            result = method.invoke( nextTarget, args );
        }
        return result;
    }
}
