package puzzle.misc;
import puzzle.Puzzle;


import java.util.regex.Pattern;

/**
 * Regex / log-parsing experiments (precompiled patterns for IP extraction, etc.).
 * NOTE: Exploratory utility code; resolve() only prints a demo.
 */
public class RegexPuzzle implements Puzzle {
    private final Pattern patternSend = Pattern.compile("^(.*?) \\[(.*?)\\] INFO .*try.*reqid:(\\d*)");
    private final Pattern patternReceive = Pattern.compile("^(.*?) \\[(.*?)\\] INFO .*received.*reqid:(\\d*)");
    private final Pattern ip = Pattern.compile("([0-9]+\\.[0-9]+\\.[0-9]+)\\.[0-9]+");

    /**
     * Print a few math/regex-related demo values and keep the compiled patterns ready for experiments.
     */
    @Override
    public void resolve() {
        System.out.println(0.5044321962154061 * Math.log10(10 + 3.51));

        double[] testData = {0.0, 0.5, 1.0, 2.0, 5.0, 10.0};

        for (double d : testData) {
            System.out.println(d + "\t" + Math.log1p(d));
        }
    }
}
