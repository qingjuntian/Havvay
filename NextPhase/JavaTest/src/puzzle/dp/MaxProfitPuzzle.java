package puzzle.dp;
import puzzle.Puzzle;
import java.util.Arrays;

/**
 * Maximum profit from stock prices (single-transaction helper plus a multi-transaction state-machine variant).
 * LeetCode: Best Time to Buy and Sell Stock (I/III)
 * Approach: maxProfit2 tracks the running minimum price; maxProfit uses global/local DP states.
 * Complexity: Time O(n), Space O(1).
 */
public class MaxProfitPuzzle implements Puzzle {

    @Override
    public void resolve() {
        System.out.println(maxProfit(new int[]{5, 4, 2, 9, 10}));
    }

    int maxProfit(int[] prices) {
        if (prices == null || prices.length == 0) return 0;
        int g[] = new int[4];
        int l[] = new int[4];

        for (int i = 0; i < prices.length - 1; ++i) {
            int diff = prices[i + 1] - prices[i];
            for (int j = 3; j >= 1; --j) {
                l[j] = Math.max(g[j - 1] + Math.max(diff, 0), l[j] + diff);
                g[j] = Math.max(l[j], g[j]);
            }
        }
        return g[2];
    }

    int maxProfit2(int[] prices) {
        int lc = prices[0];
        int max = Integer.MIN_VALUE;
        for (int i : prices) {
            max = Math.max(max, i - lc);
            lc = Math.min(lc, i);
        }
        return max;
    }

    // At most 2 transactions — buy/sell state machine (the standard, intuitive formulation).
    // O(n) time, O(1) space. Equivalent to maxProfit() above, but each variable is a real state.
    int maxProfit3(int[] prices) {
        if (prices == null || prices.length == 0) return 0;
        int buy1 = Integer.MIN_VALUE, sell1 = 0;
        int buy2 = Integer.MIN_VALUE, sell2 = 0;
        for (int p : prices) {
            buy1  = Math.max(buy1,  -p);        // max cash after the 1st buy (lowest cost)
            sell1 = Math.max(sell1, buy1 + p);  // after the 1st sell
            buy2  = Math.max(buy2,  sell1 - p); // buy again using the 1st profit
            sell2 = Math.max(sell2, buy2 + p);  // after the 2nd sell
        }
        return sell2;
    }

    // General framework — at most k transactions via cash/hold states. O(n*k) time, O(k) space.
    // Unifies every stock variant (I/II/III/IV). For THIS puzzle, call maxProfit4(prices, 2).
    int maxProfit4(int[] prices, int k) {
        if (prices == null || prices.length == 0 || k <= 0) return 0;
        int[] hold = new int[k + 1];   // hold[t] = best profit while HOLDING a stock in the t-th transaction
        int[] cash = new int[k + 1];   // cash[t] = best profit in CASH after completing up to t transactions
        Arrays.fill(hold, Integer.MIN_VALUE);
        for (int p : prices) {
            for (int t = 1; t <= k; t++) {
                hold[t] = Math.max(hold[t], cash[t - 1] - p); // buy:  from <=t-1 completed, spend p
                cash[t] = Math.max(cash[t], hold[t] + p);     // sell: gain p, completes the t-th transaction
            }
        }
        return cash[k];
    }


}
