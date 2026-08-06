package puzzle.strings;
import puzzle.Puzzle;

import java.util.LinkedList;
import java.util.List;

/**
 * Tokenize a command-line-style parameter string with single/double quotes and escapes.
 * Approach: Character-scanning state machine tracking the current quote state.
 * Complexity: Time O(n), Space O(n).
 */
public class ParamParsePuzzle implements Puzzle {

    /**
     * Parse a small sample parameter string and print the resulting token list.
     */
    @Override
    public void resolve() {
        String params = "a b c";
        System.out.println(parseArgs(params));
    }

    /**
     * Parse a command-line-style parameter string into tokens. Spaces split tokens unless the parser
     * is inside matching single or double quotes; mismatched closing quotes raise an exception.
     */
    private List<String> parseArgs(String params) {
        List<String> ret = new LinkedList<>();
        if (params == null) {
            return ret;
        }
        params = params.trim();

        if (params.length() == 0) {
            return ret;
        }
        char[] chars = params.toCharArray();

        char quota = 0;
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
                            throw new IllegalArgumentException("wrong arg format");
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
            throw new IllegalArgumentException("wrong arg format");
        }
        return ret;
    }
}
