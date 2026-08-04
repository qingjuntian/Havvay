package rmi;

import java.rmi.Remote;
import java.rmi.RemoteException;

/**
 * Created by qingjuntian on 6/1/16.
 */
public interface ComputeServer extends Remote {
    Object compute(Task task) throws RemoteException;

}
