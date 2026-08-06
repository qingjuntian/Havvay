package puzzle.math;
import puzzle.Puzzle;

/**
 * Compute the variance of a double array using two different formulas.
 * Approaches:
 *   ComputeVariance  - two-pass mean-then-deviation method (numerically safer);
 *   ComputeVariance2 - one-pass E[X^2] - (E[X])^2 method (shorter, but less stable).
 * Complexity: Time O(n), Space O(1).
 * Created by qingjuntian on 3/3/17.
 */
public class VariancePuzzle implements Puzzle {

    /**
     * Two-pass variance formula: first compute the mean, then sum squared deviations from that mean.
     * This is usually the numerically safer formulation.
     */
    private static double ComputeVariance(double a[]) {
        double variance = 0;//方差
        double average = 0;//平均数
        int i, len = a.length;
        double sum = 0, sum2 = 0;
        for (i = 0; i < len; i++) {
            sum += a[i];
        }
        average = sum / len;
        for (i = 0; i < len; i++) {
            sum2 += (a[i] - average) * (a[i] - average);
        }
        variance = sum2 / len;
        return variance;
    }

    /**
     * One-pass variance formula using E[X^2] - (E[X])^2. Shorter, but potentially less numerically
     * stable than the two-pass method above.
     */
    private static double ComputeVariance2(double a[]) {
        double variance = 0;//方差
        double sum = 0, sum2 = 0;
        int i = 0, len = a.length;
        for (; i < len; i++) {
            sum += a[i];
            sum2 += a[i] * a[i];
        }
        variance = sum2 / len - (sum / len) * (sum / len);
        return variance;
    }

    @Override
    public  void resolve() {
        double a[] = {1, 2, 3};
        System.out.println(ComputeVariance(a));
        System.out.println(ComputeVariance2(a));

    }
}
