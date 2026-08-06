package puzzle.graph;
import puzzle.Puzzle;

/**
 * Find the lowest common ancestor (LCA) of two nodes in a binary tree.
 * LeetCode: Lowest Common Ancestor of a Binary Tree
 * Approach: Postorder recursion. If the current root matches either target, return it upward. If both
 * children return non-null, then one target was found in each subtree and the current root is the LCA.
 * Complexity: Time O(n), Space O(h).
 * Created by qingjuntian on 6/4/16.
 */
public class TreeAncestor implements Puzzle {

    /**
     * Minimal binary-tree node used by the LCA demo.
     */
    private class TreeNode {
        int value;
        TreeNode left, right;

        public TreeNode(int value) {
            this.value = value;
        }
    }

    @Override
    public void resolve() {
        TreeNode root = createTestTree(0);

        TreeNode ancestor = lca(root, 3, 100);
        System.out.println(ancestor.value);
    }

    /**
     * Return the lowest common ancestor of the two target values in the binary tree rooted at
     * {@code root}. If one target is itself an ancestor of the other, that ancestor is returned.
     */
    private TreeNode lca(TreeNode root, int a, int b) {
        if (root == null) return null;
        if (root.value == a || root.value == b) return root;
        TreeNode l = lca(root.left, a, b);
        TreeNode r = lca(root.right, a, b);
        if (l == null) return r;
        if (r == null) return l;
        return root;
    }

    /**
     * Build a small complete binary tree for demonstration. Node values follow the usual heap-like
     * numbering rule: left = 2x+1, right = 2x+2, stopping once the value reaches 20.
     */
    private TreeNode createTestTree(int thisValue) {
        if (thisValue >= 20) {
            return null;
        }
        TreeNode root = new TreeNode(thisValue);
        root.left = createTestTree(thisValue * 2 + 1);
        root.right = createTestTree(thisValue * 2 + 2);
        return root;
    }
}
