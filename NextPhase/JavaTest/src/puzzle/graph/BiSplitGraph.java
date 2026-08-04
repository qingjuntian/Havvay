package puzzle.graph;
import puzzle.Puzzle;

import java.util.Arrays;
import java.util.Queue;
import java.util.concurrent.ConcurrentLinkedQueue;

/**
 * Determine whether an undirected graph is bipartite (2-colorable).
 * LeetCode: Is Graph Bipartite?
 * Approach: BFS coloring: neighbors get the opposite color; a conflict means not bipartite.
 * Complexity: Time O(V*E), Space O(V).
 * Created by qingjuntian on 7/20/16.
 */
public class BiSplitGraph implements Puzzle {

    enum Color {
        BLACK, WHITE, UNKNOW;
    }

    class Vetex {
        int id;
        Color color;
        Vetex(int id) {
            this.id = id;
            this.color = Color.UNKNOW;
        }
    }

    class Edge {
        Vetex a;
        Vetex b;

        Edge(Vetex a, Vetex b) {
            this.a = a;
            this.b = b;
        }

        public Vetex peerVetex(Vetex v) {

            if (this.a.id == v.id) {
                return b;
            }

            if (this.b.id == v.id) {
                return a;
            }

            return null;
        }
    }


    @Override
    public void resolve() {
        Vetex[] vetexes = new Vetex[10];
        for (int i = 0; i < 10; i++) {
            vetexes[i] = new Vetex(i);
        }

        Edge[] edges = new Edge[8];
        edges[0] = new Edge(vetexes[0], vetexes[1]);
        edges[1] = new Edge(vetexes[1], vetexes[5]);
        edges[2] = new Edge(vetexes[7], vetexes[2]);
        edges[3] = new Edge(vetexes[0], vetexes[6]);
        edges[4] = new Edge(vetexes[2], vetexes[8]);
        edges[5] = new Edge(vetexes[3], vetexes[5]);
        edges[6] = new Edge(vetexes[8], vetexes[3]);
        edges[7] = new Edge(vetexes[9], vetexes[6]);

        splitGraph(vetexes, edges);
    }

    private void splitGraph(Vetex[] vetexes, Edge[] edges) {
        Queue<Vetex> queue= new ConcurrentLinkedQueue<>();
        for (Vetex vetex : vetexes) {
            if (vetex.color == Color.UNKNOW) {
                vetex.color = Color.BLACK;
                queue.offer(vetex);
                while (queue.isEmpty() == false) {
                    Vetex v = queue.poll();
                    if (false == enqueueAdjacent(queue, v, edges)) {
                        System.out.println("the input graph could not be split into two parts");
                        return;
                    }
                }
            }
        }



        Arrays.stream(vetexes).filter(v -> v.color == Color.BLACK).forEach(v -> System.out.print(v.id + "\t"));
        System.out.println();
        Arrays.stream(vetexes).filter(v -> v.color == Color.WHITE).forEach(v -> System.out.print(v.id + "\t"));

    }

    private boolean enqueueAdjacent(Queue<Vetex> queue, Vetex v, Edge[] edges) {
        Color c = Color.BLACK;
        if (v.color == Color.BLACK) c = Color.WHITE;

        for (Edge edge : edges) {
            if(edge != null) {
                Vetex peer = edge.peerVetex(v);
                if (peer != null) {
                    if (peer.color == Color.UNKNOW) {
                        peer.color = c;
                        queue.offer(peer);
                    } else if (peer.color != c) {
                        return false;
                    }
                }
            }
        }
        return true;
    }
}
