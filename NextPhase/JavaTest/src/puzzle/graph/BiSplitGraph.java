package puzzle.graph;
import puzzle.Puzzle;

import java.util.ArrayDeque;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.Deque;
import java.util.List;

/**
 * Determine whether an undirected graph is bipartite (2-colorable), and if so print one valid split.
 * LeetCode: Is Graph Bipartite?
 * Approach: Build an adjacency list, then BFS-color every connected component. Each edge must connect
 * opposite colors; if a conflict appears, the graph is not bipartite. Otherwise the two color sets
 * are the required split.
 * Complexity: Time O(V+E), Space O(V+E) for the adjacency list.
 * Created by qingjuntian on 7/20/16.
 */
public class BiSplitGraph implements Puzzle {

    enum Color {
        BLACK, WHITE, UNKNOWN;
    }

    /**
     * A vertex plus its assigned bipartite color.
     */
    class Vertex {
        int id;
        Color color;
        Vertex(int id) {
            this.id = id;
            this.color = Color.UNKNOWN;
        }
    }

    /**
     * Simple undirected edge used only to build the adjacency list for the demo graph in resolve().
     */
    class Edge {
        Vertex a;
        Vertex b;

        Edge(Vertex a, Vertex b) {
            this.a = a;
            this.b = b;
        }
    }


    @Override
    public void resolve() {
        Vertex[] vetexes = new Vertex[10];
        for (int i = 0; i < 10; i++) {
            vetexes[i] = new Vertex(i);
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

    /**
     * Color every connected component by BFS and print the two parts if successful.
     */
    private void splitGraph(Vertex[] vetexes, Edge[] edges) {
        if (!isBipartite(vetexes, edges)) {
            System.out.println("the input graph could not be split into two parts");
            return;
        }

        Arrays.stream(vetexes).filter(v -> v.color == Color.BLACK).forEach(v -> System.out.print(v.id + "\t"));
        System.out.println();
        Arrays.stream(vetexes).filter(v -> v.color == Color.WHITE).forEach(v -> System.out.print(v.id + "\t"));
    }

    /**
     * Return true iff the graph is bipartite. Colors are written back into the vertex array.
     */
    private boolean isBipartite(Vertex[] vetexes, Edge[] edges) {
        List<Vertex>[] graph = buildGraph(vetexes, edges);
        Deque<Vertex> queue = new ArrayDeque<>();
        for (Vertex vetex : vetexes) {
            if (vetex.color != Color.UNKNOWN) continue;
            vetex.color = Color.BLACK;
            queue.offer(vetex);
            while (!queue.isEmpty()) {
                Vertex v = queue.poll();
                Color nextColor = (v.color == Color.BLACK) ? Color.WHITE : Color.BLACK;
                for (Vertex peer : graph[v.id]) {
                    if (peer.color == Color.UNKNOWN) {
                        peer.color = nextColor;
                        queue.offer(peer);
                    } else if (peer.color != nextColor) {
                        return false;
                    }
                }
            }
        }
        return true;
    }

    /**
     * Build adjacency lists from the demo edge list so each BFS step touches only true neighbors.
     */
    private List<Vertex>[] buildGraph(Vertex[] vetexes, Edge[] edges) {
        List<Vertex>[] graph = new ArrayList[vetexes.length];
        for (int i = 0; i < vetexes.length; i++) {
            graph[i] = new ArrayList<>();
        }
        for (Edge edge : edges) {
            if (edge == null) continue;
            graph[edge.a.id].add(edge.b);
            graph[edge.b.id].add(edge.a);
        }
        return graph;
    }
}
