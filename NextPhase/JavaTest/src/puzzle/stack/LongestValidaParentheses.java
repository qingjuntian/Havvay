package puzzle.stack;
import puzzle.Puzzle;

import java.util.Deque;
import java.util.LinkedList;

/**
 * Length of the longest valid (well-formed) parentheses substring.
 * LeetCode: Longest Valid Parentheses
 * Three approaches (all O(n) time):
 *   findLongestValid           - index stack + DP array, matched-pair span carried by M[pairIndex-1];
 *   findLongestValidStack      - classic sentinel stack (push -1 base), length = i - st.peek();
 *   findLongestValidTwoPointer - two-pass left/right counters, O(1) extra space.
 * Created by qingjuntian on 7/19/16.
 */
public class LongestValidaParentheses implements Puzzle {
    @Override
    public void resolve() {

        String input = "(())(())";

        System.out.println(findLongestValid(input));            // DP + 配对跨度进位
        System.out.println(findLongestValidStack(input));       // 标准解 1:哨兵栈
        System.out.println(findLongestValidTwoPointer(input));  // 标准解 2:双指针 O(1)

    }

    /**
     * DP + stack-stitch solution. M[i] stores the longest valid substring ending exactly at i.
     * When the current ')' matches the nearest unmatched '(', the new valid block spans that pair
     * plus any valid block immediately to the left of the matching '('.
     */
    public int findLongestValid(String s){
        if (s.length() <= 1){
            return 0;
        }
        char[] input = s.toCharArray();
        Deque<Integer> st = new LinkedList<>();
        int[] M = new int[input.length];
        M[0] = 0;
        st.push(0);
        int ans = 0;
        for (int i = 1 ; i < input.length ; i++){
            if (!st.isEmpty() && isValid(input, st.peek(), i)){
                int pairIndex = st.pop();
                M[i] = i - pairIndex + 1 + (pairIndex - 1 >= 0 ? M[pairIndex - 1] : 0);
            }else {
                st.push(i);
                M[i] = 0;
            }
            ans = Math.max(ans, M[i]);
        }
        return ans;
    }

    /**
     * Return true iff positions i and j form a directly matching pair "()".
     */
    private boolean isValid(char[] input, int i, int j){
        return input[i] == '(' && input[j] == ')';
    }

    /**
     * Standard solution 1 — sentinel index stack.
     * Push -1 as a base marker. For '(' push its index; for ')' pop the matching '(',
     * then either the stack is empty (this ')' is unmatched, becomes the new base) or
     * the length of the current valid run is i - st.peek() (distance to the last
     * unmatched index still on the stack). Time O(n), Space O(n).
     */
    public int findLongestValidStack(String s) {
        Deque<Integer> st = new LinkedList<>();
        st.push(-1);                              // base: index just before a valid run
        int ans = 0;
        for (int i = 0; i < s.length(); i++) {
            if (s.charAt(i) == '(') {
                st.push(i);
            } else {                              // ')'
                st.pop();                         // try to consume the matching '('
                if (st.isEmpty()) {
                    st.push(i);                   // no match -> this ')' is the new base
                } else {
                    ans = Math.max(ans, i - st.peek());
                }
            }
        }
        return ans;
    }

    /**
     * Standard solution 2 — two-pointer counters, O(1) extra space.
     * Left-to-right: count left '(' and right ')'; when equal a valid run of 2*right is
     * closed, when right exceeds left the run is broken so reset both. A symmetric
     * right-to-left pass catches runs like "(()" that the first pass never balances.
     * Time O(n), Space O(1).
     */
    public int findLongestValidTwoPointer(String s) {
        int ans = 0, left = 0, right = 0;
        for (int i = 0; i < s.length(); i++) {            // left -> right
            if (s.charAt(i) == '(') left++; else right++;
            if (left == right) ans = Math.max(ans, 2 * right);
            else if (right > left) left = right = 0;
        }
        left = right = 0;
        for (int i = s.length() - 1; i >= 0; i--) {       // right -> left
            if (s.charAt(i) == '(') left++; else right++;
            if (left == right) ans = Math.max(ans, 2 * left);
            else if (left > right) left = right = 0;
        }
        return ans;
    }


}
