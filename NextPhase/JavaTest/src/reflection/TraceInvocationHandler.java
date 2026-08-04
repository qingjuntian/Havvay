package reflection;

import java.lang.reflect.*;

/**
 * Created by qingjuntian on 8/3/16.
 */
public class TraceInvocationHandler extends InvocationHandlerBase {


    public static Object createProxey(Object obj) throws NoSuchMethodException, IllegalAccessException, InvocationTargetException, InstantiationException {
        Class cl = Proxy.getProxyClass(obj.getClass().getClassLoader(), obj.getClass().getInterfaces());
        Constructor cons = cl.getConstructor(new Class[]{InvocationHandler.class});
        Object proxy = cons.newInstance(new Object[] {new TraceInvocationHandler(obj)});

        return proxy;

//        return Proxy.newProxyInstance(obj.getClass().getClassLoader(), obj.getClass().getInterfaces(), new TraceInvocationHandler(obj));
    }

    public TraceInvocationHandler(Object obj) {
        super(obj);
    }

    @Override
    public Object invoke(Object proxy, Method method, Object[] args) throws Throwable {
        return method.invoke(getRealTarget(), args);
    }
}
