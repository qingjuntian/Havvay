package puzzle.graph;
import puzzle.Puzzle;

import java.util.ArrayList;
import java.util.List;

/**
 * Find the lowest common ancestor (LCA) of two nodes in a binary tree.
 * LeetCode: Lowest Common Ancestor of a Binary Tree
 * Approach: Postorder recursion; a non-null result from both children means the current root is the LCA.
 * Complexity: Time O(n), Space O(h).
 * Created by qingjuntian on 6/4/16.
 */
public class TreeAncestor implements Puzzle {

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

    private TreeNode lca(TreeNode root, int a, int b) {
        if (root == null) return null;
        if (root.value == a || root.value == b) return root;
        TreeNode l = lca(root.left, a, b);
        TreeNode r = lca(root.right, a, b);
        if (l == null) return r;
        if (r == null) return l;
        return root;
    }


    private TreeNode findCommonAncestor(TreeNode root, int a, int b) {

        List<TreeNode> aAncestor = findAncestor(root, a);
        List<TreeNode> bAncestor = findAncestor(root, b);


        if (aAncestor == null || bAncestor == null) {
            return null;
        }

        TreeNode[] arrA = new TreeNode[aAncestor.size()];
        TreeNode[] arrB = new TreeNode[bAncestor.size()];
        aAncestor.toArray(arrA);
        bAncestor.toArray(arrB);

        int i = 0;

        while (arrA[i] == arrB[i]) {
            i++;
        }

        return arrA[i - 1];
    }

    private List<TreeNode> findAncestor(TreeNode root, int value) {
        if (root == null) return null;

        if (root.value == value) {
            List<TreeNode> ret = new ArrayList<>();
            ret.add(root);
            return ret;
        }

        List<TreeNode> ret = find(root.left, value);
        if (ret != null) return ret;

        ret = find(root.right, value);
        if (ret != null) return ret;

        return null;
    }

    private List<TreeNode> find(TreeNode root, int value) {
        List<TreeNode> ancestor = findAncestor(root, value);
        if (ancestor != null) {
            List<TreeNode> ret = new ArrayList<>();
            ret.add(root);
            for (TreeNode n : ancestor) {
                ret.add(n);
            }
            return ret;
        }
        return null;
    }

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
