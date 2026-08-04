package puzzle.misc;
import puzzle.Puzzle;


import java.util.regex.Pattern;

/**
 * Regex / log-parsing experiments (precompiled patterns for IP extraction, etc.).
 * NOTE: Exploratory utility code; resolve() only prints a demo.
 */
public class RegexPuzzle implements Puzzle {


    Pattern patternSend =       Pattern.compile("^(.*?) \\[(.*?)\\] INFO .*try.*reqid:(\\d*)");
    Pattern patternReceive =    Pattern.compile("^(.*?) \\[(.*?)\\] INFO .*received.*reqid:(\\d*)");
    Pattern ip = Pattern.compile("([0-9]+\\.[0-9]+\\.[0-9]+)\\.[0-9]+");


    private static Pattern featureNamePattern = Pattern.compile("(\\d*)\\t*(number|cate)\\_(.*)=(.*)\t.*");

    @Override
    public void resolve(){

        System.out.println(0.5044321962154061*Math.log10(10 + 3.51));

        double[] testData = {0.0, 0.5, 1.0, 2.0, 5.0, 10.0};

        for (double d : testData) {
            System.out.println("" + d + "\t" + Math.log1p(d));
        }


//        String s = "00:57:54.505 [qtp1551870003-29853] INFO  com.quixey.searchbackfill.services.shenma.ShenmaSearch - try to send shenma req with query:当爱已成往事 reqid:644902345";
//        String r = "00:57:54.734 [qtp1551870003-29851] INFO  com.quixey.searchbackfill.services.shenma.ShenmaSearch - received shenma req with query:当爱已成往事 reqid:847729594";
//
//
//
//        Matcher matcher = patternReceive.matcher(r);
//        if (matcher.matches()) {
//            try {
//                String ts = matcher.group(1);
//                String thread = matcher.group(2);dian
//                String reqid = matcher.group(3);
//
//                DateFormat format = new SimpleDateFormat("yy-MM-dd HH:mm:ss");
//                Date occurDateTime = format.parse("2016-09-09 " + ts);
//                int a = 0;
//            } catch (Exception e) {
//                //
//                e.printStackTrace();
//            }
//        }


    }

}
