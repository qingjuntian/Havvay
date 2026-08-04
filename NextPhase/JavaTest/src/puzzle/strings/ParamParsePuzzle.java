package puzzle.strings;
import puzzle.Puzzle;

import java.util.*;

/**
 * Tokenize a command-line-style parameter string with single/double quotes and escapes.
 * Approach: Character-scanning state machine tracking the current quote state.
 * Complexity: Time O(n), Space O(n).
 * Created by qingjuntian on 6/26/16.
 */
public class ParamParsePuzzle implements Puzzle {

    @Override
    public void resolve() {
        String params = "a b c";
        try {
            List<String> argList = parseArgs(params);
        } catch (Exception e) {
            e.printStackTrace();
        }

    }

    private List<String> parseArgs(String params) throws Exception {
        List<String> ret = new LinkedList();
        if (params == null) return ret;
        params = params.trim();

        if (params.length() == 0) return ret;
        char[] chars = params.toCharArray();

        char quota = 0;
        boolean escape;
        boolean inQuota = false;
        StringBuilder quotaCommand = new StringBuilder();
        StringBuilder command = new StringBuilder();

        for (char c : chars) {
            switch (c) {
                case '\"':
                case '\'': {
                    if (inQuota) {
                        if (c == quota) {
                            ret.add(quotaCommand.toString());
                            inQuota = false;
                        } else {
                            throw new Exception("wrong arg format");
                        }
                    } else {
                        inQuota = true;
                        quota = c;
                        quotaCommand = new StringBuilder();
                    }
                }
                break;
                case ' ': {
                    if (inQuota) {
                        quotaCommand.append(c);
                    } else if (command.length() > 0) {
                        ret.add(command.toString());
                        command = new StringBuilder();
                    }
                }
                break;
                case '\\': {
                    if (inQuota == false) {
                        command.append(c);
                    }
                }
                break;
                default: {
                    if (inQuota) {
                        quotaCommand.append(c);
                    } else {
                        command.append(c);
                    }
                }
            }

        }

        if (command.length() > 0) {
            ret.add(command.toString());
        }
        if (inQuota) {
            throw new Exception("wrong arg format");
        }


        return ret;

    }

    private List<Integer> composePatch2(int[] ints, int number) {

        List<Integer> patches = new ArrayList<>();

        int idx = 0;
        int upper = 1;
        while (upper < number) {
            if (idx < ints.length && ints[idx] <= upper) {
                upper += ints[idx++];
            } else {
                patches.add(upper);
                upper += upper;
            }
        }
        return patches;


    }

    private List<Integer> composePatch1(int[] ints, int number) {
        List<Integer> patches = new ArrayList<>();

        for (int item : ints) {
            patches.add(item);
        }


        Set<Integer>[] sums = new HashSet[number + 1];

        for (int i = 1; i < number + 1; i++) {
            sums[i] = new HashSet<>();
            if (patches.contains(i)) {
                sums[i].add(patches.indexOf(i));
                continue;
            }
            boolean ok = false;
            for (int j = 0; j < patches.size(); j++) {
                if (i > patches.get(j) && sums[i - patches.get(j)].contains(j) == false) {
                    sums[i].addAll(sums[i - patches.get(j)]);
                    sums[i].add(j);
                    ok = true;
                    break;
                }
            }
            if (ok == false) {
                patches.add(i);
                sums[i].add(patches.indexOf(i));
            }
        }
        return patches;
    }
}
