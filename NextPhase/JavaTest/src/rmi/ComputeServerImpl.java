package rmi;

import java.rmi.RemoteException;
import java.rmi.server.UnicastRemoteObject;
import java.util.ArrayList;
import java.util.List;

/**
 * Created by qingjuntian on 6/1/16.
 */
public class ComputeServerImpl extends UnicastRemoteObject implements ComputeServer {
    protected ComputeServerImpl() throws RemoteException {
    }

    @Override
    public Object compute(Task task) throws RemoteException {
        return task.run();
    }

    public static List<Integer> dfs(boolean[] visited, int[] inDegree, List<Integer>[] outDegree, int i) {
        List<Integer> ret = new ArrayList<>();
        ret.add(i);
        visited[i] = true;
        if (outDegree[i] != null) {
            for (int o : outDegree[i]) {
                inDegree[o]--;
                if (inDegree[o] == 0 && visited[o] == false) {
                    ret.addAll(dfs(visited, inDegree, outDegree, o));
                }
            }
        }
        return ret;
    }


    public static boolean canFinish(int numCourses, int[][] prerequisites) {
        if (prerequisites == null || prerequisites.length == 0) return true;

        int[] inDegree = new int[numCourses];
        boolean[] visited = new boolean[numCourses];
        List<Integer>[] outDegree = new List[numCourses];
        for (int[] prereq : prerequisites) {
            inDegree[prereq[0]]++;
            if (outDegree[prereq[1]] == null) {
                outDegree[prereq[1]] = new ArrayList();
            }
            outDegree[prereq[1]].add(prereq[0]);
        }


        List<Integer> out = new ArrayList<>();
        while (out.size() < numCourses) {
            List<Integer> continu = new ArrayList<>();
            for (int i = 0; i < numCourses; i++) {
                if (inDegree[i] == 0 && visited[i] == false) {
                    continu.addAll(dfs(visited, inDegree, outDegree, i));
                }
            }
            if (continu.size() == 0) {
                break;
            }
            out.addAll(continu);
        }
        if (out.size() == numCourses) {
            Integer[] ret = new Integer[numCourses];
            out.toArray(ret);
        }
        return false;

    }

    public static void main(String[] args) throws Exception {

        int[][] r = new int[2][];
        r[0] = new int[]{1, 0};
        r[1] = new int[]{2, 0};

        System.out.println(canFinish(3, r));

        // use the default, restrictive security manager
//        System.setProperty("java.security.policy", "file:////Users/qingjuntian/workspace/JavaTest/sec.policy");
//        System.setProperty("java.rmi.server.hostname", "127.0.0.1");
//        System.setSecurityManager(new SecurityManager());
//        ComputeServer server = new ComputeServerImpl();
//        Naming.rebind("ComputeServer", server);
//        System.out.println("Ready to receive tasks");
        return;
    }
}
