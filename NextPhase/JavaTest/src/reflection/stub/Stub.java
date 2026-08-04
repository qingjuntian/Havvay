package reflection.stub;

import java.io.Serializable;

/**
 * Created by qingjuntian on 8/3/16.
 */
public interface Stub extends Serializable {
    /**
     * Returns the history object for the stub.
     */
    History getHistory( );
}