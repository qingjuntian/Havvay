import java.io.BufferedReader;
import java.io.FileReader;
import java.io.IOException;
import java.util.HashMap;
import java.util.LinkedList;
import java.util.List;
import java.util.Map;

/**
 * Created by qingjuntian on 12/20/16.
 */
public class TrainAnalysis {

    TrainResult result;

    public TrainAnalysis(String arg) {
        result = new TrainResult(arg);
    }


    public static void main(String args[]) throws Exception {
        TrainAnalysis analyzer = new TrainAnalysis(args[0]);
        analyzer.analyze();
    }

    public void analyze() throws Exception {
        String[] headers = null;
        List<Map> trainResults = new LinkedList<>();
        while (result.hasNext()) {
            String[] resultItems  = result.getNext();
            if (headers == null) {
                headers = resultItems;
            } else {
                Map<String, String> result = new HashMap<>();
                for (int i = 0; i < resultItems.length; i++) {
                    String h = headers[i];
                    String v = resultItems[i];
                    result.put(h, v);
                }
                trainResults.add(result);
            }
        }

        System.out.println();
    }
}


class TrainResult {

    private String data;
    private BufferedReader br;

    public TrainResult(String file) {
        try {
            br = new BufferedReader(new FileReader(file));
            data = br.readLine();
        } catch (IOException e) {
            e.printStackTrace();
            data = null;
            if (br != null) {
                try {
                    br.close();
                } catch (IOException e1) {
                    e1.printStackTrace();
                }
            }
        }
    }

    public boolean hasNext() {
        return data != null;
    }

    public String[] getNext() throws Exception {
        String ret = data;
        data = br.readLine();
        if (data == null) {
            br.close();
        }
        // here suppose the input format are userid^accessPath for each row.
        return ret.split(",");
    }
}